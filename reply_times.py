#!/usr/bin/env python3
"""Median reply time per week for each user, with the middle 50% shaded.

Counts only replies inside a conversation: anything slower than --gap is treated as a
new conversation rather than a slow reply. For the waits that cutoff discards, see
response_curve.py.

    python reply_times.py --dir data
    python reply_times.py --dir data --gap 3 --period M
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from chatstats import cli
from chatstats.conversations import conversation_table, reply_summary, reply_time_stats
from chatstats.formatting import fmt_secs
from chatstats.loading import DEFAULT_USERS
from chatstats.periods import format_date_axis, unit
from chatstats.plotting import chart_title, legend_below, plt, save, user_colors

OUT = "out/reply_times.png"
NEEDS = (cli.add_conversation_args,)

# Tick values that read as round durations on a log axis.
NICE_SECONDS = [1, 5, 10, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200,
                3 * 3600, 6 * 3600, 12 * 3600]


def add_arguments(p) -> None:
    """Options for the reply time chart."""
    g = p.add_argument_group("reply times")
    g.add_argument("--out", default=OUT, help="reply-time chart file")
    g.add_argument("--min-replies", type=int, default=3,
                   help="leave a period blank if it has fewer replies than this")


def plot_reply_times(
    conv: pd.DataFrame,
    users: list[str] = DEFAULT_USERS,
    out: str | Path = OUT,
    period: str = "W",
    min_replies: int = 3,
    gap_hours: float = 2.0,
) -> Path:
    """Median reply time per period for each user, with the middle 50% shaded. Log scale."""
    stats = reply_time_stats(conv, users, period, min_replies)
    colors = user_colors(users)
    fig, ax = plt.subplots(figsize=(14, 6))

    for u in users:
        med = stats["median"][u]
        ax.fill_between(med.index, stats["q25"][u], stats["q75"][u],
                        color=colors[u], alpha=0.12, linewidth=0)
        ax.plot(med.index, med, color=colors[u], linewidth=1.8,
                marker="o" if med.notna().sum() <= 60 else None, markersize=3,
                label=f"{u} (median {fmt_secs(conv.loc[conv['User'] == u, 'ReplySecs'].median())})")

    ax.set_yscale("log")
    lo = max(1, np.nanmin(stats["q25"].to_numpy()) * 0.8) if stats["q25"].notna().any().any() else 1
    hi = np.nanmax(stats["q75"].to_numpy()) * 1.3 if stats["q75"].notna().any().any() else 3600
    ax.set_ylim(lo, hi)
    ax.set_yticks([t for t in NICE_SECONDS if lo <= t <= hi])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(fmt_secs))
    ax.yaxis.set_minor_formatter(plt.NullFormatter())

    chart_title(ax, f"Reply Time per {unit(period).title()}",
                f"Line = median, band = middle 50%; replies within a {gap_hours:g}h conversation")
    ax.set_ylabel("Time to reply (log scale)")
    format_date_axis(ax, stats["median"].index, period)
    legend_below(ax, ncol=4)
    fig.tight_layout()
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the reply time summary and draw the chart."""
    conv = conversation_table(df, a.users, a.gap)
    reply_summary(conv, a.users)
    return plot_reply_times(conv, a.users, a.out, a.period,
                            a.min_replies, a.gap)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
