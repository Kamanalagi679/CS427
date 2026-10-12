"""Check 2: do the notebooks and the meeting rule behave sensibly?

Run:  python validate_notebooks.py

A. Correctness   - no phone ever "knows" something untrue.
B. Learning      - a phone's zone-to-zone table B, built from its notebook,
                   matches what really happened, and approaches the paper's
                   movement table as more time passes (mirrors Fig. 8).
C. Preview       - how much movement history phones learn under different
                   sharing policies (knowledge only, NOT routing performance).
"""
from dataclasses import replace

import numpy as np

from adrin_sim.config import load_config
from adrin_sim.mobility import empirical_matrix, transition_matrix
from adrin_sim.notebook import UNKNOWN, transition_matrix_from_notebook
from adrin_sim.simulation import run_simulation

TOL_REAL = 0.01     # phones should learn what really happened almost exactly
TOL_PAPER = 0.02    # ...and, with enough data, the paper's table


def check_correctness(cfg) -> bool:
    res = run_simulation(cfg)
    truth = res.mobility.trace
    bad = 0
    for node in res.nodes:
        known = node.notebook != UNKNOWN
        bad += int((node.notebook[known] != truth[known]).sum())
    print(f"A. Entries contradicting the real trace: {bad}  ->", "PASS" if bad == 0 else "FAIL")
    return bad == 0


def mean_local_matrix(res, n_zones, step):
    """Average of every phone's own table B (rows with no data are skipped)."""
    mats = np.stack([transition_matrix_from_notebook(n.notebook, n_zones, step) for n in res.nodes])
    valid = mats.sum(axis=2) > 0
    total = mats.sum(axis=0)
    counts = valid.sum(axis=0)[:, None]
    return np.divide(total, counts, out=np.zeros_like(total), where=counts > 0)


def check_learning(cfg) -> bool:
    """Compare each phone's learned table with (1) what really happened in the
    trace and (2) the paper's Fig. 7 table. (1) tests the notebooks; (2) also
    depends on how much movement was simulated, because a short trace is a
    noisy sample of the table."""
    n_zones = len(cfg.mobility.zones)
    step = cfg.mobility.move_every_min
    true_T = transition_matrix(cfg)
    # Knowledge only: no messages and no battery drain, so phones stay on for
    # the long runs (otherwise batteries run out after ~450 minutes).
    base = replace(cfg, simulation=replace(cfg.simulation, n_nodes=20),
                   mobility=replace(cfg.mobility, anchor_period_min=None),
                   network=replace(cfg.network, messages_per_epoch=0),
                   energy=replace(cfg.energy, sensing_w=0.0, scanning_w=0.0))
    print("B. Average phone's learned table (20 phones, no anchors)")
    print(f"   {'minutes':>8}{'vs what happened':>20}{'vs paper Fig. 7':>18}")
    err_real = err_paper = None
    for duration in (200, 1500, 6000):
        res = run_simulation(replace(base, simulation=replace(base.simulation, duration_min=duration)),
                             record_every=500)
        B = mean_local_matrix(res, n_zones, step)
        happened = empirical_matrix(res.mobility.trace, n_zones, step)
        err_real = float(np.abs(B - happened).max())
        err_paper = float(np.abs(B - true_T).max())
        print(f"   {duration:>8}{err_real:>20.4f}{err_paper:>18.4f}")
    ok = err_real < TOL_REAL and err_paper < TOL_PAPER
    print(f"   learned vs what happened < {TOL_REAL} and vs Fig. 7 < {TOL_PAPER}  ->", "PASS" if ok else "FAIL")
    return ok


def preview_policies(cfg, seeds=range(5)):
    print("C. Preview: what phones learn under each sharing policy (mean of 5 seeds)")
    print(f"   {'policy':<22}{'sharing ratio':>15}{'notebook coverage':>20}")
    rows = [("full", 1.0), ("fraction", 0.5), ("fraction", 0.25), ("own_trace_only", 1.0), ("none", 1.0)]
    for policy, level in rows:
        c = replace(cfg, sharing=replace(cfg.sharing, policy=policy, level=level))
        rs = [run_simulation(c, seed=s) for s in seeds]
        ratio = np.nanmean([r.sharing_ratio for r in rs])
        cov = np.mean([r.coverage[-1, 1] for r in rs])
        label = f"{policy} {level}" if policy == "fraction" else policy
        print(f"   {label:<22}{ratio:>15.3f}{cov:>20.3f}")


def main() -> int:
    cfg = load_config()
    ok = check_correctness(cfg)
    print()
    ok = check_learning(cfg) and ok
    print()
    preview_policies(cfg)
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
