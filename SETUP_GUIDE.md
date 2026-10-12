# Setup Guide

Run every command from the project's top folder (the one containing `run_experiment.py`).

## Prerequisites
- Python 3.9+ (3.10 recommended — `requirements.txt` needs numpy>=2.0, which requires at least 3.9)
- pip (comes with Python)

Check your version:
```bash
python3 --version   # macOS / Linux
python --version    # Windows
```

## Install

**macOS / Linux**
```bash
cd path/to/CS427
python3 -m venv venv
source venv/bin/activate
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

If a `venv/` folder came with your copy, delete it and make a fresh one — it won't work across machines.

## Run, in order

```bash
python validate_movement.py      # expect: RESULT: PASS
python validate_notebooks.py     # expect: RESULT: PASS (~10s)
python validate_routing.py       # expect: RESULT: PASS (~45s)
pytest                           # expect: 54 passed
python run_experiment.py         # one sanity-check run -> results/default_<timestamp>/
python run_sharing_sweep.py      # the main experiment, ~2 min -> results/sharing_sweep_<timestamp>/
python plot_sharing_sweep.py results/sharing_sweep_<timestamp>   # draws the figure
```

For what each check proves and exact expected output, see `DEMO.md`. For how to interpret the sharing-sweep numbers, see `PROJECT_STATUS.md`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'adrin_sim'` | You're not in the project's top folder. |
| `ModuleNotFoundError: No module named 'simpy'` (or numpy, yaml) | venv isn't active — activate it, then `pip install -r requirements.txt`. |
| `python: command not found` | Use `python3`, or activate the venv. |
| `FileNotFoundError: Config file not found` | Check the `--config` path — it's relative to your current folder. |
| NumPy fails to install | Python is older than 3.9 — upgrade and recreate the venv. |