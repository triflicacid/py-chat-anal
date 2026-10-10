#!/usr/bin/env python3
"""How many messages each user sends in a row before the other one replies.

A run of messages by one person is a turn. This is the average length of a turn, so
1 means strict back and forth and a rising line means saying more before an answer.

    python messages_in_a_row.py --dir data
    python messages_in_a_row.py --dir data --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.conversations import turn_counts
from chatstats.counts import daily_counts
from chatstats.loading import DEFAULT_USERS
from chatstats.periods import PERIODS, format_date_axis, resample_counts, unit
from chatstats.plotting import (chart_title, legend_below, plt, rolling_line, rolling_sums,
                                save, user_colors)

OUT = "out/messages_in_a_row.png"
NEEDS = (cli.add_rolling_args,)


def add_arguments(p) -> None:
    """Options for the messages in a row chart."""
    g = p.add_argument_group("messages in a row")
    g.add_argument("--out", default=OUT, help="messages in a row chart file")
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the chart (default W)")
    g.add_argument("--min-turns", type=int, default=10,
                   help="leave the line blank where it rests on fewer turns than this")
    # One long run in a quiet week would otherwise set the whole line.
    p.set_defaults(rolling=4)


def plot_messages_in_a_row(
    df: pd.DataFrame,
    users: list[str] = DEFAULT_USERS,
    out: str | Path = OUT,
    period: str = "W",
    rolling: int = 0,
    min_turns: int = 10,
) -> Path:
    """Mean messages per turn per period for each user.

    Smoothed as rolling messages over rolling turns, which is the true average for
    the window. Averaging the weekly averages would weigh a quiet week like a busy one.
    """
    sent = resample_counts(daily_counts(df, users), period)
    turns = turn_counts(df, users, period).reindex(sent.index, fill_value=0)
    length = sent / turns.where(turns >= min_turns)
    window = rolling_sums(turns, rolling)
    smooth = rolling_sums(sent, rolling) / window.where(window >= min_turns)
    colors = user_colors(users)
    fig, ax = plt.subplots(figsize=(14, 6))

    for u in users:
        overall = sent[u].sum() / max(turns[u].sum(), 1)
        rolling_line(ax, length[u], colors[u], f"{u} (overall {overall:.2f})", rolling,
                     period, smooth[u])
    ax.axhline(1, color="black", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Messages in a row")
    chart_title(ax, f"Consecutive Messages Before a Reply per {unit(period).title()}",
                "Dashed line = strict alternation")
    format_date_axis(ax, sent.index, period)
    legend_below(ax, ncol=4)
    fig.tight_layout()
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Draw the messages in a row chart."""
    return plot_messages_in_a_row(df, a.users, a.out, a.period, a.rolling, a.min_turns)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
