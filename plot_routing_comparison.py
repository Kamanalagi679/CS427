"""Bar chart: ADRIN's ranked relays vs random relays (both with full sharing).

Run:  python plot_routing_comparison.py                      (newest results/*/routing_check.csv)
      python plot_routing_comparison.py path/to/routing_check.csv

Reads the routing_check.csv written by run_sharing_sweep.py and saves
results/routing_comparison.png (300 dpi): one panel per metric, because the
metrics have different units. Packets sent is left out (different scale).
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

RESULTS = Path(__file__).resolve().parent / "results"
OUTPUT = RESULTS / "routing_comparison.png"

# Same colours as plot_sharing_sweep.py, so ADRIN / random look alike in every figure.
ADRIN, RANDOM = "#2a78d6", "#eb6834"
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

# metric -> (panel title, y-axis label, number format for the bar labels)
PANELS = {
    "pdr": ("Packet delivery ratio (higher is better)", "Delivered / created", "{:.3f}"),
    "latency_mean_min": ("Mean latency (lower is better)", "Minutes (delivered messages only)", "{:.1f}"),
    "energy_left_pct": ("Battery left after 200 min (higher is better)", "% of initial energy", "{:.2f}%"),
}


def find_csv() -> Path:
    """CLI path if given, otherwise the newest results/<name>_<YYYYMMDD-HHMMSS>/routing_check.csv."""
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    found = list(RESULTS.glob("*/routing_check.csv"))
    if not found:
        sys.exit("No results/*/routing_check.csv found - run python run_sharing_sweep.py first.")
    # Folder names end in a sortable timestamp, e.g. sharing_sweep_20261012-202537.
    return max(found, key=lambda p: p.parent.name.rsplit("_", 1)[-1])


def main() -> int:
    csv = find_csv()
    data = pd.read_csv(csv).set_index("metric")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), facecolor=SURFACE)
    for ax, (metric, (title, ylabel, fmt)) in zip(axes, PANELS.items()):
        row = data.loc[metric]
        values = [row.adrin_mean, row.random_mean]

        # Two bars per panel, starting from zero so heights compare honestly.
        bars = ax.bar(["ADRIN", "Random"], values, color=[ADRIN, RANDOM], width=0.55)
        for bar, value in zip(bars, values):
            ax.annotate(fmt.format(value), (bar.get_x() + bar.get_width() / 2, value),
                        xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                        fontsize=10, color=INK)

        # The paired difference (same seeds) is the real test; show it under the title.
        ax.set_title(f"{title}\nrandom − ADRIN: {row.random_minus_adrin:+.3g} ± {row.se:.2g}"
                     f"  (Wilcoxon p = {row.wilcoxon_p:.1g})", fontsize=10, color=INK)
        ax.set_ylabel(ylabel, color=INK)
        ax.set_ylim(0, max(values) * 1.15)          # headroom for the value labels

        # Quiet axes and grid so the bars carry the message.
        ax.set_facecolor(SURFACE)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=INK_2)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)

    fig.suptitle("ADRIN vs Random Relay Routing Comparison (full sharing, 30 paired seeds)",
                 color=INK, fontsize=13)
    fig.tight_layout()
    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=300, facecolor=SURFACE)
    print(f"Read  {csv}")
    print(f"Saved {OUTPUT}")

    # Open a window only in an interactive session (python -i, IPython, Jupyter),
    # so a plain `python plot_routing_comparison.py` never blocks.
    if hasattr(sys, "ps1") or sys.flags.interactive or "ipykernel" in sys.modules:
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
