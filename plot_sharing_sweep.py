"""Plot a sharing sweep: PDR, latency and energy against how much is shared.

Run:  python plot_sharing_sweep.py results/sharing_sweep_<timestamp>
Writes sharing_sweep.png (3 panels) into that folder.

x axis = sharing ratio actually achieved (entries shared / entries known).
Error bars = ±1 standard error over seeds. These show seed-to-seed spread;
the paired (same-seed) comparisons in paired_tests.csv are much tighter.
The orange point is a routing reference (random relays, full sharing), not a
sharing level.
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from run_sharing_sweep import ROUTING_REFERENCE

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
ADRIN, RANDOM = "#2a78d6", "#eb6834"      # categorical slots 1 and 2

PANELS = [  # (column, axis label)
    ("pdr", "Packet delivery ratio"),
    ("latency_mean_min", "Mean latency (minutes, delivered only)"),
    ("energy_left_pct", "Battery left after 200 min (% of initial)"),
]
# Reference points: distinct marker shapes (named in the legend), so they never rely on colour alone.
REFERENCES = {
    "full": ("*", "full sharing (= fraction 1.0)"),
    "none": ("s", "no sharing (= fraction 0.0)"),
    "own_trace_only": ("^", "own trace only"),
}


def panel(ax, s, col, label):
    # Full- and no-sharing positions: light guides titled above the plot area.
    for x, text in ((0.0, "no sharing"), (1.0, "full sharing")):
        ax.axvline(x, color=GRID, lw=1, zorder=0)
        ax.text(x, 1.02, text, transform=ax.get_xaxis_transform(), ha="center", fontsize=9, color=INK)

    fractions = s[s.setting.str.startswith("fraction")].sort_values("sharing_ratio")
    ax.errorbar(fractions.sharing_ratio, fractions[col], yerr=fractions[col + "_se"],
                color=ADRIN, lw=2, marker="o", ms=6, capsize=3, elinewidth=1.2,
                label="ADRIN, fraction sweep", zorder=3)
    for name, (marker, text) in REFERENCES.items():
        r = s[s.setting == name].iloc[0]
        ax.errorbar(r.sharing_ratio, r[col], yerr=r[col + "_se"], color=ADRIN, marker=marker,
                    ms=14 if marker == "*" else 9, mfc=SURFACE if name == "own_trace_only" else ADRIN,
                    mec=ADRIN, mew=1.8, capsize=3, ls="none", zorder=4, label=text)
    rnd = s[s.setting == ROUTING_REFERENCE].iloc[0]
    ax.errorbar(rnd.sharing_ratio, rnd[col], yerr=rnd[col + "_se"], color=RANDOM, marker="X",
                ms=10, mec=SURFACE, mew=1, capsize=3, ls="none", zorder=4,
                label="routing reference: random relays (full sharing)")
    ax.annotate("random relays", (rnd.sharing_ratio, rnd[col]), xytext=(-10, 8),
                textcoords="offset points", fontsize=8, color=INK_2, ha="right", va="bottom")

    ax.set_xlabel("Sharing ratio (entries shared / entries known)", color=INK)
    ax.set_ylabel(label, color=INK)
    ax.set_xlim(-0.08, 1.08)
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(colors=INK_2, labelsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweep_dir", help="folder written by run_sharing_sweep.py")
    args = parser.parse_args()
    folder = Path(args.sweep_dir)
    s = pd.read_csv(folder / "summary.csv")
    n = int(s.n_seeds.min())

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.6), facecolor=SURFACE)
    for ax, (col, label) in zip(axes, PANELS):
        panel(ax, s, col, label)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.005, 0.925), frameon=False,
               fontsize=9, ncol=5, handletextpad=0.4, columnspacing=1.6)
    fig.suptitle(f"Restricting location sharing in ADRIN2.0 routing  ·  {n} seeds per setting, "
                 f"error bars ±1 standard error", x=0.01, ha="left", color=INK, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    out = folder / "sharing_sweep.png"
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
