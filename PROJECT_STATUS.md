# Project Status: CS427 ADRIN2.0 Replication

**Topic:** How restricting the location history that phones share affects mobility-informed routing in post-disaster networks (based on Halder et al., "ADRIN2.0", IEEE Access 12, 2024).
**Status date:** 12 October 2026. Steps 1–3 are done: movement, notebooks and full-sharing routing. The first Step 4 sharing sweep has run (results below). The written report has not started.

---

## Summary

The simulator now runs the **unrestricted (full-sharing) ADRIN2.0 baseline** end to end. In one run:

- 50 phones move between 5 New York zones for 200 minutes (paper Fig. 7 transitions), returning to their home zone every 40 minutes.
- They swap notebook entries when they meet.
- 50 emergency messages appear each minute at random phones and are held in buffers of at most 100.
- When a carrier meets other phones, it predicts each one's arrival at the base-station zone (Manhattan) by backtracking (paper Eq. 5). It hands its messages to the best K = 3 that are predicted to arrive sooner than itself.
- A carrier in the base-station zone reaches the base station with probability 0.1 per minute; only then are its messages delivered.
- Batteries drain using the paper's Table 1 power figures.

`run_experiment.py` prints and saves PDR, latency, residual energy, packets, drops and deaths for **one seed**. `validate_routing.py` checks the paper's trends over 10 seeds.

## Implemented, module by module

| Module | What it does |
|---|---|
| `config.py` | Loads `default.yaml` and applies an experiment file on top. Checks every setting, including the new routing and energy fields, and rejects the not-yet-written `recent` policy up front. |
| `mobility.py` | Movement trace (SimPy). Hops every 3 min using the Fig. 7 matrix; forced home every 40 min. |
| `notebook.py` | Notebook table, merge, and move counting. |
| `node.py` | Phones. Each starts knowing its own future anchor visits. |
| `contacts.py` | Meetings between phones in the same zone, with a per-minute probability. |
| `sharing.py` | Sharing policies `full`, `fraction`, `own_trace_only` and `none`. **Only `full` is used in Step 3.** |
| `routing.py` | **New.** Smoothed transition matrix B; Eq. 5 backtracking in two modes (`matrix`, `elementwise`); mean first-passage fallback; arrival prediction; choosing the K best neighbours (or K random ones). |
| `messages.py` | **New.** Message creation, capped buffers, transfers, single-count delivery, and the message log. |
| `energy.py` | **New.** Idle and per-packet battery drain. A phone at or below the threshold switches off. |
| `simulation.py` | Minute loop: own position → new messages → meetings → notebook merge → forwarding → delivery → energy. Separate random streams for movement, contacts, sharing, messages and routing. |
| `metrics.py` | Notebook coverage; PDR and latency (latency over delivered messages only). |

## What is validated

| Check | Result |
|---|---|
| `validate_movement.py`: movement matches Fig. 7 (6000 min, tolerance 0.02) | **PASS** (largest difference 0.0041) |
| `validate_notebooks.py`: no false knowledge; learned B matches the real moves and Fig. 7 | **PASS** |
| `validate_routing.py`: trend directions over 10 seeds | **PASS, 5/5** (caveats below) |
| `pytest` | **54 passed** |

The routing trends checked (mean PDR over 10 seeds):

| Trend | Result |
|---|---|
| More phones → higher PDR | 0.531 → 0.638 → 0.758 (25 → 50 → 100 phones) |
| Bigger buffer → higher PDR | 0.326 → 0.491 → 0.638 → 0.709 (buffers 25 → 200) |
| ADRIN vs random neighbours | PDR 0.638 vs 0.571 (ADRIN better in 10/10 seeds); slightly more energy left (+0.83 pp), with 25× fewer packets |
| Forwarding vs none | PDR 0.638 vs 0.632. **Passes only weakly:** ADRIN is higher in just 6/10 seeds, within noise |

Exact numbers from the paper can't be replicated without its code, so only trend directions are checked.

New tests cover:

- the paper's Eq. 5 worked example in both modes;
- smoothing and the mean first-passage time;
- that a phone with an unknown schedule is never a relay;
- that buffers never exceed capacity;
- that energy never increases, and that dead phones stop;
- that the same seed gives identical metrics;
- that PDR stays in [0, 1], and latency is computed over delivered messages only;
- that the forwarding mode doesn't change movement, meetings or message origins;
- that handoff with K = 1 never duplicates a message.

