#!/usr/bin/env python3
"""When in the day and week the messages land, and whether that changed over time.

Each column is normalised to its own month, so these are shares, not counts: raw
counts would restate the volume trend and hide the rhythm.

All users pooled; people talking to each other share a clock, so splitting them
gives near identical panels.

    python daily_rhythm.py
    python daily_rhythm.py --period W
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from chatstats import cli
from chatstats.counts import selected
from chatstats.loading import resolve_users
from chatstats.periods import PERIODS, period_grouper, unit
from chatstats.plotting import (chart_title, divider_positions, draw_dividers,
                                HEATMAP_CMAP, plt, save)
from chatstats.summary import WEEKDAYS

OUT = "out/daily_rhythm.png"
NEEDS = ()


def add_arguments(p) -> None:
    """Options for the daily rhythm chart."""
    g = p.add_argument_group("daily rhythm")
    g.add_argument("--out", default=OUT, help="daily rhythm chart file")
    g.add_argument("--period", choices=list(PERIODS), default="M",
                   help="column width on the heatmaps (default M)")


def rhythm_table(df: pd.DataFrame, users: list[str], period: str, by: str) -> pd.DataFrame:
    """Share of each period's messages falling in each hour, or on each weekday.

    Rows are the hour or weekday, columns the period. Every column sums to 100.
    """
    sub = selected(df, users)
    key = sub["Local"].dt.hour if by == "hour" else sub["Local"].dt.day_name()
    counts = sub.groupby([period_grouper(period), key]).size().unstack(fill_value=0)
    rows = range(24) if by == "hour" else WEEKDAYS
    counts = counts.reindex(columns=rows, fill_value=0).T
    return counts / counts.sum() * 100


def _heatmap(ax, table: pd.DataFrame, label: str, mark_peak: bool = True):
    """Draw one normalised table, and mark each column's busiest row."""
    values = table.to_numpy(dtype=float)
    mesh = ax.pcolormesh(np.arange(values.shape[1] + 1), np.arange(values.shape[0] + 1),
                         values, cmap=HEATMAP_CMAP, vmin=0, shading="flat")
    if mark_peak:
        # One direct label per column rather than a number in all 300 cells.
        for col in range(values.shape[1]):
            if values[:, col].any():
                ax.plot(col + 0.5, values[:, col].argmax() + 0.5, "o", markersize=4,
                        markerfacecolor="white", markeredgecolor="#0C3B37",
                        markeredgewidth=0.9)
    ax.set_yticks(np.arange(values.shape[0]) + 0.5)
    ax.set_ylabel(label)
    ax.set_xticks(np.arange(values.shape[1]) + 0.5)
    ax.set_xticklabels([d.strftime("%b '%y") for d in table.columns],
                       rotation=0, fontsize=8)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return mesh


def rhythm_summary(df: pd.DataFrame, users: list[str]) -> None:
    """Print how the shape of the day and week changed between the two halves.

    Halves, not first and last column: the range starts and ends mid month.
    """
    sub = selected(df, users)
    mid = sub["Date"].min() + (sub["Date"].max() - sub["Date"].min()) / 2
    halves = [("first half", sub[sub["Date"] < mid]), ("second half", sub[sub["Date"] >= mid])]
    span = " to ".join(f"{x['Date'].min():%b %y}" for _n, x in halves)

    print(f"\n=== Daily rhythm, {span} (share of each half's messages) ===")
    print(f"{'band':<18}{'first half':>12}{'second half':>13}{'change':>9}")
    bands = {"night 00-05": range(0, 6), "morning 06-11": range(6, 12),
             "afternoon 12-17": range(12, 18), "evening 18-23": range(18, 24)}
    for name, hrs in bands.items():
        a, b = (x["Local"].dt.hour.isin(hrs).mean() * 100 for _n, x in halves)
        print(f"{name:<18}{a:>11.1f}%{b:>12.1f}%{b - a:>+8.1f}")
    peaks = ", ".join(f"{n} {x['Local'].dt.hour.value_counts().idxmax():02d}:00"
                      for n, x in halves)
    print(f"busiest hour: {peaks}")

    print(f"\n{'weekday':<18}{'first half':>12}{'second half':>13}{'change':>9}")
    for day in WEEKDAYS:
        a, b = ((x["Local"].dt.day_name() == day).mean() * 100 for _n, x in halves)
        print(f"{day:<18}{a:>11.1f}%{b:>12.1f}%{b - a:>+8.1f}")


def plot_daily_rhythm(
    df: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "M",
) -> Path:
    """Two heatmaps: hour of day, and day of week, both against time."""
    users = resolve_users(df, users)
    hours = rhythm_table(df, users, period, "hour")
    days = rhythm_table(df, users, period, "weekday")
    fig, (top, bot) = plt.subplots(2, 1, figsize=(14, 9),
                                   gridspec_kw={"height_ratios": [24, 9], "hspace": 0.16})

    mesh = _heatmap(top, hours, "Hour of day")
    draw_dividers(top, divider_positions(hours.columns, period))
    top.set_yticklabels([f"{h:02d}" for h in hours.index], fontsize=7)
    chart_title(top, "Message Timing by Hour of Day and Day of Week",
                f"Each column is one {unit(period)}, normalised to its own total; "
                f"ring = that {unit(period)}'s busiest row")
    fig.colorbar(mesh, ax=top, pad=0.01, label="share of the month (%)")

    mesh = _heatmap(bot, days, "Day of week")
    draw_dividers(bot, divider_positions(days.columns, period), labels=False)
    bot.set_yticklabels(days.index, fontsize=8)
    fig.colorbar(mesh, ax=bot, pad=0.01, label="share of the month (%)")

    fig.tight_layout()
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the rhythm summary and draw the chart."""
    rhythm_summary(df, a.users)
    return plot_daily_rhythm(df, a.users, a.out, a.period)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
