"""ADRIN2.0 ROUTING (Step 3): who should carry a message next?

A phone carrying messages that meets neighbours predicts, for each of them,
WHEN they will reach the base-station zone (delivery then still needs a
contact with the base station - see simulation.py), and hands copies to the K
earliest (K = cfg.network.k_copies).

How a prediction is made (paper Section III, Eq. 5, Algorithm 1):
  1. From MY notebook, build the zone-to-zone table B (one hop = move_every_min).
  2. Look in MY notebook for the neighbour's next KNOWN future position
     (its next anchor visit - phones know their own schedule and share it).
  3. Backtrack the most likely path of zones from "now, here" to that known
     future point. If the path passes the base-station zone, that is the
     predicted arrival.
  4. No known future point -> no prediction -> never chosen as a relay.
     (So a phone that shares nothing about its schedule is useless as a
     relay. This matters for the restricted-sharing experiments.)

The carrier's OWN prediction uses fallback=True: if backtracking gives no
answer it uses the average time to first reach the base station from B.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from .config import Config
from .notebook import UNKNOWN, transition_counts


def transition_matrix_from_notebook(notebook: np.ndarray, n_zones: int, step: int,
                                    smoothing: float) -> np.ndarray:
    """Table B for routing: move counts + `smoothing`, each row summed to 1.

    The smoothing means a move never seen is unlikely, not impossible, and a
    zone with no data at all gets a uniform row. (notebook.py's unsmoothed
    version is kept for the knowledge checks in validate_notebooks.py.)
    """
    counts = transition_counts(notebook, n_zones, step) + smoothing
    return counts / counts.sum(axis=1, keepdims=True)


def backtrack(B: np.ndarray, start_zone: int, end_zone: int, n_hops: int, mode: str) -> List[int]:
    """Most likely zone path start -> ... -> end over `n_hops` hops (Eq. 5).

    Works backwards from the known end: the zone at hop k is the one that
    maximises  P(start -> zone in k hops) * B[zone, zone at hop k+1].

    mode "matrix":      P = (B^k)[start, zone]   - true k-step Markov probability
    mode "elementwise": P = B[start, zone] ** k  - what the paper's worked
                        example computes (no cross terms)
    Ties go to the lowest zone number. Returns n_hops + 1 zones.
    """
    if n_hops < 1:
        raise ValueError("n_hops must be at least 1")
    path = [end_zone]
    step_power = np.eye(B.shape[0])
    k_step = []                       # k_step[k-1] = P(start -> * in k hops)
    for k in range(1, n_hops):
        if mode == "matrix":
            step_power = step_power @ B
            k_step.append(step_power[start_zone])
        elif mode == "elementwise":
            k_step.append(B[start_zone] ** k)
        else:
            raise ValueError(f"unknown backtrack mode '{mode}'")
    for k in range(n_hops - 1, 0, -1):
        score = k_step[k - 1] * B[:, path[0]]
        path.insert(0, int(np.argmax(score)))
    return [start_zone] + path


def mean_first_passage(B: np.ndarray, target: int) -> np.ndarray:
    """Expected hops to first reach `target` from each zone (0 for target).

    Standard absorbing-chain result: with Q = B minus the target's row and
    column, the hop counts h solve (I - Q) h = 1.
    """
    n = B.shape[0]
    others = [z for z in range(n) if z != target]
    Q = B[np.ix_(others, others)]
    h = np.zeros(n)
    h[others] = np.linalg.solve(np.eye(n - 1) - Q, np.ones(n - 1))
    return h


def hop_minutes(now: int, until: int, step: int) -> List[int]:
    """Minutes after `now` at which a phone can change zone, up to `until`.

    Phones hop on multiples of `step`; the known future point `until` (an
    anchor return) is always a change point too.
    """
    first = (now // step + 1) * step
    return list(range(first, until, step)) + [until]


def _expected_contact_wait(prob_per_min: float) -> float:
    return 1.0 / prob_per_min if prob_per_min > 0 else float("inf")


@dataclass
class RouteModel:
    """One carrier's view of the world at one minute (built from its notebook)."""
    B: np.ndarray
    bs_zone: int
    step: int
    mode: str
    bs_wait: float = 0.0     # expected minutes in the zone before a base-station contact
    _mfpt: Optional[np.ndarray] = field(default=None, repr=False)

    @classmethod
    def from_notebook(cls, notebook: np.ndarray, cfg: Config) -> "RouteModel":
        n_zones = len(cfg.mobility.zones)
        step = cfg.mobility.move_every_min
        return cls(B=transition_matrix_from_notebook(notebook, n_zones, step, cfg.network.model_smoothing),
                   bs_zone=cfg.mobility.zones.index(cfg.network.base_station_zone),
                   step=step, mode=cfg.network.backtrack_power,
                   bs_wait=_expected_contact_wait(cfg.contacts.base_station_prob_per_min))

    def mfpt_minutes(self, zone: int) -> float:
        if self._mfpt is None:
            self._mfpt = mean_first_passage(self.B, self.bs_zone)
        return float(self._mfpt[zone]) * self.step


