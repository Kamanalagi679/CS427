"""THE CONDUCTOR: runs one simulation by calling the other modules in order.

    Before the clock starts
      mobility.generate_trace      who is where, every minute        (Step 1)
      node.build_nodes             phones with notebooks             (Step 2)
    Every simulated minute, in this order
      1. live phones note their own position in their notebook
      2. messages.create_messages  new emergency messages            (Step 3)
      3. contacts.find_contacts    who meets whom                    (Step 2)
      4. sharing + notebook.merge  swap notebook entries             (Step 2)
      5. routing.choose_neighbours hand messages to better carriers  (Step 3)
      6. delivery                  phones with a base-station contact (Step 3)
      7. energy                    batteries drain; empty phones die (Step 3)

Random numbers use separate streams (movement, contacts, sharing, messages,
routing), so changing the sharing policy or forwarding mode does NOT change
how phones move, who meets whom, or where messages appear. (The one
exception: if a battery runs out, that phone stops meeting and receiving
messages, so runs that spend energy differently can diverge after that.)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import simpy

from .config import Config
from .contacts import base_station_contacts, find_contacts
from .energy import Batteries
from .messages import MessageStore, create_messages
from .metrics import delivery_stats, notebook_coverage
from .mobility import MobilityResult, generate_trace
from .node import Node, build_nodes
from .notebook import known_count, merge
from .routing import RouteModel, choose_neighbours
from .sharing import get_policy


@dataclass
class SimulationResult:
    seed: int
    mobility: MobilityResult
    nodes: List[Node]
    coverage: np.ndarray                 # rows of (minute, coverage)
    n_contacts: int
    bs_contacts: List[Tuple[int, int]]   # (minute, node): live phone made contact with the base station
    sharing_ratio: float                 # entries actually shared / entries available
    messages: Dict[str, np.ndarray]      # per message: id, origin, created, delivered, delivered_by (-1 = never)
    energy: np.ndarray                   # battery level, shape (n_nodes, duration + 1), end of each minute
    initial_energy: float
    packets_sent: int
    dropped_full: int                    # new messages lost to a full buffer at creation
    phones_died: int
    max_buffer: int                      # largest buffer occupancy seen

    def summary(self) -> dict:
        out = delivery_stats(self.messages["created"], self.messages["delivered"])
        final = self.energy[:, -1]
        out.update({
            "energy_left_mean_j": float(final.mean()),
            "energy_left_pct": float(100 * final.mean() / self.initial_energy),
            "packets_sent": self.packets_sent,
            "dropped_full_buffer": self.dropped_full,
            "phones_died": self.phones_died,
            "meetings": self.n_contacts,
        })
        return out


def run_simulation(cfg: Config, seed: Optional[int] = None, record_every: int = 5) -> SimulationResult:
    seed = cfg.simulation.seed if seed is None else seed
    mobility = generate_trace(cfg, seed)
    nodes = build_nodes(cfg, mobility)
    n = cfg.simulation.n_nodes

    contact_rng = np.random.default_rng([seed, 1])
    share_rng = np.random.default_rng([seed, 2])
    message_rng = np.random.default_rng([seed, 3])
    route_rng = np.random.default_rng([seed, 4])
    policy = get_policy(cfg)
    bs_zone = cfg.mobility.zones.index(cfg.network.base_station_zone)

    store = MessageStore(n, cfg.network.buffer_size)
    batteries = Batteries(cfg)
    energy = np.zeros((n, cfg.simulation.duration_min + 1))

    coverage: List[Tuple[int, float]] = []
    bs_events: List[Tuple[int, int]] = []
    tally = {"contacts": 0, "available": 0, "shared": 0, "died": 0}

    def epochs(env):
        for minute in range(cfg.simulation.duration_min + 1):
            zone_of = mobility.trace[:, minute]
            alive = batteries.alive
            for node in nodes:                       # 1. each live phone notes where it is
                if alive[node.id]:
                    node.notebook[node.id, minute] = zone_of[node.id]

            create_messages(store, alive, cfg.network.messages_per_epoch, minute, message_rng)  # 2.

            # 3. Meetings are drawn for every phone so the random stream does not
            # depend on who is still alive; meetings involving dead phones are dropped.
            pairs = [(i, j) for i, j in find_contacts(zone_of, contact_rng, cfg.contacts.pair_prob_per_min)
                     if alive[i] and alive[j]]
            tally["contacts"] += len(pairs)
            # A phone in the base-station zone reaches the base station with
            # probability base_station_prob_per_min (same idea as pairwise meetings).
            reach_bs = [u for u in base_station_contacts(zone_of, bs_zone, contact_rng,
                                                         cfg.contacts.base_station_prob_per_min)
                        if alive[u]]
            bs_events.extend((minute, u) for u in reach_bs)

            # 4. Everyone hands over what they knew at the START of this minute
            # (no same-minute chains of relays).
            snap = {i: nodes[i].notebook.copy() for i in {p for pair in pairs for p in pair}}
            for i, j in pairs:
                for src, dst in ((i, j), (j, i)):
                    view = policy(snap[src], src, share_rng)
                    tally["available"] += known_count(snap[src])
                    tally["shared"] += known_count(view)
                    merge(nodes[dst].notebook, view)

            forward(minute, zone_of, pairs)                                          # 5.

            for u in reach_bs:                    # 6. only phones that made contact deliver;
                store.deliver_all(u, minute)      #    the rest keep their messages and retry

            for u in batteries.end_of_minute():                                      # 7.
                store.clear(int(u))
                tally["died"] += 1
            energy[:, minute] = batteries.level

            if minute % record_every == 0:
                coverage.append((minute, notebook_coverage(nodes, minute)))
            yield env.timeout(1)

    def forward(minute, zone_of, pairs):
        """Each phone with neighbours passes the messages it held at the start
        of this step to its chosen neighbours. Messages received this step
        wait until next minute. Phones take turns in a random order."""
        neighbours: Dict[int, List[int]] = {}
        for i, j in pairs:
            neighbours.setdefault(i, []).append(j)
            neighbours.setdefault(j, []).append(i)
        carriers = [u for u in sorted(neighbours) if store.buffers[u]]
        held = {u: list(store.buffers[u]) for u in carriers}
        for u in route_rng.permutation(carriers):
            u = int(u)
            nb = nodes[u].notebook
            model = RouteModel.from_notebook(nb, cfg) if cfg.network.forwarding == "adrin" else None
            chosen = choose_neighbours(u, sorted(neighbours[u]), nb, int(zone_of[u]), minute,
                                       cfg, route_rng, model)
            if not chosen:
                continue
            for mid in held[u]:
                passed = False
                for v in chosen:
                    if store.transfer(u, v, mid):
                        batteries.packet(u, v)
                        passed = True
                if passed and cfg.network.handoff:
                    store.remove(u, mid)

    env = simpy.Environment()
    env.process(epochs(env))
    env.run()

    ratio = tally["shared"] / tally["available"] if tally["available"] else float("nan")
    return SimulationResult(seed=seed, mobility=mobility, nodes=nodes,
                            coverage=np.array(coverage), n_contacts=tally["contacts"],
                            bs_contacts=bs_events, sharing_ratio=ratio,
                            messages=store.log(), energy=energy,
                            initial_energy=float(cfg.energy.initial_j),
                            packets_sent=store.packets_sent, dropped_full=store.dropped_full,
                            phones_died=tally["died"], max_buffer=store.max_occupancy)
