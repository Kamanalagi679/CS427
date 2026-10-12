"""Check 3: does full-sharing ADRIN2.0 routing show the paper's TRENDS?

Run:  python validate_routing.py              (10 seeds per setting)
      python validate_routing.py --seeds 30

The paper's code is not public and several details had to be assumed (see
ASSUMPTIONS.md), so exact numbers cannot be replicated. Only the DIRECTION
of each effect is checked, using the mean over several seeds:
  1. More phones          -> higher delivery ratio (PDR)
  2. Bigger buffers       -> higher PDR
  3. ADRIN ranking beats picking random neighbours, on PDR and on energy left
  4. Forwarding at all beats no forwarding (no meetings: pair_prob_per_min = 0)
A FAIL is reported as a FAIL - parameters are not tuned to make it pass.
Checks 3 and 4 compare the same seeds side by side; a PASS is marked "weak"
when the average difference is smaller than twice its standard error, i.e.
the direction is right but could be seed-to-seed noise.
"""
import argparse
from dataclasses import replace

import pandas as pd

from adrin_sim.config import load_config
from adrin_sim.simulation import run_simulation


def run_setting(cfg, seeds):
    return pd.DataFrame([run_simulation(cfg, seed=s).summary() for s in seeds])


def show(label, df):
    print(f"   {label:<26} PDR {df.pdr.mean():.3f} ± {df.pdr.std():.3f}   "
          f"latency {df.latency_mean_min.mean():5.1f} min   "
          f"energy left {df.energy_left_pct.mean():6.3f}%   packets {df.packets_sent.mean():8.0f}")


def verdict(ok, text):
    print(f"   -> {'PASS' if ok else 'FAIL'}: {text}\n")
    return ok


def paired(a, b):
    """Mean of a - b over matching seeds, and whether it is within noise."""
    diff = a.reset_index(drop=True) - b.reset_index(drop=True)
    se = diff.std() / len(diff) ** 0.5
    weak = abs(diff.mean()) < 2 * se
    return diff.mean(), " (weak: within seed-to-seed noise)" if weak else ""


def increasing(name, values, cfg, seeds, make):
    print(f"{name}")
    means = []
    for v in values:
        df = run_setting(make(cfg, v), seeds)
        show(f"{v}", df)
        means.append(df.pdr.mean())
    ok = all(b > a for a, b in zip(means, means[1:]))
    return verdict(ok, "mean PDR rises at every step" if ok else
                   "mean PDR does NOT rise at every step " + str([round(m, 3) for m in means]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=10, help="seeds per setting (default 10)")
    args = parser.parse_args()
    seeds = range(args.seeds)
    cfg = load_config()
    net = lambda c, **kw: replace(c, network=replace(c.network, **kw))

    print("Trend checks only: the paper's code is not public, so its exact numbers")
    print(f"cannot be reproduced. Default config (full sharing), {args.seeds} seeds per setting.\n")
    results = []

    with_n = lambda c, n: replace(c, simulation=replace(c.simulation, n_nodes=n))
    no_meetings = lambda c: replace(c, contacts=replace(c.contacts, pair_prob_per_min=0.0))
    results.append(increasing("1. Number of phones", [25, 50, 100], cfg, seeds, with_n))
    print("   Caveat (information only, not a check): messages_per_epoch is a network-wide")
    print("   total, so more phones also means less load per phone. PDR with NO meetings")
    print("   at the same sizes shows how much of the trend is load rather than routing:")
    for n in (25, 50, 100):
        show(f"{n}, no meetings", run_setting(no_meetings(with_n(cfg, n)), seeds))
    print()
    results.append(increasing("2. Buffer size", [25, 50, 100, 200], cfg, seeds,
                              lambda c, b: net(c, buffer_size=b)))

    print("3. ADRIN ranking vs random neighbours")
    adrin = run_setting(cfg, seeds)
    rand = run_setting(net(cfg, forwarding="random"), seeds)
    show("adrin", adrin)
    show("random", rand)
    wins = int((adrin.pdr > rand.pdr).sum())
    gain, note = paired(adrin.pdr, rand.pdr)
    results.append(verdict(gain > 0, f"ADRIN PDR minus random: {gain:+.3f} "
                                     f"(ADRIN higher in {wins}/{args.seeds} seeds){note}"))
    egain, enote = paired(adrin.energy_left_pct, rand.energy_left_pct)
    results.append(verdict(egain > 0, f"ADRIN leaves {egain:+.3f} percentage points more energy "
                                      f"than random{enote}"))

    print("   Note: being switched on (scanning) costs ~224 J/min per phone; a packet costs")
    print("   under 1 J. Energy differences between forwarding modes are therefore small.\n")

    print("4. Forwarding vs no forwarding")
    none = run_setting(no_meetings(cfg), seeds)
    show("adrin", adrin)
    show("no meetings", none)
    gain, note = paired(adrin.pdr, none.pdr)
    results.append(verdict(gain > 0, f"forwarding changes mean PDR by {gain:+.3f} "
                                     f"(higher in {int((adrin.pdr > none.pdr).sum())}/{args.seeds} seeds){note}"))

    ok = all(results)
    print(f"{sum(results)}/{len(results)} checks passed")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
