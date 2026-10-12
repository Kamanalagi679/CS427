# Setup Guide

This guide takes you from a fresh copy of the project to a verified, working simulation. You don't need to know the project beforehand. Every command goes in a terminal: **Terminal** on macOS, a shell on Linux, **PowerShell** on Windows.

> **Run every command from the project's top folder** (the one containing `run_experiment.py`). The scripts expect to be started from there.

---

## 1. Prerequisites

- **Python 3.10 is recommended.** The author's own environment uses 3.10.10.
  - The project does not pin a Python version anywhere. However, `requirements.txt` asks for `numpy>=2.0`, and NumPy 2.x needs **at least Python 3.9**. Older versions will fail to install.
- **pip.** It comes with Python.
- **About 5 minutes and an internet connection** to install the packages.

Check your Python version:

```bash
python3 --version        # macOS / Linux
python --version         # Windows
```

You should see `Python 3.9.x` or newer (ideally `3.10.x`). If the command isn't found, install Python from https://www.python.org/downloads/.

## 2. Create a virtual environment and install dependencies

A virtual environment is a private folder of packages for this project, so it doesn't affect anything else on your computer. The README calls it `venv`, so use the same name.

**macOS / Linux**

```bash
cd path/to/CS427                 # the folder that contains run_experiment.py
python3 -m venv venv             # create the environment (once)
source venv/bin/activate         # turn it on (every new terminal)
pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
cd path\to\CS427
python -m venv venv
venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

When the environment is active, your prompt starts with `(venv)`. While it's active, `python` means the environment's Python on every platform, so the rest of this guide just uses `python`.

`requirements.txt` installs:

| Package | Version | Used for |
|---|---|---|
| `simpy` | exactly 4.1.2 | the discrete-event simulation clock |
| `numpy` | ≥ 2.0 | all the arrays and random numbers |
| `pyyaml` | ≥ 6.0 | reading the config files |
| `pytest` | ≥ 7.0 | running the automatic tests |
| `pandas` | ≥ 2.0 | saving result tables and summarising the validation runs |
| `matplotlib` | ≥ 3.8 | drawing the sharing-experiment figure |
| `scipy` | ≥ 1.11 | the paired significance tests in the sharing experiment |

> If a `venv/` folder came with your copy of the project, it was made on someone else's machine and may not work on yours. Delete it and create a new one with the commands above.

## 3. Verify the project works

Run these five steps in order. Each one should succeed before you go on to the next.

### Step 1: Movement check

```bash
python validate_movement.py
```

**What it does:** Simulates 50 phones for 6000 minutes and checks that the way they move between the 5 zones matches the table in the paper (Fig. 7).

**Success looks like:** Two 5×5 tables of numbers (observed, then "Paper Fig. 7 (normalised)"), followed by:

```
Largest difference: 0.0xxx  (tolerance 0.02)
RESULT: PASS
```

The difference must be **0.02 or less**. The last line must say `RESULT: PASS`. If it says `RESULT: FAIL`, stop and report it.

### Step 2: Notebook check

```bash
python validate_notebooks.py
```

**What it does:** Checks that phones never "learn" anything false, and that what they learn approaches the paper's movement table. It also prints a preview of how much phones learn under each sharing policy. The README estimates about 10 seconds; slower machines may take longer.

**Success looks like** three sections and a final verdict:

- **A.** `A. Entries contradicting the real trace: 0  -> PASS`. The count must be **0**.
- **B.** A small table with rows for `200`, `1500` and `6000` minutes and two error columns. The errors shrink as the minutes increase. The section ends with `... -> PASS`. To pass, the **6000-minute row** must be below **0.01** in the "vs what happened" column and below **0.02** in the "vs paper Fig. 7" column.
- **C.** A preview table with 5 rows: `full`, `fraction 0.5`, `fraction 0.25`, `own_trace_only` and `none`. It is information only and does not affect PASS/FAIL. Sensible values:
  - `full` has a sharing ratio of `1.000`.
  - `none` has a sharing ratio of `0.000` and a coverage of `0.020` (1 out of 50 phones, i.e. only its own history).
  - The `fraction` rows share roughly 0.5 and 0.25.
  - Coverage falls as you go down from `full` to `none`.
- The last line must be `RESULT: PASS`.

### Step 3: Routing check

```bash
python validate_routing.py
```

**What it does:** Runs the full routing simulation with 10 different random seeds for each of several settings. It checks the **direction** of four trends from the paper:

1. More phones → more messages delivered.
2. Bigger buffers → more messages delivered.
3. Smart (ADRIN) forwarding beats random forwarding.
4. Forwarding beats not forwarding.

It does not check exact numbers, because the paper's code isn't public. It takes about 45 seconds.

**Success looks like:** A block of results per check, each ending in `-> PASS: ...`, then:

```
5/5 checks passed
RESULT: PASS
```

Check 4 currently passes but is marked `(weak: within seed-to-seed noise)`. That is expected, and explained in `ASSUMPTIONS.md` §2.1. Under check 1 there is also a "Caveat" block. It is information only and is explained in `ASSUMPTIONS.md`. For more seeds (slower, more reliable): `python validate_routing.py --seeds 30`.

### Step 4: Automatic tests

```bash
pytest
```

**What it does:** Runs the 54 tests in `tests/`. They cover config loading, movement, notebooks, routing (including the paper's worked example), messages, buffers, energy and the full simulation.

**Success looks like:** A line of dots, then a green summary ending in:

```
54 passed
```

To see each test's name, run `pytest -v`.

### Step 5: An example experiment

```bash
python run_experiment.py
```

**What it does:** Runs one 200-minute simulation with the default settings: 50 phones, full sharing, ADRIN routing, seed 0. It saves the results.

**Success looks like** this (numbers from a run of the current code, seed 0):

```
Config      : configs/default.yaml
Seed        : 0
Trace shape : (50, 201)  (nodes x minutes)
Sharing     : full (level 1.0)
Routing     : adrin, K=3, backtrack=matrix, handoff=True, better-than-self=True
Meetings    : 1147
Sharing ratio        : 1.000  (entries shared / available)
Notebook coverage    : 0.891  at minute 200
Messages             : 10050 created, 6053 delivered, 1311 dropped (buffer full at creation)
PDR                  : 0.602
Latency (delivered)  : mean 37.1 min, median 26.0 min
Energy left (mean)   : 54975 J  (55.0% of 100000 J)
Packets sent         : 2997
Phones died          : 0
Saved to    : /.../CS427/results/default_<date>-<time>
```

- **PDR** (packet delivery ratio) is the share of messages that reached the base station.
- **Latency** is how long the delivered messages took.
- The same seed always gives the same result on the same machine. A different NumPy version could change the numbers slightly.

**Files created** in the new `results/default_<date>-<time>/` folder:

| File | Contents |
|---|---|
| `config_used.yaml` | the exact settings used, so the run can be reproduced |
| `summary.csv` | one row: PDR, latency, energy, packets, drops, deaths |
| `messages.csv` | one row per message: `id,origin,created,delivered,delivered_by` (blank = never arrived) |
| `notebook_coverage.csv` | columns `minute,coverage`, one row every 5 minutes (0 to 200) |
| `mobility_trace.npy` | where every phone was every minute (a NumPy array, 50 × 201) |

## 4. Running a different experiment

All the settings live in `configs/default.yaml`. **An experiment file lists only the settings it changes.** Everything else comes from the default. Experiment files go in `configs/experiments/`.

To run the included example (50% of notebook entries shared per meeting):

```bash
python run_experiment.py --config configs/experiments/example_fraction_50.yaml
```

Expect `Sharing     : fraction (level 0.5)` and a sharing ratio of about `0.5`. The results go in `results/example_fraction_50_<date>-<time>/`, named after the config file.

**To make your own experiment**, copy the example and edit it:

```bash
cp configs/experiments/example_fraction_50.yaml configs/experiments/my_test.yaml
```

```yaml
# configs/experiments/my_test.yaml
sharing:
  policy: own_trace_only
