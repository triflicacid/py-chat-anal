#!/usr/bin/env python3
"""How often each user says a given word or phrase, over time. One panel per word.

With more than one word, the first panel adds them all together.

Produces nothing unless --words is given.

    python word_usage.py --words dear love
    python word_usage.py --words "love you" --period M --mode messages
    python word_usage.py --words love --partial   # also "lovely", "loved"
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.counts import daily_word_counts, word_usage_table
from chatstats.loading import resolve_users
from chatstats.periods import PERIODS, format_date_axis, resample_counts, unit
from chatstats.plotting import (legend_under_figure, narrow_date_axis, plt, rolling_line, save,
                                user_colors)

OUT = "out/word_usage.png"
NEEDS = (cli.add_rolling_args,)
# The most panels placed side by side, and the size of each one in inches.
MAX_COLUMNS = 3
PANEL_WIDTH = {1: 14.0, 2: 7.5, 3: 6.0}
PANEL_HEIGHT = {1: 6.0, 2: 4.2, 3: 3.8}


def add_arguments(p) -> None:
    """Options for the word chart."""
    g = p.add_argument_group("word usage")
    g.add_argument("--words", nargs="+", default=[],
                   help='words/phrases to chart, e.g. --words dear love "love you"')
    g.add_argument("--out", default=OUT, help="word usage chart file")
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the word chart (default W: daily counts are mostly zeros)")
    g.add_argument("--mode", choices=["count", "messages"], default="count",
                   help="count every occurrence, or count messages containing the word")
    g.add_argument("--partial", action="store_true",
                   help='match inside words too ("love" also matches "lovely")')
    g.add_argument("--columns", type=int,
                   help=f"panels per row (default: as many as fit, up to {MAX_COLUMNS})")
    g.add_argument("--csv",
                   help="also save per-word counts (one column per word/user) to this CSV")


def word_tables(
    df: pd.DataFrame,
    words: list[str],
    users: list[str] | None = None,
    period: str = "W",
    mode: str = "count",
    partial: bool = False,
) -> dict[str, pd.DataFrame]:
    """Uses of each word per period per user, keyed by the word."""
    users = resolve_users(df, users)
    return {w: resample_counts(daily_word_counts(df, w, users, mode, partial), period)
            for w in words}


def plot_word_usage(
    tables: dict[str, pd.DataFrame],
    users: list[str] | None = None,
    out: str | Path = OUT,
    rolling: int = 0,
    period: str = "W",
    mode: str = "count",
    columns: int | None = None,
) -> Path:
    """A grid of line charts, one per word, sharing a date axis and one legend.

    Each panel keeps its own y axis, or a common word would flatten a rare one.
    With more than one word, a panel summing all of them comes first.
    """
    users = resolve_users(tables, users)
    panels = {f'"{word}"': counts for word, counts in tables.items()}
    if len(tables) > 1:
        panels = {f"All {len(tables)} Words Combined": sum(tables.values()), **panels}
    ncols = max(1, min(columns or MAX_COLUMNS, len(panels)))
    nrows = math.ceil(len(panels) / ncols)
    size = min(ncols, MAX_COLUMNS)
    colors = user_colors(users)
    fig, axs = plt.subplots(nrows, ncols, sharex=True, squeeze=False,
                            figsize=(PANEL_WIDTH[size] * ncols, PANEL_HEIGHT[size] * nrows + 1.0))
    cells = list(axs.flat)
    what = "Uses" if mode == "count" else "Messages containing it"

    for ax, (name, counts) in zip(cells, panels.items()):
        for u in users:
            rolling_line(ax, counts[u], colors[u], u, rolling, period)
        totals = ", ".join(f"{u}: {counts[u].sum():,}" for u in users)
        ax.set_title(f"{name}  ({totals})", fontsize=11 if ncols == 1 else 10)
        ax.set_ylim(bottom=0)
        format_date_axis(ax, counts.index, period)
        if ncols > 1:
            narrow_date_axis(ax)
    for ax in cells[len(panels):]:
        ax.set_visible(False)
    # sharex hides tick labels above the last row, so a short column loses them.
    # Turn them back on for the lowest panel in each.
    for col in range(ncols):
        shown = [axs[row, col] for row in range(nrows) if row * ncols + col < len(panels)]
        shown[-1].tick_params(axis="x", which="both", labelbottom=True)
    for row in axs:
        row[0].set_ylabel(f"{what} per {unit(period)}")

    legend_under_figure(fig, cells[0])
    fig.tight_layout(rect=(0, 0.5 / fig.get_figheight(), 1, 1))  # room for the legend
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path | None:
    """Print the totals table and draw the grid of panels."""
    if not a.words:
        return None

    print("\n=== Word usage ===")
    print(word_usage_table(df, a.words, a.users, a.partial).to_string())
    print()

    tables = word_tables(df, a.words, a.users, a.period, a.mode, a.partial)
    if a.csv:
        combined = pd.concat(tables, axis=1)
        combined.columns = [f"{w}|{u}" for w, u in combined.columns]
        combined.to_csv(a.csv)
        print(f"Word counts saved to {Path(a.csv).resolve()}")
    return plot_word_usage(tables, a.users, a.out, a.rolling, a.period, a.mode, a.columns)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
