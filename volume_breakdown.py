#!/usr/bin/env python3
"""Words per week for each user, split into the three things that make it up.

Words written is conversations held, times messages sent in each, times words in each
message. The top panel is the total and the three under it are the factors, so a
change in how much was said can be put down to talking less often, to shorter
conversations, or to shorter messages.

    python volume_breakdown.py --dir data
    python volume_breakdown.py --dir data --gap 4
    python volume_breakdown.py --dir data --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.conversations import conversation_list, conversation_table, initiator_counts
from chatstats.counts import daily_counts, daily_words
from chatstats.loading import resolve_users
from chatstats.periods import resample_counts, unit
from chatstats.plotting import (PAIR_COLOR, chart_title, legend_under_figure, plt, rolling_line,
                                rolling_sums, save, stack_date_axis, user_colors)

OUT = "out/volume_breakdown.png"
NEEDS = (cli.add_conversation_args, cli.add_rolling_args)


def add_arguments(p) -> None:
    """Options for the volume breakdown chart."""
    g = p.add_argument_group("volume breakdown")
    g.add_argument("--out", default=OUT, help="volume breakdown chart file")
    g.add_argument("--min-messages", type=int, default=10,
                   help="leave words per message blank where it rests on fewer messages")
    # Smoothed by default, so that the panels read as trends rather than weeks.
    p.set_defaults(rolling=4)


def halves_summary(conv: pd.DataFrame, gap_hours: float) -> None:
    """Print the two halves of the date range side by side, so the trend is explicit."""
    convs = conversation_list(conv)
    midpoint = convs["Date"].min() + (convs["Date"].max() - convs["Date"].min()) / 2
    print(f"\n=== Conversations (new conversation after {gap_hours:g}h of silence) ===")
    print(f"{'period':<26}{'convos':>8}{'per day':>9}{'median msgs':>13}"
          f"{'median mins':>13}{'messages':>10}")
    halves = [("first half", convs[convs["Date"] < midpoint]),
              ("second half", convs[convs["Date"] >= midpoint]),
              ("whole range", convs)]
    for name, x in halves:
        if x.empty:
            continue
        days = (x["Date"].max() - x["Date"].min()).days + 1
        label = f"{name} ({x['Date'].min():%b %y} to {x['Date'].max():%b %y})"
        print(f"{label:<26}{len(x):>8,}{len(x) / days:>9.2f}{x['Msgs'].median():>13.0f}"
              f"{x['Mins'].median():>13.0f}{x['Msgs'].sum():>10,}")


def plot_volume_breakdown(
    df: pd.DataFrame,
    conv: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "W",
    rolling: int = 0,
    min_messages: int = 10,
    gap_hours: float = 2.0,
) -> Path:
    """Four stacked panels: words, then the three factors that multiply to give it.

    Conversations belong to both of us, so that panel has one line; the others have
    one per user. Each ratio is smoothed as one rolling sum over another, which is
    the true average for the window and keeps the panels multiplying back to the
    top one. Averaging the weekly ratios would weigh a quiet week like a busy one.
    """
    users = resolve_users(df, users)
    words = resample_counts(daily_words(df, users), period)
    sent = resample_counts(daily_counts(df, users), period)
    held = initiator_counts(conv, users, period).sum(axis=1).reindex(words.index, fill_value=0)
    window_sent, window_held = rolling_sums(sent, rolling), rolling_sums(held, rolling)

    per_conversation = sent.div(held.where(held > 0), axis=0)
    smooth_per_conversation = window_sent.div(window_held.where(window_held > 0), axis=0)
    length = words / sent.where(sent >= min_messages)
    smooth_length = rolling_sums(words, rolling) / window_sent.where(window_sent >= min_messages)

    colors = user_colors(users)
    noun = unit(period)
    fig, axs = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    top, frequency, size, wordy = axs

    for u in users:
        rolling_line(top, words[u], colors[u], u, rolling, period)
        rolling_line(size, per_conversation[u], colors[u], u, rolling, period,
                     smooth_per_conversation[u])
        rolling_line(wordy, length[u], colors[u], u, rolling, period, smooth_length[u])
    rolling_line(frequency, held, PAIR_COLOR, "conversations", rolling, period)
    top.set_ylabel(f"Words per {noun}")
    frequency.set_ylabel(f"Conversations per {noun}")
    size.set_ylabel("Messages per conversation")
    wordy.set_ylabel("Words per message")
    chart_title(top, f"Message Volume Breakdown per {noun.title()}",
                "Words = conversations x messages per conversation x words per message; "
                f"new conversation after {gap_hours:g}h of silence")
    for ax in axs:
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:,.0f}"))

    stack_date_axis(list(axs), words.index, period)
    legend_under_figure(fig, top)
    fig.tight_layout(rect=(0, 0.035, 1, 1))  # leave room for the legend under the panels
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the conversation summary and draw the chart."""
    conv = conversation_table(df, a.users, a.gap)
    halves_summary(conv, a.gap)
    return plot_volume_breakdown(df, conv, a.users, a.out, a.period, a.rolling,
                                 a.min_messages, a.gap)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
