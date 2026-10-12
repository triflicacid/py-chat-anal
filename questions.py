#!/usr/bin/env python3
"""Questions each user asked over time, and each user's share of them.

A question is a message that holds a question mark or is worded as one ("how are
you", "did it go ok", "... is it"). The wording matters: one of us leaves the mark
off most questions, so counting marks alone badly undercounts them.

    python questions.py --dir data
    python questions.py --dir data --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.counts import daily_questions
from chatstats.periods import PERIODS, resample_counts, unit
from chatstats.plotting import plot_lines

OUT = "out/questions.png"
NEEDS = (cli.add_rolling_args,)


def add_arguments(p) -> None:
    """Options for the questions chart."""
    g = p.add_argument_group("questions")
    g.add_argument("--out", default=OUT, help="questions chart file")
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the questions chart (default W)")
    # A quiet week holds only a handful of questions from either user.
    p.set_defaults(rolling=4)


def questions_summary(counts: pd.DataFrame, users: list[str]) -> None:
    """Print how many questions each user asked."""
    print("\n=== Questions asked (a question mark, or worded as a question) ===")
    total = max(counts.to_numpy().sum(), 1)
    for u in users:
        print(f"{u}: {counts[u].sum():,} ({counts[u].sum() / total * 100:.1f}%)")


def plot_questions(
    counts: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "W",
    rolling: int = 0,
) -> Path:
    """Top: questions asked per period by each user. Bottom: each user's share of them."""
    totals = ", ".join(f"{u}: {counts[u].sum():,}" for u in users)
    return plot_lines(counts, f"Questions Asked per {unit(period).title()}", "Questions asked",
                      out, rolling, period, share=True, smooth_share=True,
                      note=f"Question = question mark or question wording. Totals: {totals}")


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Print the totals and draw the questions chart."""
    counts = resample_counts(daily_questions(df, a.users), a.period)
    questions_summary(counts, a.users)
    return plot_questions(counts, a.users, a.out, a.period, a.rolling)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
