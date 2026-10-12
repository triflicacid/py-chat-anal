#!/usr/bin/env python3
"""Nudges each user sent over time, and each user's share of them.

A nudge is speaking again after --hours of no answer.

    python nudges.py
    python nudges.py --hours 2 --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.conversations import nudge_counts
from chatstats.loading import resolve_users
from chatstats.periods import PERIODS, unit
from chatstats.plotting import plot_lines

OUT = "out/nudges.png"
NEEDS = (cli.add_rolling_args,)


def add_arguments(p) -> None:
    """Options for the nudges chart."""
    g = p.add_argument_group("nudges")
    g.add_argument("--out", default=OUT, help="nudges chart file")
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the nudges chart (default W)")
    g.add_argument("--hours", type=float, default=1.0,
                   help="hours of no answer after which speaking again counts as a nudge")
    # A user can go weeks sending one nudge or none, so smooth unless told otherwise.
    p.set_defaults(rolling=4)


def plot_nudges(
    df: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "W",
    nudge_hours: float = 1.0,
    rolling: int = 0,
) -> Path:
    """Top: nudges sent per period by each user. Bottom: each user's share of them."""
    users = resolve_users(df, users)
    counts = nudge_counts(df, users, nudge_hours, period)
    totals = ", ".join(f"{u}: {counts[u].sum():,}" for u in users)
    return plot_lines(counts, f"Nudges per {unit(period).title()}", "Nudges sent", out,
                      rolling, period, share=True, smooth_share=True,
                      note=f"Nudge = message sent after {nudge_hours:g}h without a reply. "
                           f"Totals: {totals}")


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Draw the nudges chart."""
    return plot_nudges(df, a.users, a.out, a.period, a.hours, a.rolling)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