**Baseline run** (`python run_experiment.py`, seed 0):

| Metric | Value |
|---|---|
| PDR | 0.602 (6,053 of 10,050 messages) |
| Latency | mean 37.1 min, median 26.0 min |
| Energy left | 54,972 J (55.0%) |
| Packets sent | 2,997 |
| Dropped at creation (buffer full) | 1,311 |
| Phones died | 0 |

## Step 4 results: restricted-sharing sweep

**How it was run:** `python run_sharing_sweep.py`, then `python plot_sharing_sweep.py results/sharing_sweep_20261012-202537`.

- Each setting ran on the same 30 seeds (`simulation.n_runs`), so every setting sees identical movement, meetings and messages; only what is shared differs. That allows a **paired** comparison: each seed under restricted sharing is compared with the same seed under full sharing. This removes most of the seed-to-seed noise.
- Results are in `results/sharing_sweep_20261012-202537/`: `paired_tests.csv`, `routing_check.csv`, `summary.csv`, `raw.csv` and `sharing_sweep.png`.

The sweep answers two separate questions, reported separately below.

### Result 1: restricting sharing lowers delivery, but only very slightly

Full sharing delivers **66.3%** of messages (PDR 0.663). The table shows how much each restricted level changes that, seed by seed.

| Sharing level | Share of notebook actually shared | PDR change vs full sharing (± s.e.) | 95% CI | As % of baseline | Seeds lower / higher | p (Wilcoxon, Holm-corrected) |
|---|---|---|---|---|---|---|
| fraction 0.75 | 75% | +0.0001 ± 0.0012 | −0.0023 to +0.0026 | +0.02% | 12 / 16 | 1.00 |
| fraction 0.5 | 50% | −0.0002 ± 0.0013 | −0.0029 to +0.0024 | −0.03% | 16 / 14 | 1.00 |
| fraction 0.25 | 25% | −0.0016 ± 0.0016 | −0.0048 to +0.0017 | −0.24% | 19 / 11 | 0.90 |
| own trace only | 7.5% | **−0.0035 ± 0.0011** | **−0.0056 to −0.0013** | **−0.52%** | 21 / 9 | **0.026** |
| none (nothing shared) | 0% | −0.0050 ± 0.0035 | −0.0121 to +0.0020 | −0.76% | 18 / 11 | 0.89 |

Key to the columns:

- **PDR change:** a change of −0.0035 means 0.35 fewer messages delivered per 100 sent.
- **s.e.:** standard error.
- **95% CI:** the range the true change very likely falls in. If it includes zero, the level cannot be told apart from full sharing.
- **Seeds lower / higher:** these don't always add up to 30, because some seeds tie.
- **p:** how likely a difference this consistent would be if the sharing level had no effect. It uses the Wilcoxon signed-rank test, chosen because one level's differences are not normally distributed. It is Holm-corrected because five levels are tested. A paired t-test gives the same conclusions (`paired_tests.csv`).

**How to read this:**

- **Direction:** as sharing falls, the average PDR change falls steadily, from +0.0001 to −0.0050. The direction is consistent with the hypothesis.
- **Statistical significance:** only *own trace only* differs from full sharing beyond chance, after correcting for testing five levels (p = 0.026; uncorrected p = 0.005). For every fraction level, and for sharing nothing, the 95% confidence interval includes zero.
- **Practical size:** even the significant result is tiny: 0.35 percentage points of PDR, about 0.5% of the baseline. The largest average drop, sharing nothing, is 0.5 points. These effects are **statistically detectable in one case but practically negligible in all cases**.
- **Why "none" is not significant despite the largest drop:** with nothing shared, no phone can be ranked as a relay, so there is no forwarding at all. Outcomes then vary much more from seed to seed, and 11 of 30 seeds actually do *better* than full sharing.

**Why the effect is so small:** this matches the check-4 limitation in `ASSUMPTIONS.md` (§2.1, §2.7). Even with full sharing, ADRIN forwarding barely beats not forwarding at all (+0.006 PDR in the 10-seed validation). Restricting sharing can only hurt by weakening forwarding, so there is very little benefit left to lose.

The likely root cause is the model's granularity. Phones meet only within one of 5 borough-sized zones, and delivery mostly depends on whether a phone itself reaches Manhattan and makes contact. The paper uses a 0.07-mile radio range, where the choice of relay matters much more. So this result is **not evidence that location sharing is unimportant for ADRIN2.0.** It shows that this model, as currently set up, cannot produce a large effect either way.

