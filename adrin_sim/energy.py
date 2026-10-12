"""BATTERIES (Step 3).

Uses the Table 1 power figures in configs/default.yaml. Table 1 gives watts
but not for how long each activity runs, so two [assumption] durations turn
them into joules:
    being on, per minute :  sensing_w * 60  +  scanning_w * scan_seconds_per_min
    each packet          :  transmit_w_per_packet (or receive_w_per_packet) * seconds_per_packet
A phone at or below threshold_j switches off for the rest of the run.
"""
from __future__ import annotations

import numpy as np

from .config import Config


class Batteries:
    def __init__(self, cfg: Config):
        e = cfg.energy
        self.level = np.full(cfg.simulation.n_nodes, float(e.initial_j))
        self.threshold = e.threshold_j
        self.idle_j_per_min = e.sensing_w * 60 + e.scanning_w * e.scan_seconds_per_min
        self.tx_j = e.transmit_w_per_packet * e.seconds_per_packet
        self.rx_j = e.receive_w_per_packet * e.seconds_per_packet
        self.alive = self.level > self.threshold

    def packet(self, sender: int, receiver: int) -> None:
        self.level[sender] -= self.tx_j
        self.level[receiver] -= self.rx_j

    def end_of_minute(self) -> np.ndarray:
        """Drain every live phone for one minute; return ids that just died."""
        self.level[self.alive] -= self.idle_j_per_min
        died = np.flatnonzero(self.alive & (self.level <= self.threshold))
        self.alive[died] = False
        return died
