from dataclasses import replace

import numpy as np
import pytest

from adrin_sim.notebook import UNKNOWN, new_notebook
from adrin_sim.routing import (RouteModel, backtrack, choose_neighbours, hop_minutes,
                               mean_first_passage, predicted_arrival, transition_matrix_from_notebook)
from adrin_sim.simulation import run_simulation

# The paper's worked example for Eq. 5: zones a, b, c (= 0, 1, 2).
A, B_, C = 0, 1, 2
PAPER_B = np.array([[0.33, 0.33, 0.33],
                    [1.0, 0.0, 0.0],
                    [0.0, 0.5, 0.5]])


def test_paper_worked_example_elementwise_mode():
    # The paper squares a single entry: P(b -> a in 2 hops) = B[b, a]^2 = 1.0^2 = 1.0.
    assert PAPER_B[B_, A] ** 2 == 1.0
    assert backtrack(PAPER_B, start_zone=B_, end_zone=A, n_hops=3, mode="elementwise") == [B_, A, A, A]


def test_paper_worked_example_matrix_mode_differs():
    # True 2-step probability is (B @ B)[b, a] = 0.33, not 1.0 - and the path changes.
    assert (PAPER_B @ PAPER_B)[B_, A] == pytest.approx(0.33)
    assert backtrack(PAPER_B, start_zone=B_, end_zone=A, n_hops=3, mode="matrix") == [B_, A, B_, A]


def test_backtrack_one_hop_is_just_start_and_end():
    assert backtrack(PAPER_B, 1, 2, 1, "matrix") == [1, 2]


def test_smoothing_gives_uniform_rows_without_data():
    B = transition_matrix_from_notebook(new_notebook(4, 30), 5, 3, smoothing=0.01)
    assert np.allclose(B, 0.2)


def test_smoothed_rows_sum_to_one_and_nothing_is_impossible(cfg):
    from adrin_sim.mobility import generate_trace
    trace = generate_trace(cfg, seed=0).trace.astype(np.int8)
    B = transition_matrix_from_notebook(trace, 5, 3, smoothing=0.01)
    assert np.allclose(B.sum(axis=1), 1.0) and (B > 0).all()


def test_mean_first_passage_simple_chain():
    # From zone 0 you reach zone 1 with probability 0.5 per hop -> 2 hops on average.
    h = mean_first_passage(np.array([[0.5, 0.5], [0.0, 1.0]]), target=1)
    assert h == pytest.approx([2.0, 0.0])


def test_hop_minutes_include_known_point():
    assert hop_minutes(10, 20, 3) == [12, 15, 18, 20]
    assert hop_minutes(10, 12, 3) == [12]


# --- predicted_arrival / choose_neighbours on a tiny hand-made world -----------
# 3 zones, base station = zone 1, hops every 3 minutes.
CHAIN = np.array([[0.0, 1.0, 0.0],    # 0 -> 1 -> 2, then stays in 2
                  [0.0, 0.0, 1.0],
                  [0.0, 0.0, 1.0]])


def tiny_model():
    return RouteModel(B=CHAIN, bs_zone=1, step=3, mode="matrix")


def test_known_schedule_through_base_station_gives_arrival():
    nb = new_notebook(3, 20)
    nb[2, 9] = 2                     # what I know: phone 2 will be in zone 2 at minute 9
    # Path 0 (min 0) -> 1 (min 3) -> 2 (min 6) -> 2 (min 9): passes the base station at minute 3.
    assert predicted_arrival(nb, 2, current_zone=0, current_minute=0, model=tiny_model()) == 3.0


def test_unknown_schedule_gives_no_prediction_unless_fallback():
    nb = new_notebook(3, 20)
    model = RouteModel(B=np.array([[0.5, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.5, 0.5]]),
                       bs_zone=1, step=3, mode="matrix")
    assert predicted_arrival(nb, 2, 0, 4, model) is None
    # Fallback: now + 2 hops (mean first passage) * 3 minutes.
    assert predicted_arrival(nb, 2, 0, 4, model, fallback=True) == pytest.approx(10.0)


def test_neighbour_without_known_schedule_is_never_chosen(cfg):
    c = replace(cfg, network=replace(cfg.network, require_better_than_self=False, k_copies=3))
    nb = new_notebook(cfg.simulation.n_nodes, cfg.simulation.duration_min + 1)
    nb[0, ::40] = 2                  # carrier 0 knows only its own anchor visits
    chosen = choose_neighbours(0, [1, 2, 3], nb, current_zone=2, current_minute=5, cfg=c,
                               rng=np.random.default_rng(0))
    assert chosen == []


def test_best_k_neighbours_are_the_earliest(cfg):
    c = replace(cfg, network=replace(cfg.network, require_better_than_self=False, k_copies=1))
    n = cfg.simulation.n_nodes
    nb = new_notebook(n, cfg.simulation.duration_min + 1)
    bs = cfg.mobility.zones.index(cfg.network.base_station_zone)
    nb[1, 40] = bs                   # phone 1 known to be at the base station at minute 40
    nb[2, 80] = bs                   # phone 2 only at minute 80
    chosen = choose_neighbours(0, [1, 2], nb, current_zone=0, current_minute=5, cfg=c,
                               rng=np.random.default_rng(0))
    assert chosen == [1]


def test_random_forwarding_picks_k_neighbours(cfg):
    c = replace(cfg, network=replace(cfg.network, forwarding="random", k_copies=2))
    nb = new_notebook(cfg.simulation.n_nodes, cfg.simulation.duration_min + 1)
    chosen = choose_neighbours(0, [4, 5, 6], nb, 0, 5, c, np.random.default_rng(0))
    assert len(chosen) == 2 and set(chosen) <= {4, 5, 6}


def test_sharing_nothing_means_nobody_is_ever_a_relay(cfg):
    c = replace(cfg, sharing=replace(cfg.sharing, policy="none"))
    assert run_simulation(c, seed=1).packets_sent == 0