simulation:
  seed: 3
```

```bash
python run_experiment.py --config configs/experiments/my_test.yaml
```

Things to know:

- **`--config` is the only option.** There is no `--seed` flag. To change the seed, set `simulation: seed:` in your experiment file.
- **Each run uses a single seed.** `n_runs: 30` in the default config is not used yet, so repeating over many seeds is not automated.
- **Sharing policies that work:** `full`, `fraction` (uses `level`, between 0.0 and 1.0), `own_trace_only` and `none`. **`recent` is not written yet.** The config loader rejects it straight away with a message saying so.
- **Routing settings** (under `network:`) that are useful to try:
  - `k_copies` (1 or 3 in the paper)
  - `buffer_size`
  - `forwarding: random` (a comparison point)
  - `backtrack_power: elementwise` (the paper's own arithmetic; see `ASSUMPTIONS.md`)
  - `handoff: false`
  - `require_better_than_self: false`
- **Settings that are read but not used yet:** `simulation.n_runs` and `network.sliding_window`. `contacts.base_station_prob_per_min` controls delivery: the chance per minute that a phone in the base-station zone actually reaches the base station.
- **A misspelled setting name** stops the run with an error such as `Problem in the 'sharing' section of the config: ...`.

## 5. Reproducing the sharing experiment (Step 4)

This is the project's main experiment: how much does delivery suffer when phones share less of their location history?

**1. Run the sweep** (about 2 minutes):

```bash
python run_sharing_sweep.py
```

It runs 9 settings, each on the same 30 random seeds (the number comes from `simulation.n_runs` in `configs/default.yaml`):

- full sharing;
- sharing a random 100%, 75%, 50%, 25% or 0% of the notebook;
- own trace only;
- nothing;
- random relays with full sharing, used as a routing reference.

**What you'll see:** progress lines (`done: full`, `done: fraction 1.0`, ...), then two tables:

- **"1. RESTRICTED SHARING vs FULL SHARING":** one row per sharing level. Each row shows the change in PDR compared with full sharing on the same seeds, its 95% confidence interval, and p-values.
- **"2. ROUTING REFERENCE":** ADRIN's ranked relays against random relays.

The run ends with `Saved to .../results/sharing_sweep_<date>-<time>` and the exact plot command to use next.

**2. Draw the figure:**

```bash
python plot_sharing_sweep.py results/sharing_sweep_<date>-<time>
```

Use the folder name printed by step 1. Expect `Saved results/sharing_sweep_<date>-<time>/sharing_sweep.png`: three panels showing PDR, latency and battery against how much is shared.

**Files in the sweep folder:**

| File | Contents |
|---|---|
| `raw.csv` | one row per setting and seed: every metric |
| `summary.csv` | per setting: mean and standard error of each metric |
| `paired_tests.csv` | per sharing level: PDR change vs full sharing, confidence interval, effect size, p-values |
| `routing_check.csv` | ADRIN vs random relays on PDR, latency, battery and packets |
| `sharing_sweep.png` | the figure |
| `config_used.yaml` | the base settings |

**Options:**

- `--seeds 10` gives a quicker but less precise run.
- `--reanalyse results/sharing_sweep_<date>-<time>` recomputes the statistics from an existing `raw.csv` without re-running the simulations.

How to interpret the numbers is explained in `PROJECT_STATUS.md` under "Step 4 results".

## 6. Project layout

```
CS427/
├── README.md              short project overview and quick start
├── PROJECT_STATUS.md      progress report (what is and isn't done)
├── SETUP_GUIDE.md         this file
├── ASSUMPTIONS.md         every choice the paper left open, and why
├── requirements.txt       Python packages to install
├── pytest.ini             tells pytest where the tests are
├── configs/
│   ├── default.yaml       every setting, each tagged [paper] or [assumption]
│   └── experiments/       small files that override only what changes
├── adrin_sim/             the simulation code (a Python package)
│   ├── config.py          reads and checks the YAML settings
│   ├── mobility.py        how phones move between zones
│   ├── notebook.py        each phone's record of where everyone has been
│   ├── node.py            the phone object
│   ├── contacts.py        which phones meet each minute
│   ├── sharing.py         what a phone shares when it meets another
│   ├── routing.py         picks which neighbours carry a message next
│   ├── messages.py        messages, buffers and delivery
│   ├── energy.py          batteries
│   ├── simulation.py      runs one simulation, calling the modules above
│   └── metrics.py         measures results (coverage, PDR, latency)
├── validate_movement.py   check 1: movement matches the paper
├── validate_notebooks.py  check 2: notebooks and meetings behave sensibly
├── validate_routing.py    check 3: routing shows the paper's trends
├── run_experiment.py      run one simulation from a config and save results
├── run_sharing_sweep.py   Step 4 experiment: all sharing levels x 30 seeds, with statistics
├── plot_sharing_sweep.py  draws the Step 4 figure from a sweep folder
├── tests/                 automatic tests (run with `pytest`)
└── results/               output folders from run_experiment.py and run_sharing_sweep.py
```

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'adrin_sim'` | You're not in the project's top folder. `cd` into it and try again. |
| `ModuleNotFoundError: No module named 'simpy'` (or `numpy`, `yaml`) | The virtual environment isn't active. Run `source venv/bin/activate` (or `venv\Scripts\Activate.ps1` on Windows), then `pip install -r requirements.txt`. |
| `python: command not found` | Use `python3`, or activate the virtual environment first. |
| `FileNotFoundError: Config file not found` | Check the path after `--config`. It's read relative to the folder you're in. |
| NumPy fails to install | Your Python is older than 3.9. Install a newer Python and recreate `venv`. |