**Proposal thresholds dropped.** The proposal's "acceptable" thresholds (PDR at least 90% of full sharing, latency at most 1.2×) are no longer used. Their 10% PDR margin is about 13 times larger than the biggest sharing effect measured, so every level, including sharing nothing, would pass. The paired differences and tests above replace them.

### Result 2: ADRIN's relay prediction adds real value (a separate question)

This compares ADRIN's ranked relay choice against picking relays at random, **both with full sharing**. It tests whether the prediction mechanism matters when there is a real relay decision to make. It says nothing about restricting sharing.

| Metric (30 paired seeds) | ADRIN ranked relays | Random relays | Seeds where random is worse | p (Wilcoxon) |
|---|---|---|---|---|
| PDR | **0.663** | 0.596 (−0.066 ± 0.005) | 30 / 30 | 2 × 10⁻⁶ |
| Packets sent | **2,617** | 63,208 (24× more) | 30 / 30 | 2 × 10⁻⁹ |
| Battery left | **54.98%** | 54.16% (−0.82 pp) | 30 / 30 | 2 × 10⁻⁹ |
| Mean latency, delivered messages only | 36.7 min | **34.1 min** (−2.6 ± 0.5) | 3 / 30 | 1 × 10⁻⁵ |

- **ADRIN wins on what matters:** it delivers more messages in every seed, with 24 times fewer transmissions and more battery left.
- **Random relays deliver slightly faster.** This is measured only over the messages each method delivers, and random delivers fewer of them, so the comparison is not like for like.
- **Why this matters for Step 4:** prediction is valuable when used. The weak sharing effect comes from forwarding having little to do in this model, not from the prediction being useless.

## Key assumptions and limitations

All of these are in `ASSUMPTIONS.md`, with evidence. The most important:

- **The paper's Eq. 5 is ambiguous.** Its worked example squares a single probability instead of taking a matrix power. Both are implemented, and a test shows that only `elementwise` reproduces the paper's arithmetic. The default is `matrix` because it is the mathematically correct one. In practice, the choice changes PDR by less than 0.005.
- **Forwarding barely helps yet.** Delivery now needs an actual base-station contact (0.1 per minute in Manhattan) rather than mere presence in the zone. That dropped PDR without forwarding from 0.862 to 0.632, but **ADRIN's advantage over not forwarding shrank to +0.006 (noise)**, and its lead over random forwarding stayed at about +0.07. Old vs new numbers are in `ASSUMPTIONS.md` §2.1.
- **Adding the expected contact wait to predictions changed nothing.** Predictions now include the expected 10-minute wait for a base-station contact (1 / 0.1). Every result is identical, because the same +10 is added to every prediction and phones only meet within one zone, so no ranking or comparison can change. Check 4 is **still weak** (+0.006), ADRIN vs random is still +0.067, and K = 1 vs K = 3 is still 0.638 vs 0.638. See `ASSUMPTIONS.md` §2.7.
- **The "more phones" trend is mostly a load effect.** Message load is network-wide, so more phones means less load per phone. At equal load per phone, PDR does not rise at every step (0.677 → 0.638 → 0.677).
- **K = 1 and K = 3 perform almost identically.** With handoff and the better-than-self rule, carriers rarely have several qualifying neighbours.
- **Energy figures rest on assumed durations.** Table 1 gives watts only. Continuous scanning and 1 s per packet are assumed, which leaves about 55% residual energy. Scanning dominates the budget, so routing choices barely move energy.
- **Contact probabilities (0.02 per pair per minute) are uncalibrated.**

## Not yet implemented

- **Step 4 follow-ups:** the `recent` policy (still rejected at config load); and repeating the sweep once forwarding has a meaningful effect in the model (see Result 1).
- **Centralized baselines** from the paper (`sliding_window` is still unused).
- **The written report.** The first figure exists (`sharing_sweep.png`); further graphs, such as the paper-trend comparisons, are not yet made.
- **Routing that accounts for time spent at the base station.** Predictions include a fixed expected wait for a contact. That had no effect, so the next idea is to rank phones by how long they are likely to stay in the base-station zone (see `ASSUMPTIONS.md` §2.7).
- **Calibration** of the contact and delivery model against the paper's Figs. 9–13. No parameter has been tuned.
