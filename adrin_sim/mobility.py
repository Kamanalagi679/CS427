"""MOVEMENT MODEL (Step 1 - done and validated).

Phones hop between zones using the transition table from Fig. 7 of the
ADRIN2.0 paper, and return to their own home ("anchor") zone every
`anchor_period_min` minutes.

Input : a Config object
Output: a MobilityResult holding trace[node, minute] = zone number
Other modules (nodes, routing) read this trace to know who is where.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import simpy

from .config import Config


@dataclass
class MobilityResult:
    trace: np.ndarray     # shape (n_nodes, duration + 1); values are zone numbers
    anchors: np.ndarray   # shape (n_nodes,); each phone's home zone


def transition_matrix(cfg: Config) -> np.ndarray:
    """Fig. 7 table, with each row rescaled to add up to exactly 1."""
    T = np.asarray(cfg.mobility.transition_matrix, dtype=float)
    return T / T.sum(axis=1, keepdims=True)


def _node_process(env, node_id, anchor, trace, rng, T, move_every, anchor_period):
    """One phone. SimPy wakes it every simulated minute."""
    n_zones = T.shape[0]
    zone = anchor
    trace[node_id, 0] = zone
    for minute in range(1, trace.shape[1]):
        yield env.timeout(1)
        if anchor_period and minute % anchor_period == 0:
            zone = anchor                                 # forced return home
        elif minute % move_every == 0:
            zone = rng.choice(n_zones, p=T[zone])         # random hop
        trace[node_id, minute] = zone


def generate_trace(cfg: Config, seed: int) -> MobilityResult:
    rng = np.random.default_rng(seed)
    T = transition_matrix(cfg)
    n_nodes = cfg.simulation.n_nodes
    duration = cfg.simulation.duration_min
    anchors = rng.integers(0, T.shape[0], size=n_nodes)   # [assumption] uniform homes
    trace = np.zeros((n_nodes, duration + 1), dtype=int)

    env = simpy.Environment()
    for i in range(n_nodes):
        env.process(_node_process(
            env, i, anchors[i], trace, rng, T,
            cfg.mobility.move_every_min, cfg.mobility.anchor_period_min))
    env.run()
    return MobilityResult(trace=trace, anchors=anchors)


def empirical_matrix(trace: np.ndarray, n_zones: int, step: int) -> np.ndarray:
    """Count zone-to-zone moves actually seen in a trace (one look per hop)."""
    looks = trace[:, ::step]
    counts = np.zeros((n_zones, n_zones))
    np.add.at(counts, (looks[:, :-1].ravel(), looks[:, 1:].ravel()), 1)
    return counts / counts.sum(axis=1, keepdims=True)
