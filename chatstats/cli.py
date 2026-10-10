"""Shared command line: the options more than one script needs."""
from __future__ import annotations

import argparse
import sys
from typing import Callable, Iterable

import pandas as pd

from .loading import DEFAULT_TZ, DEFAULT_USERS, FILE_GLOB, load_messages
from .periods import PERIODS
from .plotting import show_dividers

AddArguments = Callable[[argparse.ArgumentParser], None]


def use_utf8_console() -> None:
    """The summaries print characters a legacy console codepage cannot encode."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def base_parser(doc: str | None = None) -> argparse.ArgumentParser:
    """A parser with the options every script needs."""
    p = argparse.ArgumentParser(description=doc,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_argument_group("input")
    g.add_argument("--dir", default=".", help="folder containing the export CSVs")
    g.add_argument("--pattern", default=FILE_GLOB, help="filename glob")
    g.add_argument("--users", nargs="+", default=DEFAULT_USERS, help="usernames to compare")
    g.add_argument("--tz", default=DEFAULT_TZ,
                   help="timezone the export's wall-clock times are in, used for local "
                        f"day/hour buckets (default {DEFAULT_TZ})")
    p.add_argument("--relationship-dividers", action="store_true",
                   help="mark the days we got together and broke up on the chart")
    return p


def add_rolling_args(p: argparse.ArgumentParser) -> None:
    """Smoothing, shared by the two line charts."""
    p.add_argument("--rolling", type=int, default=0,
                   help="rolling-average window, in periods (0 = raw)")


def add_gap_args(p: argparse.ArgumentParser) -> argparse._ArgumentGroup:
    """What counts as one conversation, for the scripts with no date axis."""
    g = p.add_argument_group("conversations")
    g.add_argument("--gap", type=float, default=2.0,
                   help="hours of silence that end a conversation (default 2)")
    return g


def add_conversation_args(p: argparse.ArgumentParser) -> None:
    """What counts as one conversation, and the bucket to chart it in."""
    g = add_gap_args(p)
    g.add_argument("--period", choices=list(PERIODS), default="W",
                   help="bucket for the chart's date axis (default W)")


def run_chart(
    needs: Iterable[AddArguments],
    add_arguments: AddArguments,
    run: Callable[[pd.DataFrame, argparse.Namespace], object],
    doc: str | None,
    argv: list[str] | None = None,
) -> None:
    """Entry point shared by every script: parse, load, hand over to `run`."""
    use_utf8_console()
    p = base_parser(doc)
    for add in needs:
        add(p)
    add_arguments(p)
    args = p.parse_args(argv)
    show_dividers(args.relationship_dividers)
    run(load_messages(args.dir, args.pattern, args.tz), args)
