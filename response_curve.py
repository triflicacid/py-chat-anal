#!/usr/bin/env python3
"""Replying in a conversation vs waiting for one, split at --gap.

Top panel: how fast each person answers while the other is still there.
Bottom panel: how long the waits run once nobody is, and who breaks the silence.

Unlike reply_times.py this keeps every handover, including the overnight ones.

    python response_curve.py --dir data
    python response_curve.py --dir data --gap 4 --nudge-hours 2
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from chatstats import cli
from chatstats.conversations import handover_times, response_summary
from chatstats.formatting import fmt_secs
from chatstats.loading import DEFAULT_USERS
from chatstats.plotting import chart_title, plt, save, user_colors

OUT = "out/response_curve.png"
NEEDS = (cli.add_gap_args,)

# Reference times marked on the top panel, in seconds.
CURVE_TICKS = [1, 5, 10, 30, 60, 300, 900, 3600, 3 * 3600, 6 * 3600, 12 * 3600,
               24 * 3600, 48 * 3600]
# Upper edges of the wait buckets on the bottom panel, in hours.
WAIT_BUCKETS = (3, 6, 12, 24)


def add_arguments(p) -> None:
    """Options for the response curve chart."""
    g = p.add_argument_group("replying vs waiting")
    g.add_argument("--out", default=OUT,
                   help="response-curve chart: share still waiting vs elapsed time")
    g.add_argument("--nudge-hours", type=float, default=1.0,
                   help="hours of no answer after which speaking again counts as a nudge")


def _survival(x: np.ndarray) -> np.ndarray:
    """Share of waits still outstanding after each observed time, as a percentage."""
    return (1.0 - np.arange(1, len(x) + 1) / len(x)) * 100


def _draw_replies(ax, quick: pd.DataFrame, users: list[str], colors: dict[str, str],
                  cut: float, gap_hours: float, n_all: int) -> None:
    """Top panel: the volley, as a survival curve per responder."""
    positive = quick.loc[quick["Secs"] > 0, "Secs"]
    lo = max(0.5, positive.min()) if not positive.empty else 1.0
    for k, u in enumerate(users):
        x = np.sort(quick.loc[quick["Responder"] == u, "Secs"].to_numpy(dtype=float))
        if not len(x):
            continue
        ax.step(np.concatenate([[lo], x]), np.concatenate([[100.0], _survival(x)]),
                where="post", color=colors[u], linewidth=1.9, zorder=3,
                label=f"{u} replies ({len(x):,}; median {fmt_secs(np.median(x))}, "
                      f"1 in 10 over {fmt_secs(np.quantile(x, 0.9))})")
        for share in (50, 10):
            t = np.quantile(x, 1 - share / 100)
            ax.plot([t], [share], "o", color=colors[u], markersize=5, zorder=4)
            # Stack by user: the two curves often cross a line at the same time.
            ax.annotate(fmt_secs(t), xy=(t, share), xytext=(0, 8 + 13 * k),
                        textcoords="offset points", ha="center", fontsize=7.5,
                        color=colors[u], zorder=5,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                  ec=colors[u], lw=0.6, alpha=0.9))

    for share, text in ((50, "half still waiting"), (10, "1 in 10 still waiting")):
        ax.axhline(share, color="black", linewidth=0.7, linestyle="--", alpha=0.45, zorder=2)
        ax.text(cut, share + 1, text, ha="right", va="bottom", fontsize=7.5)

    ax.set_xscale("log")
    ax.set_xlim(lo, cut)
    ax.set_ylim(0, 100)
    ax.set_xticks([t for t in CURVE_TICKS if lo <= t <= cut])
    ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt_secs))
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    ax.grid(True, which="major", alpha=0.35)
    ax.grid(True, which="minor", axis="x", alpha=0.12)
    ax.set_xlabel("Time since the message (log scale)")
    ax.set_ylabel("Share still waiting for a reply")
    chart_title(ax, "Reply Time Distribution Within Conversations",
                f"{len(quick):,} handovers answered inside {gap_hours:g}h "
                f"({len(quick) / max(n_all, 1) * 100:.1f}% of all)")
    ax.legend(loc="lower left", frameon=False, fontsize=9)


def _draw_waits(ax, waits: pd.DataFrame, users: list[str], colors: dict[str, str],
                cut: float, gap_hours: float, nudge_hours: float, n_all: int) -> None:
    """Bottom panel: how long the waits ran, and how often the waiter spoke first."""
    bounds = [cut] + [h * 3600 for h in WAIT_BUCKETS if h * 3600 > cut] + [np.inf]
    edges = list(zip(bounds, bounds[1:]))
    names = [f"over {fmt_secs(a)}" if np.isinf(b) else f"{fmt_secs(a)} to {fmt_secs(b)}"
             for a, b in edges]
    spot = np.arange(len(names))
    w = 0.8 / max(len(users), 1)

    for k, u in enumerate(users):
        mine = waits[waits["Waiter"] == u]
        off = (k - (len(users) - 1) / 2) * w
        in_bin = [(mine["Secs"] > a) & (mine["Secs"] <= b) for a, b in edges]
        total = [int(m.sum()) for m in in_bin]
        nudged = [int((m & (mine["Nudges"] > 0)).sum()) for m in in_bin]
        ax.bar(spot + off, total, w, color=colors[u], alpha=0.30, linewidth=0, zorder=2,
               label=f"{u} waited ({len(mine):,})")
        ax.bar(spot + off, nudged, w, color=colors[u], alpha=0.95, linewidth=0, zorder=3,
               label=f"{u} nudged while waiting ({int((mine['Nudges'] > 0).sum()):,})")
        for xx, t in zip(spot + off, total):
            if t:
                ax.text(xx, t, f"{t:,}", ha="center", va="bottom", fontsize=7.5,
                        color=colors[u], zorder=4)

    # Headroom so the legend never lands on the tallest bar.
    ax.set_ylim(top=max(ax.get_ylim()[1], 1) * 1.42)
    ax.set_xticks(spot)
    ax.set_xticklabels(names)
    ax.set_ylabel("Number of waits")
    ax.set_xlabel("How long the wait ran")
    ax.grid(True, axis="y", alpha=0.35)
    ax.set_axisbelow(True)
    chart_title(ax, f"Wait Duration Beyond {gap_hours:g}h",
                f"{len(waits):,} waits ({len(waits) / max(n_all, 1) * 100:.1f}% of all); "
                f"solid = waiter sent another message after {nudge_hours:g}h without a reply")
    ax.legend(loc="upper right", frameon=False, fontsize=9, ncol=len(users))


def _draw_footer(fig, hand: pd.DataFrame, users: list[str], colors: dict[str, str],
                 nudge_hours: float) -> None:
    """Every handover again, from the waiting side.

    Fixed-width columns in a monospace font, every row padded to one length, so
    centring each row on the figure still lines the columns up.
    """
    rows = []
    for u in users:
        x = hand.loc[hand["Waiter"] == u]
        if x.empty:
            continue
        long = x.loc[x["Secs"] > 3600, "Secs"]
        med = fmt_secs(long.median()) if len(long) else "n/a"
        rows.append((u, f"{u:<12}{len(x):>7,} waits {len(long):>5,} over 1h "
                        f"({len(long) / len(x) * 100:>4.1f}%) "
                        f"median of those {med:>6} {int(x['Nudges'].sum()):>5,} nudges"))
    width = max((len(r) for _, r in rows), default=0)
    fig.text(0.5, 0.082, "Waiting: every handover from the other side "
                         f"(nudge = spoke again after {nudge_hours:g}h of no answer)",
             ha="center", va="bottom", fontsize=8.5, color="dimgrey")
    for i, (u, row) in enumerate(rows):
        fig.text(0.5, 0.052 - i * 0.024, row.ljust(width), ha="center", va="bottom",
                 fontsize=8.5, family="monospace", color=colors[u])


def plot_response_curve(
    hand: pd.DataFrame,
    users: list[str] = DEFAULT_USERS,
    out: str | Path = OUT,
    gap_hours: float = 2.0,
    nudge_hours: float = 1.0,
) -> Path:
    """Two panels over the same handovers, split at the conversation gap.

    They are split because one regime otherwise hides the other: the overwhelming
    majority of handovers land inside the gap, so on a single axis every wait is
    squeezed into an invisible tail.
    """
    cut = gap_hours * 3600
    colors = user_colors(users)
    fig, (top, bot) = plt.subplots(2, 1, figsize=(13, 12),
                                   gridspec_kw={"height_ratios": [3, 2], "hspace": 0.30})

    _draw_replies(top, hand[hand["Secs"] <= cut], users, colors, cut, gap_hours, len(hand))
    _draw_waits(bot, hand[hand["Secs"] > cut], users, colors, cut, gap_hours,
                nudge_hours, len(hand))

    fig.tight_layout(rect=(0, 0.12, 1, 1))
    # tight_layout under-reserves against a fixed hspace, so pin the margin that
    # keeps the lower panel's x-label clear of the footer.
    fig.subplots_adjust(bottom=0.145)
    _draw_footer(fig, hand, users, colors, nudge_hours)
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the response and waiting summaries, then draw the chart."""
    hand = handover_times(df, a.users, a.nudge_hours)
    response_summary(hand, a.users, a.nudge_hours)
    return plot_response_curve(hand, a.users, a.out, a.gap, a.nudge_hours)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
