#!/usr/bin/env python3
"""What each user talked about over time, from a list of topics and their words.

One chart per user, side by side, with a heatmap under them of where two differ.

Topics live in topics.toml, a file of names and word lists.

    python topics.py
    python topics.py --topics my_topics.toml --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from chatstats import cli
from chatstats.periods import PERIODS, format_date_axis, period_end, unit
from chatstats.plotting import (chart_title, diverging_cmap, legend_under_figure,
                                narrow_date_axis, plt, rolling_line, rolling_sums, save,
                                TOPIC_COLORS, user_colors)
from chatstats.topics import TOPICS_FILE, load_topics, topic_counts_by_user

OUT = "out/topics.png"
NEEDS = (cli.add_rolling_args,)
PEAK_MIN_MENTIONS = 10  # mentions a month needs before the summary will call it a peak


def add_arguments(p) -> None:
    """Options for the topics chart."""
    g = p.add_argument_group("topics")
    g.add_argument("--out", default=OUT, help="topics chart file")
    g.add_argument("--topics", default=TOPICS_FILE,
                   help=f"file of topic names and their words (default {TOPICS_FILE})")
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the chart (default W)")
    g.add_argument("--min-mentions", type=int, default=10,
                   help="leave a user's mix blank where it rests on fewer topic mentions")
    # A week holds too few mentions of any one topic to give a steady share.
    p.set_defaults(rolling=4)


def topics_summary(user: str, counts: pd.DataFrame, names: list[str]) -> None:
    """Print how often one user raised each topic, and the month it peaked in."""
    monthly = counts.resample("MS").sum()
    share = monthly[names].div(monthly["messages"].where(monthly["messages"] > 0), axis=0)
    print(f"\n=== Topics: {user} (messages mentioning each) ===")
    print(f"{'topic':<20}{'messages':>10}{'of all':>8}   peak month")
    for name in sorted(names, key=lambda n: -counts[n].sum()):
        line = (f"{name:<20}{counts[name].sum():>10,}"
                f"{counts[name].sum() / max(counts['messages'].sum(), 1) * 100:>7.1f}%   ")
        # A month with few mentions can top the shares by chance.
        steady = share[name][monthly[name] >= PEAK_MIN_MENTIONS]
        if steady.empty:
            print(line + "too few mentions to say")
            continue
        print(line + f"{steady.idxmax():%b %Y} ({steady.max() * 100:.1f}% of that month)")
    print(f"{'any topic':<20}{counts['any'].sum():>10,}"
          f"{counts['any'].sum() / max(counts['messages'].sum(), 1) * 100:>7.1f}%")


def topic_mix(window: pd.DataFrame, names: list[str], min_mentions: int) -> pd.DataFrame:
    """Each topic's share of one user's topic mentions per period, out of 100.

    Periods under `min_mentions` are left blank.
    """
    mentions = window[names].sum(axis=1)
    return window[names].div(mentions.where(mentions >= min_mentions), axis=0) * 100


def _draw_mix(ax, mix: pd.DataFrame, period: str) -> None:
    """Stacked areas: one user's mix of topics, out of 100%."""
    # Repeat the last row at the end of its period, or the final bucket has no width.
    end = period_end(mix.index[-1], period)
    mix = pd.concat([mix, mix.iloc[[-1]].set_axis([end])])
    base = pd.Series(0.0, index=mix.index)
    for i, name in enumerate(mix.columns):
        upper = base + mix[name]
        ax.fill_between(mix.index, base, upper, color=TOPIC_COLORS[i % len(TOPIC_COLORS)],
                        alpha=0.85, linewidth=0, step="post", label=name)
        base = upper
    ax.set_ylim(0, 100)


