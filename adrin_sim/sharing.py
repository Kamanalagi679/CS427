"""SHARING POLICIES - what a phone is willing to hand over when it meets another.

A policy is a function:   policy(notebook, owner, rng) -> notebook_view
where notebook_view is the same table with every entry the phone WITHHOLDS
replaced by UNKNOWN. Whatever is left is what the other phone learns.

Chosen by cfg.sharing.policy, so every experiment is just a config file.

  full            everything (normal ADRIN2.0 = the baseline)
  fraction        each known entry is shared with probability cfg.sharing.level
  own_trace_only  only the phone's own history, no second-hand gossip
  none            nothing (lower bound)
  recent          NOT YET (Step 4). Rejected by config validation up front, so a
                  run never starts with it and then fails half way.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from .config import Config
from .notebook import UNKNOWN

Policy = Callable[[np.ndarray, int, np.random.Generator], np.ndarray]


def _full(notebook, owner, rng):
    return notebook


def _none(notebook, owner, rng):
    return np.full_like(notebook, UNKNOWN)


def _own_trace_only(notebook, owner, rng):
    view = np.full_like(notebook, UNKNOWN)
    view[owner] = notebook[owner]
    return view


def get_policy(cfg: Config) -> Policy:
    name, level = cfg.sharing.policy, cfg.sharing.level
    if name == "full":
        return _full
    if name == "none":
        return _none
    if name == "own_trace_only":
        return _own_trace_only
    if name == "fraction":
        def _fraction(notebook, owner, rng):
            keep = rng.random(notebook.shape) < level
            return np.where(keep, notebook, UNKNOWN).astype(notebook.dtype)
        return _fraction
    # Only reachable if a Config was built without load_config's checks.
    raise ValueError(f"Unknown or unimplemented sharing policy '{name}'.")
