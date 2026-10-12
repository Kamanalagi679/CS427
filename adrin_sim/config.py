"""Loads the YAML settings into simple, checked Python objects.

Every other module receives a `Config` object and reads its settings from
it, so no numbers are hard-coded inside the simulation code.

How experiment files work:
    load_config("configs/experiments/foo.yaml")
    -> reads configs/default.yaml first,
    -> then overlays whatever foo.yaml changes.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "default.yaml"

SHARING_POLICIES = ("full", "fraction", "own_trace_only", "none")
PLANNED_POLICIES = ("recent",)          # named in the plan, not written yet
BACKTRACK_MODES = ("matrix", "elementwise")
FORWARDING_MODES = ("adrin", "random")


@dataclass(frozen=True)
class SimulationConfig:
    n_nodes: int
    duration_min: int
    seed: int
    n_runs: int


@dataclass(frozen=True)
class MobilityConfig:
    zones: List[str]
    move_every_min: int
    anchor_period_min: Optional[int]
    transition_matrix: List[List[float]]


@dataclass(frozen=True)
class NetworkConfig:
    k_copies: int
    buffer_size: int
    messages_per_epoch: int
    sliding_window: int
    base_station_zone: str
    model_smoothing: float
    backtrack_power: str
    require_better_than_self: bool
    forwarding: str
    handoff: bool


@dataclass(frozen=True)
class ContactsConfig:
    pair_prob_per_min: float
    base_station_prob_per_min: float


@dataclass(frozen=True)
class EnergyConfig:
    initial_j: float
    threshold_j: float
    sensing_w: float
    scanning_w: float
    receive_w_per_packet: float
    transmit_w_per_packet: float
    scan_seconds_per_min: float
    seconds_per_packet: float


@dataclass(frozen=True)
class SharingConfig:
    policy: str
    level: float


@dataclass(frozen=True)
class OutputConfig:
    results_dir: str


@dataclass(frozen=True)
class Config:
    simulation: SimulationConfig
    mobility: MobilityConfig
    network: NetworkConfig
    contacts: ContactsConfig
    energy: EnergyConfig
    sharing: SharingConfig
    output: OutputConfig


_SECTIONS = {
    "simulation": SimulationConfig,
    "mobility": MobilityConfig,
    "network": NetworkConfig,
    "contacts": ContactsConfig,
    "energy": EnergyConfig,
    "sharing": SharingConfig,
    "output": OutputConfig,
}


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Return base with override's values laid on top (recursively)."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _build_section(cls, data: Dict[str, Any], name: str):
    try:
        return cls(**data)
    except TypeError as err:  # missing or misspelled key
        raise ValueError(f"Problem in the '{name}' section of the config: {err}")


def _validate(cfg: Config) -> None:
    zones = cfg.mobility.zones
    matrix = cfg.mobility.transition_matrix
    if len(matrix) != len(zones) or any(len(row) != len(zones) for row in matrix):
        raise ValueError("transition_matrix must be square and match the number of zones")
    if cfg.network.base_station_zone not in zones:
        raise ValueError(f"base_station_zone must be one of {zones}")
    if cfg.sharing.policy in PLANNED_POLICIES:
        raise ValueError(f"sharing.policy '{cfg.sharing.policy}' is planned for Step 4 but not "
                         f"implemented yet; use one of {SHARING_POLICIES}")
    if cfg.sharing.policy not in SHARING_POLICIES:
        raise ValueError(f"sharing.policy must be one of {SHARING_POLICIES}")
    if not 0.0 <= cfg.sharing.level <= 1.0:
        raise ValueError("sharing.level must be between 0.0 and 1.0")
    for p_ in (cfg.contacts.pair_prob_per_min, cfg.contacts.base_station_prob_per_min):
        if not 0.0 <= p_ <= 1.0:
            raise ValueError("contact probabilities must be between 0.0 and 1.0")
    if cfg.simulation.n_nodes < 1 or cfg.simulation.duration_min < 1:
        raise ValueError("n_nodes and duration_min must be at least 1")
    net = cfg.network
    if net.backtrack_power not in BACKTRACK_MODES:
        raise ValueError(f"network.backtrack_power must be one of {BACKTRACK_MODES}")
    if net.forwarding not in FORWARDING_MODES:
        raise ValueError(f"network.forwarding must be one of {FORWARDING_MODES}")
    if net.model_smoothing <= 0:
        raise ValueError("network.model_smoothing must be greater than 0")
    if net.k_copies < 1 or net.buffer_size < 1 or net.messages_per_epoch < 0:
        raise ValueError("k_copies and buffer_size must be at least 1, messages_per_epoch at least 0")
    if not 0 <= cfg.energy.scan_seconds_per_min <= 60 or cfg.energy.seconds_per_packet < 0:
        raise ValueError("scan_seconds_per_min must be 0-60 and seconds_per_packet at least 0")


def load_config(path: Optional[str] = None) -> Config:
    """Load default.yaml, then overlay the experiment file at `path` (if given)."""
    raw = _read_yaml(DEFAULT_CONFIG_PATH)
    if path is not None and Path(path).resolve() != DEFAULT_CONFIG_PATH.resolve():
        raw = _deep_merge(raw, _read_yaml(Path(path)))
    cfg = Config(**{name: _build_section(cls, raw.get(name, {}), name)
                    for name, cls in _SECTIONS.items()})
    _validate(cfg)
    return cfg


def save_config(cfg: Config, path: Path) -> None:
    """Write the exact settings used, so a result can always be reproduced."""
    with open(path, "w") as f:
        yaml.safe_dump(asdict(cfg), f, sort_keys=False)
