#!/usr/bin/env python3
"""Links each user shared over time, and each user's share of them.

    python links.py --dir data
    python links.py --dir data --period M --rolling 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.counts import daily_links
from chatstats.loading import resolve_users
from chatstats.periods import PERIODS, resample_counts, unit
from chatstats.plotting import plot_lines

OUT = "out/links.png"
NEEDS = (cli.add_rolling_args,)


def add_arguments(p) -> None:
    """Options for the links chart."""
    g = p.add_argument_group("links shared")
    g.add_argument("--out", default=OUT, help="links chart file")
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the links chart (default W)")
    # A handful of links a week is too few to read raw.
    p.set_defaults(rolling=4)


def plot_links(
    df: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    period: str = "W",
    rolling: int = 0,
) -> Path:
    """Top: links sent per period by each user. Bottom: each user's share of them."""
    users = resolve_users(df, users)
    counts = resample_counts(daily_links(df, users), period)
    totals = ", ".join(f"{u}: {counts[u].sum():,}" for u in users)
    return plot_lines(counts, f"Links Shared per {unit(period).title()}", "Links sent", out,
                      rolling, period, share=True, smooth_share=True, note=f"Totals: {totals}")


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Draw the links chart."""
    return plot_links(df, a.users, a.out, a.period, a.rolling)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