def _draw_difference(fig, ax, mixes: dict[str, pd.DataFrame], colors: dict[str, str],
                     period: str) -> None:
    """Heatmap of the gap between two users' mixes: a row per topic, a column per period.

    Each cell is the first user's share of a topic minus the second's, in points.
    """
    first, second = mixes
    gap = (mixes[first] - mixes[second]).T
    edges = mdates.date2num(list(gap.columns) + [period_end(gap.columns[-1], period)])
    # The scale stops short of the largest gap, so one freak week cannot wash out the rest.
    limit = max(5.0, float(np.ceil(np.nanpercentile(np.abs(gap.to_numpy()), 98) / 5) * 5))
    mesh = ax.pcolormesh(edges, np.arange(len(gap) + 1), gap.to_numpy(),
                         cmap=diverging_cmap(colors[second], colors[first]),
                         vmin=-limit, vmax=limit, edgecolors="white", linewidth=0.3)
    ax.set_ylim(len(gap), 0)  # topics in the order of the legend, first at the top
    ax.set_yticks(np.arange(len(gap)) + 0.5)
    ax.set_yticklabels(gap.index, fontsize=9)
    ax.tick_params(axis="y", length=0)
    chart_title(ax, "Difference in Topic Share",
                "Colour = the user for whom the topic made up more of their own topic mentions")
    format_date_axis(ax, gap.columns, period)
    ax.grid(False)
    bar = fig.colorbar(mesh, ax=ax, pad=0.01, ticks=[-limit, 0, limit])
    bar.ax.set_yticklabels([f"{second}\n+{limit:.0f} points", "equal",
                            f"{first}\n+{limit:.0f} points"], fontsize=8)
    bar.outline.set_visible(False)


def plot_topics(
    tables: dict[str, pd.DataFrame],
    names: list[str],
    out: str | Path = OUT,
    period: str = "W",
    rolling: int = 0,
    min_mentions: int = 10,
) -> Path:
    """Top: each user's mix of topics. Middle: where the two differ. Bottom: coverage.

    The top row is the mix out of 100%, the bottom row the share of all talk the
    topics cover. The middle row needs exactly two users and is left out otherwise.
    """
    colors = user_colors(tables)
    compare = len(tables) == 2
    heights = [3, 1.7, 1] if compare else [3, 1]
    fig = plt.figure(figsize=(9 * len(tables), 9 + 4 * compare))
    grid = fig.add_gridspec(len(heights), len(tables), height_ratios=heights)
    tops = [fig.add_subplot(grid[0, 0])]
    tops += [fig.add_subplot(grid[0, k], sharey=tops[0]) for k in range(1, len(tables))]
    bottom = fig.add_subplot(grid[-1, :])

    mixes = {}
    for (user, counts), top in zip(tables.items(), tops):
        window = rolling_sums(counts, rolling)
        mixes[user] = topic_mix(window, names, min_mentions)
        _draw_mix(top, mixes[user], period)
        top.set_title(user, color=colors[user], fontsize=12, fontweight="bold")
        format_date_axis(top, counts.index, period)
        if len(tables) > 1:
            narrow_date_axis(top)

        coverage = counts["any"] / counts["messages"].where(counts["messages"] > 0) * 100
        smooth = window["any"] / window["messages"].where(window["messages"] > 0) * 100
        rolling_line(bottom, coverage, colors[user], user, rolling, period, smooth)
    for ax in tops[1:]:
        ax.tick_params(axis="y", labelleft=False)
    tops[0].set_ylabel("Share of own topic mentions (%)")
    chart_title(bottom, "Messages Mentioning Any Listed Topic")
    bottom.set_ylabel("Share of own messages (%)")
    bottom.set_ylim(bottom=0)
    format_date_axis(bottom, next(iter(tables.values())).index, period)
    bottom.legend(loc="lower right", frameon=False, fontsize=9, ncol=len(tables))
    if compare:
        _draw_difference(fig, fig.add_subplot(grid[1, :]), mixes, colors, period)

    smoothing = f" ({rolling}-{unit(period).title()} Window)" if rolling > 1 else ""
    fig.suptitle(f"Topic Share per {unit(period).title()}{smoothing}", fontsize=13)
    legend_under_figure(fig, tops[0], ncol=6)
    fig.tight_layout(rect=(0, 0.05, 1, 1))  # leave room for the legend under the panels
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Read the topic file, print each user's summary and draw the chart."""
    topics = load_topics(a.topics)
    tables = topic_counts_by_user(df, topics, a.users, a.period)
    for user, counts in tables.items():
        topics_summary(user, counts, list(topics))
    return plot_topics(tables, list(topics), a.out, a.period, a.rolling, a.min_mentions)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
