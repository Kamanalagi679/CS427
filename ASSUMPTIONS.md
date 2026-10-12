# Assumptions and Open Questions

The ADRIN2.0 paper does not fully specify everything this simulation needs, and its authors' code is not public. This file is in three parts:

1. **Ambiguities in the paper itself.** Gaps or contradictions in the published paper. These are findings, not choices.
2. **Modeling choices with measured impact.** Decisions made here, with numbers showing how much each one matters.
3. **Minor technical defaults.** Reasonable defaults with nothing measurable to report.

Settings marked `[assumption]` in `configs/default.yaml` refer back to this file.

How the numbers were produced:

- Unless stated otherwise, numbers are means over **10 seeds** with the default config (50 phones, 200 minutes, full sharing).
- **"Current"** means the current delivery rule: delivery needs a base-station contact.
- **"Old rule"** means numbers measured before the delivery-rule fix in §2.1 (delivery on mere presence in the zone). They are kept for comparison.

---

## 1. Ambiguities in the paper itself

### 1.1 Eq. 5 contradicts its own worked example (`network.backtrack_power`)

Backtracking (Eq. 5, Algorithm 1) picks each intermediate zone by maximising P(start → zone in k hops) × B[zone, next zone]. "P in k hops" should be the k-step Markov probability, i.e. the matrix power (Bᵏ)[start, zone]. But the paper's worked example squares a single entry instead.

The example has zones a, b, c and B = [[.33,.33,.33],[1,0,0],[0,.5,.5]]. It starts at b, ends at a, and covers 3 hops. It computes P(b → a in 2 hops) = B[b,a]² = 1.0² = **1.0**. The true value is (B²)[b,a] = **0.33**.

