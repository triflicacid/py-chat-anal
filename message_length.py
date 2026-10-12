#!/usr/bin/env python3
"""Average message length over time: words per message, for each user.

    python message_length.py
    python message_length.py --period M
    python message_length.py --text-only
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.counts import period_stats, selected
from chatstats.loading import resolve_users
from chatstats.periods import PERIODS, format_date_axis, unit
from chatstats.plotting import chart_title, legend_below, plt, save, user_colors

OUT = "out/message_length.png"
NEEDS = ()


def add_arguments(p) -> None:
    """Options for the message length chart."""
    g = p.add_argument_group("message length")
    g.add_argument("--out", default=OUT, help="message length chart file")
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the length chart (default W)")
    g.add_argument("--min-messages", type=int, default=10,
                   help="leave a period blank if it holds fewer messages than this")
    g.add_argument("--text-only", action="store_true",
                   help="ignore messages with no words at all, which are usually an "
                        "image or a link on its own")


def length_stats(
    df: pd.DataFrame,
    users: list[str] | None = None,
    period: str = "W",
    min_messages: int = 10,
    text_only: bool = False,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Per period length statistics, and the messages they were taken from."""
    users = resolve_users(df, users)
    sub = selected(df, users)
    if text_only:
        sub = sub[sub["WordCount"] > 0]
    return period_stats(sub, users, "WordCount", period, min_messages), sub


def length_summary(sub: pd.DataFrame, users: list[str]) -> None:
    """Print each user's message length, overall and at the extremes."""
    print("\n=== Message length (words per message) ===")
    print(f"{'user':<14}{'messages':>10}{'mean':>8}{'median':>8}{'q25':>6}{'q75':>6}"
          f"{'p95':>6}{'longest':>9}{'no words':>10}")
    for u in users:
        w = sub.loc[sub["User"] == u, "WordCount"]
        if w.empty:
            print(f"{u:<14}{'none':>10}")
            continue
        print(f"{u:<14}{len(w):>10,}{w.mean():>8.2f}{w.median():>8.0f}"
              f"{w.quantile(0.25):>6.0f}{w.quantile(0.75):>6.0f}{w.quantile(0.95):>6.0f}"
              f"{w.max():>9,}{(w == 0).sum():>10,}")


def plot_message_length(
    df: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "W",
    min_messages: int = 10,
    text_only: bool = False,
) -> Path:
    """Mean words per message per period, with the middle 50% of messages shaded."""
    users = resolve_users(df, users)
    stats, sub = length_stats(df, users, period, min_messages, text_only)
    colors = user_colors(users)
    fig, ax = plt.subplots(figsize=(14, 6))

    for u in users:
        mean = stats["mean"][u]
        ax.fill_between(mean.index, stats["q25"][u], stats["q75"][u],
                        color=colors[u], alpha=0.12, linewidth=0)
        overall = sub.loc[sub["User"] == u, "WordCount"]
        ax.plot(mean.index, mean, color=colors[u], linewidth=1.8,
                marker="o" if mean.notna().sum() <= 60 else None, markersize=3,
                label=f"{u} (overall {overall.mean():.2f} words, median {overall.median():.0f})")

    ax.set_ylim(bottom=0)
    ax.set_ylabel("Words per message")
    scope = "messages that contain words" if text_only else "all messages"
    chart_title(ax, f"Message Length per {unit(period).title()}",
                f"Line = mean, band = middle 50% of {scope}")
    format_date_axis(ax, stats["mean"].index, period)
    legend_below(ax, ncol=4)
    fig.tight_layout()
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the length summary and draw the chart."""
    _stats, sub = length_stats(df, a.users, a.period, a.min_messages, a.text_only)
    length_summary(sub, a.users)
    return plot_message_length(df, a.users, a.out, a.period,
                               a.min_messages, a.text_only)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
