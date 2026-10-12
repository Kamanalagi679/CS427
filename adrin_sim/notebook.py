"""THE NOTEBOOK (frequency table F in the paper, Section III-B1).

A notebook is a table: notebook[v, t] = the zone phone v was in at minute t,
or UNKNOWN (-1) if this phone has never heard about it.

Two operations matter:
  merge(...)                          swap knowledge after a meeting
  transition_matrix_from_notebook()   turn knowledge into the table B used
                                      for routing decisions

NOTE on the paper's Eqs. 3-4 ("F_u <- F_u + F_v"): adding zone IDs makes no
sense, so we implement the intent: fill in what I don't know from what you
know. Entries never conflict because they all come from the same real trace.
"""
from __future__ import annotations

import numpy as np

UNKNOWN = -1


def new_notebook(n_nodes: int, n_minutes: int) -> np.ndarray:
    return np.full((n_nodes, n_minutes), UNKNOWN, dtype=np.int8)


def merge(mine: np.ndarray, shared: np.ndarray) -> None:
    """Fill the entries I don't know from what was shared with me (in place)."""
    fill = (mine == UNKNOWN) & (shared != UNKNOWN)
    mine[fill] = shared[fill]


def known_count(notebook: np.ndarray) -> int:
    return int(np.count_nonzero(notebook != UNKNOWN))


def transition_counts(notebook: np.ndarray, n_zones: int, step: int) -> np.ndarray:
    """How many times this notebook saw a move from zone i to zone j.

    Looks at pairs of known entries `step` minutes apart (one hop).
    """
    grid = notebook[:, ::step]
    a, b = grid[:, :-1], grid[:, 1:]
    ok = (a != UNKNOWN) & (b != UNKNOWN)
    counts = np.zeros((n_zones, n_zones))
    np.add.at(counts, (a[ok].astype(int), b[ok].astype(int)), 1)
    return counts


def transition_matrix_from_notebook(notebook: np.ndarray, n_zones: int, step: int) -> np.ndarray:
    """Zone-to-zone move counts from what this notebook knows, row-normalised.

    Rows with no data stay all zeros (no knowledge yet), as in the paper.
    (routing.py has a smoothed version for making forwarding decisions.)
    """
    counts = transition_counts(notebook, n_zones, step)
    rows = counts.sum(axis=1, keepdims=True)
    return np.divide(counts, rows, out=np.zeros_like(counts), where=rows > 0)
