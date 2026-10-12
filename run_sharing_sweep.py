"""Step 4: how does restricting location sharing affect ADRIN2.0 routing?

Run:  python run_sharing_sweep.py                 (simulation.n_runs seeds per setting)
      python run_sharing_sweep.py --seeds 10      (quicker, less precise)
      python run_sharing_sweep.py --reanalyse results/sharing_sweep_<timestamp>
                                                  (redo the statistics from raw.csv, no simulation)

Runs every setting below on the SAME seeds, so each seed sees the same
movement, meetings and messages in every setting - only what is shared
(or how neighbours are picked) differs. That allows PAIRED comparisons:
each seed is compared with the same seed under full sharing.

Two separate questions, reported separately:
  1. Sharing levels vs full sharing: does restricting what phones share
     lower delivery (PDR)? Paired difference per level, Wilcoxon
     signed-rank test (paired t-test as a cross-check), Holm-corrected for
     the number of levels tested.
  2. Routing reference: ADRIN's ranked relay choice vs random relays, both
     with full sharing. This tests whether the prediction mechanism adds
     value; it is NOT a sharing level.

Saves to results/sharing_sweep_<timestamp>/:
    raw.csv            one row per (setting, seed)
    summary.csv        per setting: mean and standard error of each metric
    paired_tests.csv   question 1: one row per sharing level
    routing_check.csv  question 2: random vs ADRIN relay choice
    config_used.yaml   the base settings
Then plot with:  python plot_sharing_sweep.py results/sharing_sweep_<timestamp>
"""
import argparse
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from adrin_sim.config import PROJECT_ROOT, load_config, save_config
from adrin_sim.simulation import run_simulation

# (label, sharing policy, sharing level, forwarding)
SETTINGS = [
    ("full",            "full",           1.0,  "adrin"),
    ("fraction 1.0",    "fraction",       1.0,  "adrin"),
    ("fraction 0.75",   "fraction",       0.75, "adrin"),
    ("fraction 0.5",    "fraction",       0.5,  "adrin"),
    ("fraction 0.25",   "fraction",       0.25, "adrin"),
    ("fraction 0.0",    "fraction",       0.0,  "adrin"),
    ("own_trace_only",  "own_trace_only", 1.0,  "adrin"),
    ("none",            "none",           1.0,  "adrin"),
    ("random (full)",   "full",           1.0,  "random"),
]
BASELINE = "full"
ROUTING_REFERENCE = "random (full)"
# Sharing levels tested against full sharing. Left out: "fraction 1.0" and
# "fraction 0.0" are identical to "full" and "none" on every seed (sanity
# checks), and the random-forwarding reference answers a different question.
TESTED_LEVELS = ["fraction 0.75", "fraction 0.5", "fraction 0.25", "own_trace_only", "none"]

METRICS = ["pdr", "latency_mean_min", "latency_median_min", "energy_left_pct",
           "sharing_ratio", "packets_sent", "dropped_full_buffer"]


def run_sweep(cfg, seeds):
    rows, start = [], time.time()
    for n, (label, policy, level, forwarding) in enumerate(SETTINGS):
        c = replace(cfg, sharing=replace(cfg.sharing, policy=policy, level=level),
                    network=replace(cfg.network, forwarding=forwarding))
        for s in seeds:
            res = run_simulation(c, seed=s)
            rows.append({"setting": label, "policy": policy, "level": level, "forwarding": forwarding,
                         "seed": s, "sharing_ratio": res.sharing_ratio, **res.summary()})
        if n == 0:
            projected = (time.time() - start) * len(SETTINGS)
            print(f"   first setting took {time.time() - start:.0f}s -> whole sweep about {projected / 60:.1f} min")
            if projected > 300:
                print(f"   (that is more than 5 minutes; try --seeds {max(5, len(seeds) // 3)} for a quick look)")
        print(f"   done: {label}")
    return pd.DataFrame(rows)


def summarise(raw):
    """Mean and standard error of every metric, per setting (descriptive only)."""
    g = raw.groupby("setting", sort=False)
    summary = pd.DataFrame(index=[s[0] for s in SETTINGS])
    for m in METRICS:
        summary[m] = g[m].mean()
        summary[m + "_se"] = g[m].sem()
    summary["n_seeds"] = g.size()
    return summary.rename_axis("setting").reset_index()


def paired_diff(raw, setting, metric):
    """Per-seed difference setting - full sharing (same seeds)."""
    base = raw[raw.setting == BASELINE].set_index("seed")[metric]
    return (raw[raw.setting == setting].set_index("seed")[metric] - base).dropna()


def holm(pvalues):
    """Holm-Bonferroni adjusted p-values (controls the chance of any false positive)."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adjusted[i] = min(1.0, running)
    return adjusted


def paired_tests(raw):
    """Question 1: each sharing level's PDR vs full sharing, seed by seed."""
    base_pdr = raw[raw.setting == BASELINE].pdr.mean()
    rows = []
    for level in TESTED_LEVELS:
        d = paired_diff(raw, level, "pdr")
        n, mean, sd = len(d), d.mean(), d.std()
        se = sd / np.sqrt(n)
        half = stats.t.ppf(0.975, n - 1) * se
        rows.append({
            "setting": level,
            "sharing_ratio": raw[raw.setting == level].sharing_ratio.mean(),
            "n_seeds": n,
            "pdr_diff": mean,                       # absolute PDR change vs full sharing
            "pdr_diff_se": se,
            "ci95_low": mean - half,
            "ci95_high": mean + half,
            "pct_of_baseline_pdr": 100 * mean / base_pdr,
            "cohens_dz": mean / sd if sd > 0 else np.nan,   # difference in units of seed-to-seed spread
            "seeds_lower": int((d < 0).sum()),
            "seeds_higher": int((d > 0).sum()),
            "wilcoxon_p": stats.wilcoxon(d).pvalue,
            "ttest_p": stats.ttest_rel(raw[raw.setting == level].set_index("seed").pdr.loc[d.index],
                                       raw[raw.setting == BASELINE].set_index("seed").pdr.loc[d.index]).pvalue,
        })
    tests = pd.DataFrame(rows)
    tests["wilcoxon_p_holm"] = holm(tests.wilcoxon_p)
    tests["significant_5pct_holm"] = tests.wilcoxon_p_holm < 0.05
    return tests