def predicted_arrival(notebook: np.ndarray, neighbour: int, current_zone: int, current_minute: int,
                      model: RouteModel, fallback: bool = False) -> Optional[float]:
    """Predicted minute `neighbour` DELIVERS to the base station, using what
    `notebook` (the carrier's) knows about it. None = cannot be ranked.

    Reaching the base-station zone is not delivery: a contact is still needed,
    so every prediction adds the expected wait model.bs_wait (1 / p minutes).
    That includes a phone in the zone right now ("now + wait", not "now").

    fallback=True (used for the carrier itself) never returns None:
      - no known future point:        now + mean first-passage time from here + wait
      - path misses the base station: known point + mean first-passage from there + wait
    """
    future = np.flatnonzero(notebook[neighbour, current_minute + 1:] != UNKNOWN)
    if future.size == 0:
        return current_minute + model.mfpt_minutes(current_zone) + model.bs_wait if fallback else None
    until = current_minute + 1 + int(future[0])
    end_zone = int(notebook[neighbour, until])
    minutes = [current_minute] + hop_minutes(current_minute, until, model.step)
    path = backtrack(model.B, current_zone, end_zone, len(minutes) - 1, model.mode)
    for zone, minute in zip(path, minutes):
        if zone == model.bs_zone:                 # includes path[0]: in the zone right now
            return minute + model.bs_wait
    return until + model.mfpt_minutes(end_zone) + model.bs_wait if fallback else None


def choose_neighbours(carrier: int, neighbours: Sequence[int], notebook: np.ndarray, current_zone: int,
                      current_minute: int, cfg: Config, rng: np.random.Generator,
                      model: Optional[RouteModel] = None) -> List[int]:
    """Which neighbours get a copy of the carrier's messages this minute.

    "adrin":  rank neighbours by predicted arrival (earliest first), skip any
              that cannot be ranked, optionally keep only those predicted to
              beat the carrier itself, then take the best k_copies.
    "random": k_copies neighbours picked at random, predictions ignored.
    """
    k = cfg.network.k_copies
    if not neighbours:
        return []
    if cfg.network.forwarding == "random":
        picked = rng.choice(len(neighbours), size=min(k, len(neighbours)), replace=False)
        return [neighbours[i] for i in sorted(picked)]

    model = model or RouteModel.from_notebook(notebook, cfg)
    ranked: Dict[int, float] = {}
    for v in neighbours:
        t = predicted_arrival(notebook, v, current_zone, current_minute, model)
        if t is not None:
            ranked[v] = t
    if cfg.network.require_better_than_self:
        mine = predicted_arrival(notebook, carrier, current_zone, current_minute, model, fallback=True)
        ranked = {v: t for v, t in ranked.items() if t < mine}
    return sorted(ranked, key=lambda v: (ranked[v], v))[:k]
