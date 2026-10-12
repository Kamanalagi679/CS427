# CS427: Restricted Location Sharing in ADRIN2.0

Simulation study of how limiting the location information phones share
affects mobility-informed routing in post-disaster networks. Based on
Halder et al., "ADRIN2.0", IEEE Access 12 (2024).

## Layout

    configs/default.yaml      all settings (each tagged [paper] or [assumption])
    configs/experiments/      small files that change only what differs
    adrin_sim/                the simulation code, one file per job
      config.py               loads and checks the YAML
      mobility.py             movement model            (Step 1, done)
      notebook.py             the notebook table + merge (Step 2, done)
      node.py                 phones                    (Step 2, done)
      contacts.py             who meets whom            (Step 2, done)
      sharing.py              sharing policies          (Step 2; 'recent' is Step 4)
      routing.py              ADRIN2.0 forwarding       (Step 3, done: full-sharing baseline)
      messages.py             messages, buffers, delivery (Step 3, done)
      energy.py               batteries                 (Step 3, done)
      simulation.py           conductor: calls the others in order
      metrics.py              notebook coverage, PDR, latency
    validate_movement.py      check movement matches the paper
    validate_notebooks.py     check notebooks/meetings behave sensibly
    validate_routing.py       check routing shows the paper's trends
    run_experiment.py         run a simulation from a config, save results
    run_sharing_sweep.py      Step 4: every sharing level x 30 seeds, plus paired statistics
    plot_sharing_sweep.py     figure of PDR / latency / energy vs sharing ratio
    ASSUMPTIONS.md            every choice the paper left open, and why
    tests/                    automatic checks (pytest)
    results/                  output of runs (one folder per run)

This folder is not a git repository.

## Quick start (Mac)

    python3 -m venv venv             # first time only
    source venv/bin/activate
    pip install -r requirements.txt
    python validate_movement.py      # expect RESULT: PASS
    python validate_notebooks.py     # expect RESULT: PASS (about 10 seconds)
    python validate_routing.py       # expect RESULT: PASS (about 45 seconds)
    pytest                           # expect 54 passed
    python run_experiment.py         # runs and saves to results/

## Reproduce the sharing experiment (Step 4)

    python run_sharing_sweep.py      # about 2 minutes; prints the paired tests,
                                     # saves results/sharing_sweep_<timestamp>/
    python plot_sharing_sweep.py results/sharing_sweep_<timestamp>
                                     # writes sharing_sweep.png into that folder
    python run_sharing_sweep.py --reanalyse results/sharing_sweep_<timestamp>
                                     # redo the statistics from raw.csv, no simulation

Results and how to read them: PROJECT_STATUS.md ("Step 4 results").

See SETUP_GUIDE.md for a step-by-step version.

## How the pieces talk

    YAML  ->  config.py  ->  Config object  ->  simulation.py
                                                 |-> mobility.py   (who is where)
                                                 |-> node.py       (notebooks)
                                                 |-> contacts.py   (meetings)
                                                 |-> sharing.py    (what is shared)
                                                 |-> messages.py   (buffers, delivery)
                                                 |-> routing.py    (forwarding)
                                                 |-> energy.py     (batteries)
                                                 '-> metrics.py    (results)
