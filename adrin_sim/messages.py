"""EMERGENCY MESSAGES (Step 3): creation, buffers, hand-overs, delivery.

Every message has an id. The store keeps:
  - each phone's buffer (at most cfg.network.buffer_size message ids)
  - a log: when each message was created, where, and when it was delivered
Several phones may hold copies of one message; it counts as delivered once,
the first time any carrier makes contact with the base station.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

NOT_DELIVERED = -1


class MessageStore:
    def __init__(self, n_nodes: int, capacity: int):
        self.capacity = capacity
        # dict used as an ordered set: oldest message first, fast "do I have it?"
        self.buffers: List[Dict[int, None]] = [dict() for _ in range(n_nodes)]
        self.created_at: List[int] = []
        self.origin: List[int] = []
        self.delivered_at: List[int] = []
        self.delivered_by: List[int] = []   # phone that delivered it first
        self.dropped_full = 0      # new messages lost because the origin's buffer was full
        self.packets_sent = 0      # successful phone-to-phone transfers
        self.max_occupancy = 0     # largest buffer seen during the run (for checks)

    def create(self, node: int, minute: int) -> int:
        """Log a new message at `node`; keep it only if the buffer has room."""
        mid = len(self.created_at)
        self.created_at.append(minute)
        self.origin.append(node)
        self.delivered_at.append(NOT_DELIVERED)
        self.delivered_by.append(NOT_DELIVERED)
        if len(self.buffers[node]) >= self.capacity:
            self.dropped_full += 1
        else:
            self._put(node, mid)
        return mid

    def transfer(self, src: int, dst: int, mid: int) -> bool:
        """Copy message `mid` from src to dst. False if dst is full or has it."""
        buf = self.buffers[dst]
        if mid in buf or len(buf) >= self.capacity:
            return False
        self._put(dst, mid)
        self.packets_sent += 1
        return True

    def remove(self, node: int, mid: int) -> None:
        self.buffers[node].pop(mid, None)

    def deliver_all(self, node: int, minute: int) -> int:
        """Phone made contact with the base station: hand over everything it carries.
        Returns how many messages were delivered for the first time."""
        new = 0
        for mid in self.buffers[node]:
            if self.delivered_at[mid] == NOT_DELIVERED:
                self.delivered_at[mid] = minute
                self.delivered_by[mid] = node
                new += 1
        self.buffers[node].clear()
        return new

    def clear(self, node: int) -> None:
        """Phone switched off: whatever it carried is lost."""
        self.buffers[node].clear()

    def log(self) -> Dict[str, np.ndarray]:
        return {"id": np.arange(len(self.created_at)),
                "origin": np.array(self.origin, dtype=int),
                "created": np.array(self.created_at, dtype=int),
                "delivered": np.array(self.delivered_at, dtype=int),
                "delivered_by": np.array(self.delivered_by, dtype=int)}

    def _put(self, node: int, mid: int) -> None:
        buf = self.buffers[node]
        buf[mid] = None
        self.max_occupancy = max(self.max_occupancy, len(buf))


def create_messages(store: MessageStore, alive: np.ndarray, count: int, minute: int,
                    rng: np.random.Generator) -> None:
    """`count` new messages, each at a phone picked at random from the live ones."""
    live = np.flatnonzero(alive)
    if live.size == 0:
        return
    for node in live[rng.integers(0, live.size, size=count)]:
        store.create(int(node), minute)
