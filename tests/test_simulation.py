from dataclasses import replace

import numpy as np
import pytest

from adrin_sim.notebook import UNKNOWN
from adrin_sim.simulation import run_simulation


@pytest.fixture
def small(cfg):
    return replace(cfg, simulation=replace(cfg.simulation, n_nodes=20, duration_min=120))


def with_policy(cfg, policy, level=1.0):
    return replace(cfg, sharing=replace(cfg.sharing, policy=policy, level=level))


def test_no_notebook_entry_contradicts_reality(small):
    res = run_simulation(small)
    for node in res.nodes:
        known = node.notebook != UNKNOWN
        assert (node.notebook[known] == res.mobility.trace[known]).all()


def test_phones_always_know_their_own_past(small):
    res = run_simulation(small)
    for node in res.nodes:
        assert (node.notebook[node.id, :] != UNKNOWN).all()


def test_same_seed_is_reproducible(small):
    a = run_simulation(small, seed=4)
    b = run_simulation(small, seed=4)
    assert a.n_contacts == b.n_contacts
    assert np.allclose(a.coverage, b.coverage)


def test_sharing_policy_does_not_change_movement_or_meetings(small):
    full = run_simulation(with_policy(small, "full"), seed=2)
    none = run_simulation(with_policy(small, "none"), seed=2)
    assert (full.mobility.trace == none.mobility.trace).all()
    assert full.n_contacts == none.n_contacts
    assert full.bs_contacts == none.bs_contacts


def test_sharing_nothing_means_knowing_only_your_own_row(small):
    res = run_simulation(with_policy(small, "none"), seed=2)
    assert res.sharing_ratio == 0.0
    assert res.coverage[-1, 1] == pytest.approx(1 / small.simulation.n_nodes)


def test_full_sharing_ratio_is_one(small):
    assert run_simulation(with_policy(small, "full"), seed=2).sharing_ratio == pytest.approx(1.0)


def test_more_sharing_never_means_less_knowledge(small):
    cov = lambda p, l=1.0: run_simulation(with_policy(small, p, l), seed=2).coverage[-1, 1]
    full, half, own, none = cov("full"), cov("fraction", 0.5), cov("own_trace_only"), cov("none")
    assert full >= half >= none
    assert full >= own >= none


def test_fraction_policy_shares_roughly_that_fraction(small):
    ratio = run_simulation(with_policy(small, "fraction", 0.5), seed=2).sharing_ratio
    assert 0.4 < ratio < 0.6


def test_unknown_policy_that_skipped_config_checks_still_fails_clearly(small):
    with pytest.raises(ValueError):
        run_simulation(with_policy(small, "recent"))
