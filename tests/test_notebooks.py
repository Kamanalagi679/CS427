import numpy as np

from adrin_sim.mobility import empirical_matrix, generate_trace
from adrin_sim.node import build_nodes
from adrin_sim.notebook import UNKNOWN, merge, new_notebook, transition_matrix_from_notebook


def test_merge_fills_only_unknown_entries():
    mine = new_notebook(2, 4)
    mine[0, 0] = 3
    theirs = new_notebook(2, 4)
    theirs[0, 0] = 3
    theirs[1, 2] = 1
    merge(mine, theirs)
    assert mine[0, 0] == 3 and mine[1, 2] == 1
    assert (mine == UNKNOWN).sum() == 8 - 2


def test_merge_is_idempotent():
    a = new_notebook(2, 4)
    b = new_notebook(2, 4)
    b[1, 1] = 2
    merge(a, b)
    snapshot = a.copy()
    merge(a, b)
    assert (a == snapshot).all()


def test_new_nodes_know_their_own_anchor_visits(cfg):
    mob = generate_trace(cfg, seed=3)
    nodes = build_nodes(cfg, mob)
    period = cfg.mobility.anchor_period_min
    for n in nodes:
        assert (n.notebook[n.id, ::period] == n.anchor).all()
        others = np.delete(n.notebook, n.id, axis=0)
        assert (others == UNKNOWN).all()          # knows nothing about other phones yet


def test_transition_matrix_from_full_notebook_matches_trace(cfg):
    mob = generate_trace(cfg, seed=3)
    n_zones = len(cfg.mobility.zones)
    step = cfg.mobility.move_every_min
    from_notebook = transition_matrix_from_notebook(mob.trace.astype(np.int8), n_zones, step)
    from_trace = empirical_matrix(mob.trace, n_zones, step)
    assert np.allclose(from_notebook, from_trace)


def test_empty_notebook_gives_zero_matrix(cfg):
    nb = new_notebook(5, 50)
    assert (transition_matrix_from_notebook(nb, 5, 3) == 0).all()
