"""RESULTS.

notebook_coverage - how much of everyone's past movement the average phone
                    knows about (KNOWLEDGE, not routing performance).
delivery_stats    - packet delivery ratio (PDR) and latency (Step 3).
Energy and packet counts are summarised in simulation.SimulationResult.summary().
"""
from __future__ import annotations

from typing import List

import numpy as np

from .node import Node
from .notebook import UNKNOWN


def notebook_coverage(nodes: List[Node], minute: int) -> float:
    """Average fraction of all (phone, minute<=now) entries a phone knows."""
    return float(np.mean([(n.notebook[:, : minute + 1] != UNKNOWN).mean() for n in nodes]))


def delivery_stats(created: np.ndarray, delivered: np.ndarray) -> dict:
    """PDR and latency from the message log (delivered = -1 means never).

    PDR counts every message created, including ones dropped because the
    origin's buffer was full. Latency is over delivered messages only.
    """
    done = delivered >= 0
    latency = (delivered - created)[done]
    n = len(created)
    return {
        "created": n,
        "delivered": int(done.sum()),
        "pdr": float(done.sum() / n) if n else float("nan"),
        "latency_mean_min": float(latency.mean()) if latency.size else float("nan"),
        "latency_median_min": float(np.median(latency)) if latency.size else float("nan"),
    }
