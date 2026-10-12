"""Run one simulation from a config file and save the result.

Run:  python run_experiment.py
      python run_experiment.py --config configs/experiments/example_fraction_50.yaml

Results go to results/<config-name>_<timestamp>/ together with the exact
settings used (config_used.yaml), so any result can be reproduced later:
    summary.csv            one row: PDR, latency, energy, packets, drops, deaths
    messages.csv           one row per message: origin, created, delivered, delivered_by (blank = never)
    notebook_coverage.csv  knowledge over time
    mobility_trace.npy     zone of every phone at every minute
"""
import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from adrin_sim.config import load_config, save_config, PROJECT_ROOT
from adrin_sim.simulation import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None,
                        help="experiment YAML (changes on top of configs/default.yaml)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    result = run_simulation(cfg)

    name = Path(args.config).stem if args.config else "default"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = PROJECT_ROOT / cfg.output.results_dir / f"{name}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_config(cfg, out_dir / "config_used.yaml")
    np.save(out_dir / "mobility_trace.npy", result.mobility.trace)
    np.savetxt(out_dir / "notebook_coverage.csv", result.coverage, delimiter=",",
               header="minute,coverage", comments="")
    summary = result.summary()
    pd.DataFrame([{"config": name, "seed": result.seed, **summary}]).to_csv(out_dir / "summary.csv", index=False)
    log = pd.DataFrame(result.messages)
    for col in ("delivered", "delivered_by"):                                           # blank = never
        log[col] = log[col].where(log[col] >= 0).astype("Int64")
    log.to_csv(out_dir / "messages.csv", index=False)

    trace = result.mobility.trace
    net = cfg.network
    print(f"Config      : {args.config or 'configs/default.yaml'}")
    print(f"Seed        : {result.seed}")
    print(f"Trace shape : {trace.shape}  (nodes x minutes)")
    print(f"Sharing     : {cfg.sharing.policy} (level {cfg.sharing.level})")
    print(f"Routing     : {net.forwarding}, K={net.k_copies}, backtrack={net.backtrack_power}, "
          f"handoff={net.handoff}, better-than-self={net.require_better_than_self}")
    print(f"Meetings    : {result.n_contacts}")
    print(f"Sharing ratio        : {result.sharing_ratio:.3f}  (entries shared / available)")
    print(f"Notebook coverage    : {result.coverage[-1, 1]:.3f}  at minute {int(result.coverage[-1, 0])}")
    print(f"Messages             : {summary['created']} created, {summary['delivered']} delivered, "
          f"{summary['dropped_full_buffer']} dropped (buffer full at creation)")
    print(f"PDR                  : {summary['pdr']:.3f}")
    print(f"Latency (delivered)  : mean {summary['latency_mean_min']:.1f} min, "
          f"median {summary['latency_median_min']:.1f} min")
    print(f"Energy left (mean)   : {summary['energy_left_mean_j']:.0f} J  "
          f"({summary['energy_left_pct']:.1f}% of {cfg.energy.initial_j:.0f} J)")
    print(f"Packets sent         : {summary['packets_sent']}")
    print(f"Phones died          : {summary['phones_died']}")
    print(f"Saved to    : {out_dir}")

if __name__ == "__main__":
    main()
