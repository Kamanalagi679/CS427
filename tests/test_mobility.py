from dataclasses import replace

import numpy as np

from adrin_sim.mobility import empirical_matrix, generate_trace, transition_matrix


def test_transition_rows_sum_to_one(cfg):
    assert np.allclose(transition_matrix(cfg).sum(axis=1), 1.0)


def test_trace_shape_and_valid_zones(cfg):
    r = generate_trace(cfg, seed=1)
    assert r.trace.shape == (cfg.simulation.n_nodes, cfg.simulation.duration_min + 1)
    assert r.trace.min() >= 0 and r.trace.max() < len(cfg.mobility.zones)


def test_nodes_return_to_anchor_on_schedule(cfg):
    r = generate_trace(cfg, seed=1)
    period = cfg.mobility.anchor_period_min
    for minute in range(period, cfg.simulation.duration_min + 1, period):
        assert (r.trace[:, minute] == r.anchors).all()


def test_same_seed_gives_same_trace(cfg):
    a = generate_trace(cfg, seed=7)
    b = generate_trace(cfg, seed=7)
    assert (a.trace == b.trace).all()


def test_different_seed_gives_different_trace(cfg):
    a = generate_trace(cfg, seed=7)
    b = generate_trace(cfg, seed=8)
    assert not (a.trace == b.trace).all()


def test_movement_matches_paper_fig7(cfg):
    long_cfg = replace(
        cfg,
        simulation=replace(cfg.simulation, duration_min=3000),
        mobility=replace(cfg.mobility, anchor_period_min=None),
    )
    r = generate_trace(long_cfg, seed=0)
    observed = empirical_matrix(r.trace, len(cfg.mobility.zones), cfg.mobility.move_every_min)
    assert np.abs(observed - transition_matrix(cfg)).max() < 0.02
