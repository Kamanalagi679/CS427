"""PHONES (Step 2).

A Node is one phone: an id, its home (anchor) zone, and its notebook.
Later steps add a message buffer and a battery (Step 3).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from .config import Config
from .mobility import MobilityResult
from .notebook import new_notebook


@dataclass
class Node:
    id: int
    anchor: int
    notebook: np.ndarray    # shape (n_nodes, duration + 1)
    # Step 3 adds: buffer (messages carried), energy (battery left)


def build_nodes(cfg: Config, mobility: MobilityResult) -> List[Node]:
    """Create all phones. Each starts knowing only its own future anchor visits.

    Anchor visits are periodic (every anchor_period_min minutes at the home
    zone), so a phone knows them in advance - this is the 'periodicity' that
    ADRIN2.0 exploits.
    """
    n = cfg.simulation.n_nodes
    n_minutes = cfg.simulation.duration_min + 1
    period = cfg.mobility.anchor_period_min or n_minutes   # no period -> only minute 0
    nodes = []
    for u in range(n):
        nb = new_notebook(n, n_minutes)
        nb[u, ::period] = mobility.anchors[u]
        nodes.append(Node(id=u, anchor=int(mobility.anchors[u]), notebook=nb))
    return nodes
