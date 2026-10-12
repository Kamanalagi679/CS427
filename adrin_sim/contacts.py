"""THE MEETING RULE (Step 2).

Who is close enough to talk at a given minute?

Assumption (documented in configs/default.yaml): two phones can only meet if
they are in the same zone, and then they meet with a small probability per
minute. This stands in for the real radio range, which the zone-level model
in the paper does not capture.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np


def find_contacts(zone_of: np.ndarray, rng: np.random.Generator, pair_prob: float) -> List[Tuple[int, int]]:
    """Return the (i, j) pairs of phones that meet this minute."""
    pairs: List[Tuple[int, int]] = []
    for zone in np.unique(zone_of):
        members = np.flatnonzero(zone_of == zone)
        if len(members) < 2:
            continue
        i_idx, j_idx = np.triu_indices(len(members), k=1)
        hit = rng.random(len(i_idx)) < pair_prob
        pairs.extend(zip(members[i_idx[hit]].tolist(), members[j_idx[hit]].tolist()))
    return pairs


def base_station_contacts(zone_of: np.ndarray, bs_zone: int, rng: np.random.Generator, prob: float) -> List[int]:
    """Phones that reach the base station this minute (must be in its zone)."""
    members = np.flatnonzero(zone_of == bs_zone)
    return members[rng.random(len(members)) < prob].tolist()
