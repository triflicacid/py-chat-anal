#!/usr/bin/env python3
"""Who starts the conversation, and who sends the first message of the day.

    python initiators.py --dir data
    python initiators.py --dir data --gap 3 --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.conversations import (conversation_table, first_of_day_counts,
                                     initiator_counts, starter_summary)
from chatstats.periods import unit
from chatstats.plotting import (chart_title, legend_under_figure, plt, rolling_line,
                                rolling_sums, save, share_panel, stack_date_axis,
                                user_colors)

OUT = "out/initiators.png"
NEEDS = (cli.add_conversation_args, cli.add_rolling_args)


def add_arguments(p) -> None:
    """Options for the who starts chart."""
    g = p.add_argument_group("who starts conversations")
    g.add_argument("--out", default=OUT, help="who-starts chart file")
    g.add_argument("--day-start", type=float, default=5.0,
                   help="local hour at which a new day begins for the first-message "
                        "panel (default 5, so a 1am message belongs to the night before)")
    # Weekly starts are small numbers, and a share of them swings a long way on one
    # conversation, so this chart is smoothed unless told otherwise.
    p.set_defaults(rolling=4)


def first_of_day_summary(first: pd.DataFrame, users: list[str], day_start: float) -> None:
    """Print how many days each user opened."""
    print(f"\n=== First message of the day (day starts at {day_start:g}:00) ===")
    days = max(first.to_numpy().sum(), 1)
    for u in users:
        print(f"{u}: {first[u].sum():,} days ({first[u].sum() / days * 100:.1f}%)")


def plot_initiators(
    conv: pd.DataFrame,
    first: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "W",
    gap_hours: float = 2.0,
    rolling: int = 0,
) -> Path:
    """Top: conversations started per period by each user. Middle: each user's share
    of them. Bottom: each user's share of the days they were first to speak."""
    counts = initiator_counts(conv, users, period)
    colors = user_colors(users)
    fig, (top, middle, bottom) = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                                              gridspec_kw={"height_ratios": [2, 1, 1]})

    for u in users:
        rolling_line(top, counts[u], colors[u],
                     f"{u} ({counts[u].sum():,} started, "
                     f"{counts[u].sum() / max(counts.to_numpy().sum(), 1) * 100:.0f}%)",
                     rolling, period)
    top.set_ylim(bottom=0)
    top.set_ylabel(f"Conversations started per {unit(period)}")
    chart_title(top, f"Conversation Initiation per {unit(period).title()}",
                f"New conversation after {gap_hours:g}h of silence")

    share_panel(middle, rolling_sums(counts, rolling), period, ylabel="Share started (%)")
    share_panel(bottom, rolling_sums(first, rolling), period,
                ylabel="Sent the day's\nfirst message (%)")

    stack_date_axis([top, middle, bottom], counts.index, period)
    legend_under_figure(fig, top)
    fig.tight_layout(rect=(0, 0.04, 1, 1))  # leave room for the legend under the panels
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print who starts and who speaks first each day, then draw the chart."""
    conv = conversation_table(df, a.users, a.gap)
    starter_summary(conv, a.users, a.gap)
    first = first_of_day_counts(df, a.users, a.period, a.day_start)
    first_of_day_summary(first, a.users, a.day_start)
    return plot_initiators(conv, first, a.users, a.out, a.period, a.gap,
                           a.rolling)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