def routing_check(raw):
    """Question 2: random relay choice vs ADRIN's ranked choice (both full sharing)."""
    rows = []
    for metric in ("pdr", "latency_mean_min", "energy_left_pct", "packets_sent"):
        d = paired_diff(raw, ROUTING_REFERENCE, metric)
        rows.append({"metric": metric,
                     "adrin_mean": raw[raw.setting == BASELINE][metric].mean(),
                     "random_mean": raw[raw.setting == ROUTING_REFERENCE][metric].mean(),
                     "random_minus_adrin": d.mean(),
                     "se": d.sem(),
                     "seeds_random_lower": int((d < 0).sum()),
                     "wilcoxon_p": stats.wilcoxon(d).pvalue})
    return pd.DataFrame(rows)


def report(tests, routing, raw):
    n = int(tests.n_seeds.min())
    base_pdr = raw[raw.setting == BASELINE].pdr.mean()
    print(f"\n1. RESTRICTED SHARING vs FULL SHARING  (PDR, {n} paired seeds; full-sharing PDR = {base_pdr:.3f})")
    print(f"   {'setting':<16}{'shared':>7}{'PDR change':>18}{'95% CI':>20}{'% of base':>10}"
          f"{'dz':>7}{'lower/higher':>14}{'Wilcoxon p':>12}{'Holm p':>9}{'t-test p':>10}")
    for r in tests.itertuples():
        print(f"   {r.setting:<16}{r.sharing_ratio:>7.3f}{r.pdr_diff:>+11.4f} ± {r.pdr_diff_se:.4f}"
              f"   [{r.ci95_low:+.4f}, {r.ci95_high:+.4f}]{r.pct_of_baseline_pdr:>+9.2f}%"
              f"{r.cohens_dz:>+7.2f}{f'{r.seeds_lower}/{r.seeds_higher}':>14}"
              f"{r.wilcoxon_p:>12.4f}{r.wilcoxon_p_holm:>9.4f}{r.ttest_p:>10.4f}")
    print("   PDR change = mean of (setting - full sharing) over the same seeds, ± standard error.")
    print("   dz = that change divided by its seed-to-seed spread (paired effect size).")
    print("   Holm p = Wilcoxon p corrected for testing", len(tests), "levels.")
    sig = tests[tests.significant_5pct_holm]
    if len(sig):
        print(f"   Statistically significant after correction: {', '.join(sig.setting)} "
              f"- but the largest of these is only {sig.pdr_diff.abs().max():.4f} PDR "
              f"({sig.pct_of_baseline_pdr.abs().max():.1f}% of baseline).")
    else:
        print("   No level differs significantly from full sharing after correction.")

    print("\n2. ROUTING REFERENCE: random relays vs ADRIN's ranked relays (both full sharing)")
    for r in routing.itertuples():
        print(f"   {r.metric:<18} ADRIN {r.adrin_mean:>9.3f}   random {r.random_mean:>9.3f}   "
              f"random - ADRIN {r.random_minus_adrin:>+10.3f} ± {r.se:.3f}   "
              f"random lower in {r.seeds_random_lower}/{n} seeds   Wilcoxon p {r.wilcoxon_p:.2g}")


def analyse(out_dir: Path, raw: pd.DataFrame) -> None:
    summarise(raw).to_csv(out_dir / "summary.csv", index=False)
    tests = paired_tests(raw)
    tests.to_csv(out_dir / "paired_tests.csv", index=False)
    routing = routing_check(raw)
    routing.to_csv(out_dir / "routing_check.csv", index=False)
    report(tests, routing, raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None, help="base experiment YAML (default: configs/default.yaml)")
    parser.add_argument("--seeds", type=int, default=None, help="seeds per setting (default: simulation.n_runs)")
    parser.add_argument("--reanalyse", metavar="SWEEP_DIR", default=None,
                        help="recompute statistics from an existing sweep's raw.csv (no simulation)")
    args = parser.parse_args()

    if args.reanalyse:
        out_dir = Path(args.reanalyse)
        analyse(out_dir, pd.read_csv(out_dir / "raw.csv"))
        print(f"\nRewrote summary.csv, paired_tests.csv, routing_check.csv in {out_dir}")
        return 0

    cfg = load_config(args.config)
    n_seeds = args.seeds or cfg.simulation.n_runs
    print(f"Sharing sweep: {len(SETTINGS)} settings x {n_seeds} seeds (seeds 0-{n_seeds - 1})")
    raw = run_sweep(cfg, range(n_seeds))

    out_dir = PROJECT_ROOT / cfg.output.results_dir / f"sharing_sweep_{datetime.now():%Y%m%d-%H%M%S}"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out_dir / "raw.csv", index=False)
    save_config(cfg, out_dir / "config_used.yaml")
    analyse(out_dir, raw)
    print(f"\nSaved to {out_dir}")
    print(f"Plot with: python plot_sharing_sweep.py {out_dir.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
