"""Messages, buffers, delivery, energy and the per-run metrics."""
from collections import Counter
from dataclasses import replace

import numpy as np
import pytest

from adrin_sim.messages import NOT_DELIVERED, MessageStore
from adrin_sim.metrics import delivery_stats
from adrin_sim import simulation
from adrin_sim.simulation import run_simulation


@pytest.fixture
def small(cfg):
    return replace(cfg, simulation=replace(cfg.simulation, n_nodes=20, duration_min=120))


def with_network(cfg, **changes):
    return replace(cfg, network=replace(cfg.network, **changes))


# --- the message store on its own ---------------------------------------------

def test_full_buffer_drops_new_messages_and_refuses_transfers():
    store = MessageStore(n_nodes=2, capacity=2)
    for _ in range(3):
        store.create(0, minute=0)
    assert len(store.buffers[0]) == 2 and store.dropped_full == 1
    store.create(1, 0)
    store.create(1, 0)
    assert store.transfer(0, 1, 0) is False            # receiver full
    assert store.packets_sent == 0


def test_message_is_delivered_once_even_with_several_copies():
    store = MessageStore(n_nodes=3, capacity=5)
    mid = store.create(0, minute=2)
    store.transfer(0, 1, mid)
    store.transfer(0, 2, mid)
    assert store.deliver_all(1, minute=7) == 1
    assert store.deliver_all(2, minute=9) == 0         # second copy: not counted again
    assert store.delivered_at[mid] == 7


def test_latency_counts_delivered_messages_only():
    created = np.array([0, 10, 20, 30])
    delivered = np.array([5, NOT_DELIVERED, 50, NOT_DELIVERED])
    s = delivery_stats(created, delivered)
    assert s["pdr"] == 0.5
    assert s["latency_mean_min"] == pytest.approx((5 + 30) / 2)
    assert s["latency_median_min"] == pytest.approx(17.5)


def test_nothing_delivered_gives_no_latency():
    s = delivery_stats(np.array([0, 1]), np.array([NOT_DELIVERED, NOT_DELIVERED]))
    assert s["pdr"] == 0.0 and np.isnan(s["latency_mean_min"])


# --- whole simulation -----------------------------------------------------------

def test_buffers_never_exceed_capacity(small):
    res = run_simulation(with_network(small, buffer_size=5), seed=3)
    assert res.max_buffer <= 5
    assert res.dropped_full > 0                        # the limit really was hit


def test_messages_are_delivered_only_at_base_station_contacts(small):
    res = run_simulation(small, seed=3)
    m = res.messages
    done = m["delivered"] >= 0
    assert done.any()
    contacts = set(res.bs_contacts)
    assert all((int(t), int(u)) in contacts for t, u in zip(m["delivered"][done], m["delivered_by"][done]))


def test_being_in_the_zone_is_not_enough_without_contact(small):
    no_bs = replace(small, contacts=replace(small.contacts, base_station_prob_per_min=0.0))
    assert run_simulation(no_bs, seed=3).summary()["delivered"] == 0


def test_pdr_is_between_zero_and_one(small):
    s = run_simulation(small, seed=3).summary()
    assert 0.0 <= s["pdr"] <= 1.0
    assert s["created"] == small.network.messages_per_epoch * (small.simulation.duration_min + 1)


def test_delivery_never_happens_before_creation(small):
    m = run_simulation(small, seed=3).messages
    done = m["delivered"] >= 0
    assert (m["delivered"][done] >= m["created"][done]).all()


def test_same_seed_gives_identical_metrics(small):
    assert run_simulation(small, seed=5).summary() == run_simulation(small, seed=5).summary()


def test_energy_never_increases(small):
    res = run_simulation(small, seed=3)
    assert (res.energy[:, 0] <= res.initial_energy).all()
    assert (np.diff(res.energy, axis=1) <= 0).all()


def test_energy_after_default_run_is_in_a_middle_range(cfg):
    pct = run_simulation(cfg).summary()["energy_left_pct"]
    assert 20 < pct < 80


def test_empty_batteries_switch_phones_off(small):
    tiny = replace(small, energy=replace(small.energy, initial_j=1000))   # ~4.5 minutes of power
    res = run_simulation(tiny, seed=3)
    assert res.phones_died == small.simulation.n_nodes
    last_alive_minute = int(np.flatnonzero((res.energy > tiny.energy.threshold_j).any(axis=0)).max())
    assert res.messages["created"].max() <= last_alive_minute + 1
    assert (res.energy[:, -1] == res.energy[:, last_alive_minute + 1]).all()   # dead phones stop draining


def test_forwarding_mode_does_not_change_movement_meetings_or_messages(small):
    a = run_simulation(small, seed=2)
    b = run_simulation(with_network(small, forwarding="random"), seed=2)
    assert (a.mobility.trace == b.mobility.trace).all()
    assert a.n_contacts == b.n_contacts
    assert (a.messages["origin"] == b.messages["origin"]).all()


def test_handoff_with_one_copy_keeps_a_single_carrier(small, monkeypatch):
    """K = 1 with handoff: a message is passed on, never duplicated."""
    stores = []

    class RecordingStore(MessageStore):
        def __init__(self, *args):
            super().__init__(*args)
            stores.append(self)

    monkeypatch.setattr(simulation, "MessageStore", RecordingStore)
    res = run_simulation(with_network(small, k_copies=1, handoff=True), seed=3)
    assert res.packets_sent > 0
    copies = Counter(mid for buf in stores[0].buffers for mid in buf)
    assert max(copies.values()) == 1