| | `matrix` (true Markov) | `elementwise` (paper's arithmetic) |
|---|---|---|
| P(b → a in 2 hops) | 0.33 | 1.0, the value the paper quotes |
| Backtracked path | **b → a → b → a** | **b → a → a → a** |
| Mean PDR, current rule | 0.638 | 0.641 |
| Mean PDR, old rule | 0.906 | 0.907 |

- **Chosen:** both modes are implemented. The default is `matrix`, because it is the mathematically correct one.
- **Tests:** `tests/test_routing.py` checks both paths. Only `elementwise` produces the paper's quoted 1.0. The paper's final path isn't available to compare against, so the match is on that intermediate value.
- **Impact:** in full simulations the choice changes PDR by under 0.005, because B's diagonal dominates and both modes usually agree.

### 1.2 What "messages per epoch" means (`network.messages_per_epoch = 50`)

Table 1 says 50 messages per epoch. It doesn't define an epoch, or say whether the count is per phone or for the whole network.

**Chosen:** 50 new messages **per simulated minute across the whole network**, each created at a uniformly random live phone, starting at minute 0. That gives 201 × 50 = 10,050 messages per run.

**Measured consequence:** with a network-wide total, more phones means less load per phone. That makes the paper's "more phones → higher PDR" trend partly a load effect, not a routing effect.

| PDR at 25 / 50 / 100 phones | Current rule | Old rule |
|---|---|---|
| ADRIN, 50 messages/min network-wide (the `validate_routing.py` check) | 0.531 / 0.638 / 0.758 | 0.825 / 0.906 / 0.966 |
| No meetings at all, same load | 0.520 / 0.632 / 0.716 | 0.805 / 0.862 / 0.894 |
| ADRIN, load held at 1 message per phone per minute | **0.677 / 0.638 / 0.677** | **0.911 / 0.906 / 0.924** |

The validation check passes, but at a fixed per-phone load PDR **does not rise at every step**, under either rule. The "more relays help" effect is not clearly visible in this model.

### 1.3 Radio range vs zone size: how contacts happen

The paper models 5 large zones (the NYC boroughs) but a radio range of 0.07 mile. It doesn't say how being in the same zone translates into being in radio range, either between phones or with the base station.

**Chosen:** per-minute contact probabilities as stand-ins:

- `contacts.pair_prob_per_min = 0.02` for two phones in the same zone;
- `contacts.base_station_prob_per_min = 0.1` for a phone in the base-station zone.

Both are **uncalibrated**; the plan is to tune them against the paper's Figs. 9–13. How delivery uses the base-station probability is a choice made here, and has a large measured impact (see §2.1).

### 1.4 Base-station location and home zones

The paper says neither where the base station is nor how phones' home (anchor) zones are assigned.

**Chosen:** the base station is in **Manhattan** (`network.base_station_zone`), and home zones are **uniformly random**. **Impact not measured yet.** Manhattan has a strong self-transition (0.73), so a different zone would likely change absolute PDR.

### 1.5 Energy figures without durations (`energy.scan_seconds_per_min`, `energy.seconds_per_packet`)

Table 1 gives power in watts (sensing 0.05, scanning 3.68, receive 0.31, transmit 0.37) but no duty cycle or airtime, so energy in joules can't be computed from the paper alone.

**Chosen:**

- The radio scans continuously (60 s per minute): 3.68 × 60 + 0.05 × 60 ≈ **224 J per phone per minute**.
- Each message takes 1 s of airtime: 0.37 J to send, 0.31 J to receive.

**Measured:**

- **About 55%** of the 100,000 J is left after 200 minutes, a mid range as intended.
- No phone dies in a default run; batteries would run out around minute 450.
- Scanning dominates the budget, so routing barely moves energy. ADRIN leaves **+0.83 percentage points** more than random forwarding under the current rule (+0.65 under the old rule), despite sending about 25× fewer packets.

### 1.6 Notebook merge, Eqs. 3–4

The paper writes the merge as F_u ← F_u + F_v. Adding zone IDs is meaningless, so the operation as written can't be the intended one.

**Chosen:** fill in each unknown entry from the partner's notebook. Entries can never conflict, because they all come from the same true trace.

**Measured:** `validate_notebooks.py` finds **0** entries contradicting the real trace. The average learned B ends within 0.001 of the moves that really happened, and within 0.018 of Fig. 7, after 6000 minutes.

### 1.7 Fig. 7 values are rounded

The printed transition probabilities don't sum exactly to 1 per row.

**Chosen:** each row is rescaled to sum to 1.

**Measured:** `validate_movement.py` finds a largest difference of **0.0041** between simulated and normalised Fig. 7 transitions (tolerance 0.02).

---

## 2. Modeling choices with measured impact

### 2.1 Delivery rule: contact with the base station, not just presence in its zone

- **Old rule:** a message was delivered whenever its carrier was anywhere in the Manhattan zone.
- **Current rule:** each minute, every live phone in Manhattan reaches the base station with probability `contacts.base_station_prob_per_min` (0.1), using the same random-draw pattern as pairwise meetings. Only phones that succeed deliver. The others keep their messages and retry in later minutes, or forward them as usual.
- **Tests:** every delivery must match a logged base-station contact, and with probability 0 nothing is delivered.

**Seed-0 baseline** (`python run_experiment.py`):

| | Old rule | Current rule |
|---|---|---|
| PDR | 0.906 (9,108 / 10,050) | **0.602** (6,053 / 10,050) |
| Latency, mean / median | 15.3 / 10.0 min | **37.1 / 26.0 min** |
| Energy left | 54,972 J (55.0%) | 54,975 J (55.0%) |
| Packets sent | 3,215 | 2,997 |
| Dropped at creation (buffer full) | 244 | 1,311 |

**`validate_routing.py`**, 10 seeds:

| Setting | Old rule | Current rule |
|---|---|---|
| ADRIN baseline | 0.906 | 0.638 |
| No meetings (no forwarding) | 0.862 | **0.632** |
| ADRIN − no forwarding | +0.045, ADRIN higher in 10/10 seeds | **+0.006, 6/10 seeds; within noise** |
| Random forwarding | 0.842 | 0.571 |
| ADRIN − random | +0.064, 10/10 seeds | +0.067, 10/10 seeds |
| Packets, random vs ADRIN | 50,919 vs 2,993 (17×) | 63,496 vs 2,558 (25×) |
| Buffer 25 / 50 / 100 / 200 | 0.649 / 0.813 / 0.906 / 0.942 | 0.326 / 0.491 / 0.638 / 0.709 |
| Messages delivered with latency 0 | 23.5% | 2.1% |

What changed:

- **As expected:** PDR without forwarding fell sharply (0.862 → 0.632), and latency more than doubled.
- **Not as expected:** the advantage of ADRIN over not forwarding did **not** widen. It shrank to +0.006, within seed-to-seed noise. ADRIN's lead over *random* forwarding stayed about the same (+0.064 → +0.067).
- **Not tuned:** `base_station_prob_per_min` was not changed to make the gap appear.

The hypothesis written here earlier was that routing ignored the wait for a base-station contact. **It was tested in §2.7 and ruled out:** adding the wait changes no decision at all.

### 2.2 Handoff (`network.handoff = true`)

**Chosen:** the sender deletes its own copy once at least one chosen neighbour has accepted the message. K then controls redundancy instead of filling every buffer.

| | Handoff on | Handoff off |
|---|---|---|
| PDR, current rule | **0.638** | 0.599 |
| Dropped at creation, current rule | 1,300 | 2,226 |
| Packets, current rule | 2,558 | 2,871 |
| PDR, old rule | 0.906 | 0.861 |
| Dropped at creation, old rule | 224 | 703 |
| Packets, old rule | 2,993 | 3,929 |

Without handoff, duplicate copies fill the buffers and new messages get dropped. Kept on.

### 2.3 Only forward to better carriers (`network.require_better_than_self = true`)

**Chosen:** forward only to neighbours predicted to reach the base-station zone **strictly earlier** than the carrier itself. The carrier's own estimate uses the fallback described in §3.

| | On | Off |
|---|---|---|
| PDR, current rule | **0.638** | 0.626 |
| Packets, current rule | 2,558 | 17,511 (6.8×) |
| PDR, old rule | 0.906 | 0.909 |
| Packets, old rule | 2,993 | 6,640 (2.2×) |

Turning the rule off costs many more packets for no gain in PDR. Kept on.

### 2.4 K copies has no measurable effect (`network.k_copies`)

This is a paper parameter, not a choice made here, but its lack of effect follows from the two choices above.

| | K = 1 | K = 3 |
|---|---|---|
| PDR, current rule | 0.638 | 0.638 |
| PDR, old rule | 0.908 | 0.906 |

With handoff and the better-than-self rule, a carrier rarely has more than one qualifying neighbour. The paper compares K = 1 and K = 3, so this difference is worth investigating.

### 2.5 Predictions use the carrier's knowledge

**Chosen:** a carrier builds B from **its own** notebook. A neighbour's "future schedule" is whatever the carrier has learned about it: in practice, its next anchor visit, which phones know about themselves from the start and share like any other entry. A neighbour with no known future entry cannot be ranked and is never chosen.

**Measured:** with sharing policy `none`, **0 packets** are ever sent (`tests/test_routing.py`). This is what lets the restricted-sharing experiments in Step 4 affect routing at all.

### 2.6 What counts in the PDR denominator

**Chosen:** **all created messages**, including those dropped at creation because the origin's buffer was full.

**Measured:** with the current rule about 1,300 of 10,050 messages are dropped this way. PDR is **0.638** counting them, and would be **0.732** if they were left out.

### 2.7 Adding the expected contact wait to predictions (`predicted_arrival`)

**Change:** since delivery needs a contact, every predicted arrival now adds the expected wait in the zone, 1 / `base_station_prob_per_min` = **10 minutes**. This applies in three cases:

- a backtracked path that reaches the base-station zone;
- the mean-first-passage fallback;
- a phone that is in the zone right now (now + 10, not now).

A spot check confirmed the change is active: a phone in the zone at minute 5 now predicts 15 instead of 5, and a fallback prediction moves from 20 to 30.

**Measured impact: none.** Every result is identical to §2.1's current-rule numbers, down to the packet counts:

| | Before the wait | With the wait |
|---|---|---|
| Seed-0 PDR | 0.602 | 0.602 |
| Seed-0 latency, mean / median | 37.1 / 26.0 min | 37.1 / 26.0 min |
| Seed-0 energy left | 54,975 J (55.0%) | 54,975 J (55.0%) |
| Seed-0 packets / dropped | 2,997 / 1,311 | 2,997 / 1,311 |
| ADRIN, 10 seeds | 0.638 | 0.638 |
| No forwarding | 0.632 | 0.632 |
| ADRIN − no forwarding | +0.006, 6/10 seeds, **weak** | +0.006, 6/10 seeds, **still weak** |
| ADRIN − random | +0.067, 10/10 seeds | +0.067, 10/10 seeds |
| K = 1 vs K = 3 | 0.638 vs 0.638 | 0.638 vs 0.638 |

**Why nothing changes:** every prediction, for the carrier and for each neighbour, gets the same +10 minutes. Adding a constant to every score changes neither the ranking of neighbours nor the "strictly earlier than me" test. Also, phones only meet when they are in the same zone. So when a carrier is in Manhattan, all of its neighbours are too, and all of them score "now + 10".

**What would actually differ** (not implemented here): a prediction that depends on how long each phone is likely to *stay* in the base-station zone, since more minutes there means more contact rolls. For example, it could use the probability of a contact during the predicted stay, instead of a fixed wait added to the first arrival. That would separate a neighbour about to leave Manhattan from one staying there.

---

## 3. Minor technical defaults

- **Smoothing:** `network.model_smoothing = 0.01` is added to every move count before normalising, so no move is impossible and the mean-first-passage system is always solvable. It must be > 0.
- **Ties:** ties in backtracking go to the lowest zone number.
- **Hop timing:** hops happen at multiples of `move_every_min` (3). A known anchor visit is the final hop even if it isn't a multiple of 3 (e.g. minute 40).
- **Path misses the base station:** a neighbour gets no prediction. For the carrier itself, the estimate is the known future time plus the mean first-passage time from that zone.
- **Carrier with no known schedule:** current time plus the mean first-passage time from the current zone, solving (I − Q)h = 1, with hops converted to minutes (×3).
- **Turn order:** carriers forward in a random order each minute, using their own random stream. Only messages held at the start of forwarding are sent; anything received waits until the next minute.
- **Full receiver:** the transfer is refused, with no packet counted and no energy spent.
- **Duplicates:** a message counts once, at its first delivery. There are no acknowledgements, so other copies are discarded only when they reach the base station.
- **Messages created in the base-station zone:** they count like any other. Under the current rule they still need a contact (2.1% are delivered in the same minute).
- **End of run:** messages created near minute 200 have little time to arrive, and count as undelivered.
- **Dead phones:** batteries are checked at the end of each minute. A phone at or below 10 J is switched off and its buffer is lost. No phone dies in a default run.
- **Random streams after a death:** meetings and base-station rolls are drawn for all phones and then filtered to live ones. Message origins are drawn only among live phones.
- **`recent` sharing policy:** it is Step 4 and not written yet, so the config loader rejects it with a clear message.
- **Packages:** `pandas` is used for result CSVs and validation tables. `matplotlib` was removed until graphs are made.
- **Git:** the project folder is not a git repository, and the README says so.
- **`validate_notebooks.py` check B:** its 6000-minute knowledge runs turn off messages and battery drain, which that check doesn't test.
