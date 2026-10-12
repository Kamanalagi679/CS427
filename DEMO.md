# Live Demo Script

Run top to bottom from the project folder. Each block can be copied and pasted as it is.

## 0. Activate the environment

```bash
cd ~/CS427 && source venv/bin/activate
```

## 1. Proof of rigour: validation (about 1 minute in total)

```bash
python validate_movement.py
```
**Proves:** simulated movement matches the paper's Fig. 7 transition table.
**Expect:** `Largest difference: 0.0041  (tolerance 0.02)`, then `RESULT: PASS`.

```bash
python validate_notebooks.py
```
**Proves:** phones never learn anything false, and what they learn converges to the paper's movement table.
**Expect:** checks A and B each print `PASS`, then `RESULT: PASS`. Takes about 12 s.

```bash
python validate_routing.py
```
**Proves:** routing reproduces the paper's trend directions over 10 seeds: more phones, bigger buffers, ranked vs random relays, and forwarding vs none.
**Expect:** `5/5 checks passed`, then `RESULT: PASS`. Takes about 45 s.
**Note:** check 4 is marked `(weak: within seed-to-seed noise)`. That is expected and documented: forwarding barely beats no forwarding in this zone-level model.

```bash
pytest
```
**Proves:** 54 unit and integration tests pass. They include the paper's Eq. 5 worked example, the buffer and energy limits, and reproducibility.
**Expect:** `54 passed`. Takes about 3 s.

## 2. Main event: the sharing sweep (about 1.6 minutes)

```bash
python run_sharing_sweep.py
```
**What it runs:** 9 settings × 30 seeds. With no flags it uses `n_runs: 30` from `configs/default.yaml`; this is the same as `--seeds 30`.

**Expect, in order:**

1. `first setting took 11s -> whole sweep about 1.6 min`
2. `done: full`, `done: fraction 1.0`, ..., `done: random (full)`
3. **Table 1, restricted sharing vs full sharing.** Each level's change in PDR on the same seeds, with p-values. Only `own_trace_only` is significant after correction (Holm p 0.026, −0.0035 PDR). Every level costs under 1% of baseline delivery.
4. **Table 2, the routing reference.** ADRIN delivers 0.663 vs random's 0.596, and random sends 24× more packets. ADRIN wins on delivery in 30 of 30 seeds.
5. `Saved to .../results/sharing_sweep_<date>-<time>`, holding `raw.csv`, `summary.csv`, `paired_tests.csv`, `routing_check.csv` and `config_used.yaml`.

The seeds are fixed, so the numbers match the saved run exactly.

Then draw and open the figure from the folder just created:

```bash
python plot_sharing_sweep.py "$(ls -d results/sharing_sweep_* | tail -1)"
open "$(ls -d results/sharing_sweep_* | tail -1)/sharing_sweep.png"
```
**Expect:** `Saved results/sharing_sweep_<date>-<time>/sharing_sweep.png`. It has three panels, PDR, latency and battery against sharing ratio, with full and no sharing marked.

## Fallback: skip the live run (instant)

If time is short, recompute every statistic from the saved 30-seed data, then show the saved figure:

```bash
python run_sharing_sweep.py --reanalyse results/sharing_sweep_20261012-202537
open results/sharing_sweep_20261012-202537/sharing_sweep.png
```
**Expect:** the same two tables as step 2, item 3 onwards, in under a second. The output ends with `Rewrote summary.csv, paired_tests.csv, routing_check.csv in results/sharing_sweep_20261012-202537`.
