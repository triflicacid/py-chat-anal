#!/usr/bin/env python3
"""Who has the last word: who sent the final message of each conversation.

The counterpart to initiators.py. The last word is the message followed by --gap
hours of silence, so having it means being the one left without an answer.

    python last_word.py --dir data
    python last_word.py --dir data --gap 4 --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.conversations import conversation_table, ender_counts
from chatstats.loading import DEFAULT_USERS
from chatstats.periods import unit
from chatstats.plotting import plot_lines

OUT = "out/last_word.png"
NEEDS = (cli.add_conversation_args, cli.add_rolling_args)


def add_arguments(p) -> None:
    """Options for the last word chart."""
    g = p.add_argument_group("who has the last word")
    g.add_argument("--out", default=OUT, help="last word chart file")
    # A share of a dozen conversations swings a long way on one of them.
    p.set_defaults(rolling=4)


def last_word_summary(counts: pd.DataFrame, users: list[str], gap_hours: float) -> None:
    """Print how many conversations each user ended."""
    print(f"\n=== Last word (the final message before {gap_hours:g}h of silence) ===")
    total = max(counts.to_numpy().sum(), 1)
    for u in users:
        print(f"{u}: ended {counts[u].sum():,} conversations ({counts[u].sum() / total * 100:.1f}%)")


def plot_last_word(
    counts: pd.DataFrame,
    out: str | Path = OUT,
    period: str = "W",
    gap_hours: float = 2.0,
    rolling: int = 0,
) -> Path:
    """Top: conversations ended per period by each user. Bottom: each user's share."""
    return plot_lines(counts, f"Conversation Endings per {unit(period).title()}",
                      "Conversations ended", out, rolling, period, share=True,
                      smooth_share=True,
                      note=f"Ending = final message before {gap_hours:g}h of silence")


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print who ends conversations and draw the chart."""
    counts = ender_counts(conversation_table(df, a.users, a.gap), a.users, a.period)
    last_word_summary(counts, a.users, a.gap)
    return plot_last_word(counts, a.out, a.period, a.gap, a.rolling)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
