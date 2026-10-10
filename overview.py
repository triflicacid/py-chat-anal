#!/usr/bin/env python3
"""Printed overview of an export: totals per user, daily activity, weekday and hour."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.summary import summarise

NEEDS = ()


def add_arguments(p) -> None:
    """Options for the printed overview."""
    g = p.add_argument_group("overview")
    g.add_argument("--csv", help="also save the per-user table to this CSV")


def run(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Print the overview, and save the per user table if a CSV was asked for."""
    per_user = summarise(df, args.users)
    if args.csv:
        per_user.to_csv(args.csv)
        print(f"\nPer-user table saved to {Path(args.csv).resolve()}")
    return per_user


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
