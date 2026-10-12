#!/usr/bin/env python3
"""How long conversations last, by who started them, and the difference between the two.

Duration is first message to last. Only conversations more than one person took
part in are counted.

    python conversation_duration.py
    python conversation_duration.py --gap 4 --min-conversations 8
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from chatstats import cli
from chatstats.conversations import conversation_list, conversation_table
from chatstats.counts import windowed_stats
from chatstats.formatting import fmt_secs
from chatstats.periods import format_date_axis, unit
from chatstats.plotting import chart_title, narrow_date_axis, plt, save, user_colors

OUT = "out/conversation_duration.png"
NEEDS = (cli.add_conversation_args, cli.add_rolling_args)
# Tick values that read as round durations on a log axis.
NICE_SECONDS = [60, 120, 300, 600, 900, 1800, 3600, 2 * 3600, 3 * 3600, 6 * 3600, 12 * 3600]


def add_arguments(p) -> None:
    """Options for the conversation duration chart."""
    g = p.add_argument_group("conversation duration")
    g.add_argument("--out", default=OUT, help="conversation duration chart file")
    g.add_argument("--min-conversations", type=int, default=5,
                   help="leave a point blank where it rests on fewer conversations than this")
    # One user starts only a few conversations a week, too few for a steady median.
    p.set_defaults(rolling=4)


def answered(conv: pd.DataFrame) -> pd.DataFrame:
    """The conversations both users took part in, with who started each and its length."""
    convs = conversation_list(conv)
    convs = convs[convs["Users"] > 1].copy()
    convs["User"] = convs["Starter"]
    convs["Secs"] = convs["Mins"] * 60
    return convs


def duration_summary(convs: pd.DataFrame, everything: int, users: list[str], gap_hours: float) -> None:
    """Print how long conversations lasted, by who started them."""
    print(f"\n=== Conversation duration (new conversation after {gap_hours:g}h of silence) ===")
    print(f"{len(convs):,} of {everything:,} conversations were answered; the rest are left out")
    for u in users:
        x = convs.loc[convs["User"] == u, "Secs"]
        if x.empty:
            print(f"started by {u}: none")
            continue
        print(f"started by {u}: {len(x):,} conversations, median {fmt_secs(x.median())}, "
              f"middle half {fmt_secs(x.quantile(0.25))} to {fmt_secs(x.quantile(0.75))}, "
              f"longest {fmt_secs(x.max())}")


def plot_conversation_duration(
    convs: pd.DataFrame,
    span: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "W",
    rolling: int = 0,
    min_conversations: int = 5,
    gap_hours: float = 2.0,
) -> Path:
    """Top: median duration of each user's conversations, middle half shaded.
    Bottom: the first user's median minus the second's.

    The top row is log, since durations run from a minute to most of a day; the
    difference is in plain minutes.
    """
    stats = windowed_stats(convs, users, "Secs", period, rolling, min_conversations, span)
    colors = user_colors(users)
    compare = len(users) == 2
    fig = plt.figure(figsize=(9 * len(users), 6 + 3.5 * compare))
    grid = fig.add_gridspec(1 + compare, len(users), height_ratios=[3, 1.6][:1 + compare])
    tops = [fig.add_subplot(grid[0, 0])]
    tops += [fig.add_subplot(grid[0, k], sharey=tops[0]) for k in range(1, len(users))]

    for u, ax in zip(users, tops):
        median = stats["median"][u]
        ax.fill_between(median.index, stats["q25"][u], stats["q75"][u], color=colors[u],
                        alpha=0.15, linewidth=0)
        ax.plot(median.index, median, color=colors[u], linewidth=2)
        overall = convs.loc[convs["User"] == u, "Secs"]
        ax.set_title(f"Started by {u}  (median {fmt_secs(overall.median())})" if len(overall)
                     else f"Started by {u}", color=colors[u], fontsize=12, fontweight="bold")
        ax.set_yscale("log")
        format_date_axis(ax, median.index, period)
        if len(users) > 1:
            narrow_date_axis(ax)
    low, high = np.nanmin(stats["q25"].to_numpy()), np.nanmax(stats["q75"].to_numpy())
    if np.isfinite(low) and np.isfinite(high):
        tops[0].set_ylim(max(low * 0.8, 30), high * 1.25)
        tops[0].set_yticks([t for t in NICE_SECONDS if low * 0.8 <= t <= high * 1.25])
    tops[0].yaxis.set_major_formatter(plt.FuncFormatter(fmt_secs))
    tops[0].yaxis.set_minor_formatter(plt.NullFormatter())
    tops[0].set_ylabel("Median duration (log scale)")
    for ax in tops[1:]:
        ax.tick_params(axis="y", labelleft=False)

    if compare:
        first, second = users
        gap = (stats["median"][first] - stats["median"][second]) / 60
        ax = fig.add_subplot(grid[1, :])
        ax.fill_between(gap.index, 0, gap, where=gap >= 0, color=colors[first], alpha=0.6,
                        linewidth=0, interpolate=True)
        ax.fill_between(gap.index, 0, gap, where=gap <= 0, color=colors[second], alpha=0.6,
                        linewidth=0, interpolate=True)
        ax.plot(gap.index, gap, color="black", linewidth=0.8)
        ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.6)
        chart_title(ax, "Difference in Median Duration",
                    f"Above zero = conversations started by {first} lasted longer; "
                    f"below = those started by {second}")
        ax.set_ylabel("Difference (minutes)")
        format_date_axis(ax, gap.index, period)

    window = f" ({rolling}-{unit(period).title()} Window)" if rolling > 1 else ""
    fig.suptitle(f"Conversation Duration per {unit(period).title()}{window}", fontsize=13)
    fig.text(0.5, 0.012, f"Answered conversations only; new conversation after {gap_hours:g}h of "
                         "silence; band = middle half of conversations",
             ha="center", va="bottom", fontsize=9, color="dimgrey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the duration summary and draw the chart."""
    conv = conversation_table(df, a.users, a.gap)
    convs = answered(conv)
    duration_summary(convs, conv["ConvID"].nunique(), a.users, a.gap)
    return plot_conversation_duration(convs, conv, a.users, a.out, a.period, a.rolling,
                                      a.min_conversations, a.gap)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
