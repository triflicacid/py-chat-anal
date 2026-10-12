#!/usr/bin/env python3
"""The words that set each month apart from the rest of the history.

A word is listed under a month when it was said several times more often then than
at any other time. Nothing is told what to look for, so this finds topics a word
list would miss, and shows which words are worth adding to topics.toml.

    python distinctive_words.py --dir data
    python distinctive_words.py --dir data --top 12 --min-ratio 2
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

from chatstats import cli
from chatstats.counts import period_words
from chatstats.formatting import fmt_date
from chatstats.periods import PERIODS, unit
from chatstats.plotting import (chart_title, divider_positions, draw_dividers,
                                HEATMAP_CMAP, plt, save)

OUT = "out/distinctive_words.png"
NEEDS = ()
RATIO_CAP = 30.0  # the colour scale stops here, so one freak word does not wash out the rest


def add_arguments(p) -> None:
    """Options for the distinctive words chart."""
    g = p.add_argument_group("distinctive words")
    g.add_argument("--out", default=OUT, help="distinctive words chart file")
    g.add_argument("--period", choices=list(PERIODS), default="M",
                   help="how long each row covers (default M)")
    g.add_argument("--top", type=int, default=8, help="most words to list per row (default 8)")
    g.add_argument("--min-uses", type=int, default=8,
                   help="ignore a word said fewer times than this in the period")
    g.add_argument("--min-ratio", type=float, default=3.0,
                   help="how many times more common than elsewhere a word must be (default 3)")


def words_summary(found: dict[pd.Timestamp, pd.Series], period: str) -> None:
    """Print each period's words, with how many times more common each was."""
    print(f"\n=== Distinctive words per {unit(period)} (times more common than elsewhere) ===")
    for start, scores in found.items():
        words = ", ".join(f"{w} ({s:.0f}x)" for w, s in scores.items()) or "nothing stood out"
        print(f"{fmt_date(start, period)}: {words}")


def plot_distinctive_words(
    found: dict[pd.Timestamp, pd.Series],
    out: str | Path = OUT,
    period: str = "M",
    top: int = 8,
    min_ratio: float = 3.0,
) -> Path:
    """A grid of words: one row per period, strongest word first, coloured by strength."""
    grid = np.full((len(found), top), np.nan)
    for row, scores in enumerate(found.values()):
        grid[row, :len(scores)] = scores.to_numpy()
    norm = LogNorm(vmin=min(max(min_ratio, 1.0), RATIO_CAP / 2), vmax=RATIO_CAP, clip=True)
    fig, ax = plt.subplots(figsize=(14, 0.48 * len(found) + 1.6))
    mesh = ax.pcolormesh(np.arange(top + 1), np.arange(len(found) + 1), grid,
                         cmap=HEATMAP_CMAP.with_extremes(bad="white"), norm=norm,
                         edgecolors="white", linewidth=1.5)

    for row, scores in enumerate(found.values()):
        for col, (word, score) in enumerate(scores.items()):
            ax.text(col + 0.5, row + 0.5, word, ha="center", va="center", fontsize=9.5,
                    color="white" if norm(score) > 0.5 else "#0C3B37")
    ax.set_ylim(len(found), 0)
    ax.set_yticks(np.arange(len(found)) + 0.5)
    ax.set_yticklabels([d.strftime("%b '%y") if period == "M" else fmt_date(d, period)
                        for d in found], fontsize=9)
    ax.set_xticks([])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    chart_title(ax, f"Distinctive Words per {unit(period).title()}",
                "Most distinctive first")
    # Time runs down this chart, so the dividers lie across it. Each is moved to the
    # nearest edge of its row, because a line through the middle strikes the words out.
    marks = divider_positions(pd.DatetimeIndex(list(found)), period)
    draw_dividers(ax, [(round(pos), label) for pos, label in marks], vertical=False)
    bar = fig.colorbar(mesh, ax=ax, pad=0.015,
                       label=f"times more common than in every other {unit(period)}")
    bar.set_ticks([t for t in (2, 3, 5, 10, 20, 30) if norm.vmin <= t <= RATIO_CAP])
    bar.ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _p: f"{v:.0f}x+" if v >= RATIO_CAP else f"{v:.0f}x"))
    bar.ax.yaxis.set_minor_formatter(plt.NullFormatter())
    bar.outline.set_visible(False)
    fig.tight_layout()
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Find each period's words, print them and draw the grid."""
    found = period_words(df, a.users, a.period, a.top, a.min_uses, a.min_ratio)
    words_summary(found, a.period)
    return plot_distinctive_words(found, a.out, a.period, a.top, a.min_ratio)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
