"""Check 1: does the simulated movement match the paper's Fig. 7 table?

Run:  python validate_movement.py
Runs a long simulation with no anchor returns (so only the hopping is
tested) and compares the moves it saw against the paper's table.
"""
from dataclasses import replace

import numpy as np

from adrin_sim.config import load_config
from adrin_sim.mobility import empirical_matrix, generate_trace, transition_matrix

TOLERANCE = 0.02   # largest allowed difference for a PASS


def main() -> int:
    cfg = load_config()
    long_cfg = replace(
        cfg,
        simulation=replace(cfg.simulation, duration_min=6000),
        mobility=replace(cfg.mobility, anchor_period_min=None),
    )
    result = generate_trace(long_cfg, seed=cfg.simulation.seed)
    n_zones = len(cfg.mobility.zones)
    observed = empirical_matrix(result.trace, n_zones, cfg.mobility.move_every_min)
    expected = transition_matrix(cfg)

    np.set_printoptions(precision=3, suppress=True)
    print("Observed transition matrix (simulation):\n", observed)
    print("\nPaper Fig. 7 (normalised):\n", expected)
    worst = float(np.abs(observed - expected).max())
    print(f"\nLargest difference: {worst:.4f}  (tolerance {TOLERANCE})")
    print("RESULT:", "PASS" if worst <= TOLERANCE else "FAIL")
    return 0 if worst <= TOLERANCE else 1


if __name__ == "__main__":
    raise SystemExit(main())
