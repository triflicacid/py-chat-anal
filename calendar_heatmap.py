#!/usr/bin/env python3
"""Every day as one square, coloured by how many messages we sent on it.

Weeks run left to right and weekdays top to bottom, so a streak shows as a solid
block and a silence as a gap. The longest streak and the busiest day are marked.

    python calendar_heatmap.py --dir data
    python calendar_heatmap.py --dir data --out calendar.svg
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

from chatstats import cli
from chatstats.counts import daily_counts
from chatstats.formatting import fmt_date, fmt_span
from chatstats.loading import resolve_users
from chatstats.peaks import find_streaks
from chatstats.periods import plural
from chatstats.plotting import (chart_title, DIVIDER_COLOR, dividers, HEATMAP_CMAP,
                                PAIR_COLOR, plt, save)
from chatstats.summary import WEEKDAYS

OUT = "out/calendar_heatmap.png"
NEEDS = ()
SILENT_COLOR = "#E4E4E4"  # a day inside the range on which nobody said anything


def add_arguments(p) -> None:
    """Options for the calendar heatmap."""
    g = p.add_argument_group("calendar heatmap")
    g.add_argument("--out", default=OUT, help="calendar heatmap chart file")


def calendar_grid(daily: pd.Series) -> tuple[np.ndarray, pd.Timestamp]:
    """Daily totals laid out as weekday rows by week columns.

    Returns the grid and the Monday its first column starts on. Days outside the
    range are NaN, which keeps them apart from days inside it that were silent.
    """
    monday = daily.index[0] - pd.Timedelta(days=daily.index[0].weekday())
    days_in = (daily.index - monday).days
    grid = np.full((7, days_in.max() // 7 + 1), np.nan)
    # A log scale has no place for zero, so a silent day is held just under one
    # message, where the colour map's "under" colour picks it up.
    grid[days_in % 7, days_in // 7] = daily.where(daily > 0, 0.5).to_numpy()
    return grid, monday


def streak_summary(streaks: list[tuple], daily: pd.Series) -> None:
    """Print the longest streaks and the busiest day."""
    print("\n=== Longest streaks (days in a row with at least one message) ===")
    for i, (start, end, length, msgs) in enumerate(streaks, 1):
        print(f"#{i}: {fmt_span(start, end, 'D')}  ({plural(length, 'D')}, {msgs:,} msgs)")
    print(f"Busiest day: {fmt_date(daily.idxmax(), 'D')} ({daily.max():,} msgs)")


def plot_calendar_heatmap(
    df: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
) -> Path:
    """One strip of squares for the whole range, on a log colour scale.

    Log, because the busiest day holds over a thousand messages and a typical one a
    few dozen. On a linear scale every ordinary day would be the same pale square.
    """
    users = resolve_users(df, users)
    daily = daily_counts(df, users).sum(axis=1)
    grid, monday = calendar_grid(daily)
    weeks = grid.shape[1]
    streaks = find_streaks(daily)
    streak_summary(streaks, daily)

    cmap = HEATMAP_CMAP.with_extremes(under=SILENT_COLOR, bad="white")
    fig, ax = plt.subplots(figsize=(max(8.0, weeks * 0.25 + 1.6), 3.6))
    mesh = ax.pcolormesh(np.arange(weeks + 1), np.arange(8), grid, cmap=cmap,
                         norm=LogNorm(vmin=1, vmax=max(daily.max(), 10)),
                         edgecolors="white", linewidth=1.2)

    def cell(date: pd.Timestamp) -> tuple[float, float]:
        """Centre of a date's square, as (x, y)."""
        days_in = (date - monday).days
        return days_in // 7 + 0.5, days_in % 7 + 0.5

    ax.plot(*cell(daily.idxmax()), "o", markersize=6, markerfacecolor="none",
            markeredgecolor="white", markeredgewidth=1.4)
    note = f"Ring: busiest day ({daily.max():,} on {fmt_date(daily.idxmax(), 'D')})"
    if streaks:
        start, end, length, _msgs = streaks[0]
        left, right = cell(start)[0] - 0.5, cell(end)[0] + 0.5
        ax.plot([left, right], [7.45, 7.45], color=PAIR_COLOR, linewidth=1.5, clip_on=False)
        ax.text((left + right) / 2, 7.75, f"longest streak: {plural(length, 'D')} in a row, "
                f"{fmt_span(start, end, 'D')}", ha="center", va="top", fontsize=8.5,
                color=PAIR_COLOR)
    # A day here is a square, not a point on an axis, so a divider is an outline.
    marked = [(date, label) for date, label in dividers()
              if daily.index[0] <= date <= daily.index[-1]]
    for date, _label in marked:
        x, y = cell(date)
        ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, fill=False, zorder=5,
                                   edgecolor=DIVIDER_COLOR, linewidth=2))
    if marked:
        note += ". Outlined: " + ", ".join(f"{label} {fmt_date(date, 'D')}".lstrip()
                                           for date, label in marked)
    chart_title(ax, "Messages per Day", note, lift=16)

    # A month is labelled over the week its first day falls in.
    firsts = pd.date_range(daily.index[0], daily.index[-1], freq="MS")
    ax.set_xticks([cell(d)[0] for d in firsts])
    ax.set_xticklabels([d.strftime("%b '%y") for d in firsts], fontsize=8)
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(7) + 0.5)
    ax.set_yticklabels([d[:3] for d in WEEKDAYS], fontsize=8)
    ax.set_ylim(7, 0)  # Monday on top
    ax.set_aspect("equal")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(mesh, ax=ax, pad=0.015, shrink=0.75, label="messages that day")
    bar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:,.0f}"))
    bar.outline.set_visible(False)
    fig.tight_layout()
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the streaks and draw the calendar."""
    return plot_calendar_heatmap(df, a.users, a.out)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
