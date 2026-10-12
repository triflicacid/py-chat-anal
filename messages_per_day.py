#!/usr/bin/env python3
"""Messages per day for each user, with peaks labelled and quiet spells shaded.

    python messages_per_day.py
    python messages_per_day.py --period W --rolling 4
    python messages_per_day.py --axis linear
    python messages_per_day.py --metric words
    python messages_per_day.py --peaks 0 --quiet 0 --user-quiet 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.counts import daily_counts, daily_words
from chatstats.formatting import fmt_date, fmt_span
from chatstats.loading import resolve_users
from chatstats.peaks import find_quiet_periods, find_peaks
from chatstats.periods import (DEFAULT_PEAK_DISTANCE, DEFAULT_USER_QUIET_MIN, PERIODS,
                               plural, resample_counts, unit)
from chatstats.plotting import plot_lines

OUT = "out/messages_per_day.png"
NEEDS = (cli.add_rolling_args,)
# metric -> (table builder, axis label, the noun the printed report counts in)
METRICS = {"messages": (daily_counts, "Messages", "msgs"),
           "words": (daily_words, "Words", "words")}


def add_arguments(p) -> None:
    """Options for the messages per day chart."""
    g = p.add_argument_group("messages per day")
    g.add_argument("--out", default=OUT, help="output image (.png/.svg/.pdf)")
    g.add_argument("--metric", choices=list(METRICS), default="messages",
                   help="count messages, or the words inside them (default messages)")
    g.add_argument("--period", choices=list(PERIODS), default="D",
                   help="bucket for the messages chart: D(ay), W(eek), M(onth)")
    g.add_argument("--axis", "--yscale", choices=["linear", "log"], default="log",
                   help="y-axis scale. log (default) is symlog, so silent days still "
                        "plot at zero; linear is the plain view")
    g.add_argument("--peaks", type=int, default=5, help="label each user's top N peaks (0 = off)")
    g.add_argument("--peak-distance", type=int,
                   help="min periods between labelled peaks (default: 14 days / 4 weeks / 2 months)")
    g.add_argument("--quiet", type=int, default=12,
                   help="shade (grey) the N longest periods where both users were quiet (0 = off)")
    g.add_argument("--user-quiet", type=int, default=6,
                   help="shade (user colour) each user's N longest solo gaps (0 = off)")
    g.add_argument("--user-quiet-min", type=int,
                   help="only count solo gaps of at least N periods (default: 2 days / 1 week / 1 month)")
    g.add_argument("--quiet-threshold", type=int, default=5,
                   help="a period counts as quiet if messages <= this (default 5; 0 = silent); "
                        "combined total for --quiet, each user's own count for --user-quiet")
    g.add_argument("--quiet-min", type=int, default=1,
                   help="ignore quiet runs shorter than N periods")
    g.add_argument("--total", type=str.lower, choices=["true", "false"], default="true",
                   help="draw the red combined-total line (default true)")
    g.add_argument("--csv", help="also save the daily counts table to this CSV")


def solo_quiet_runs(
    counts: pd.DataFrame, users: list[str], threshold: int, min_length: int
) -> dict[str, list[tuple]]:
    """Each user's quiet runs, minus those falling wholly inside a shared silence.

    Those are already under the grey "both quiet" shading.
    """
    everyone_quiet = counts.sum(axis=1) <= threshold
    runs = {}
    for u in users:
        found = find_quiet_periods(counts[u], None, threshold, min_length)
        runs[u] = [r for r in found if not everyone_quiet.loc[r[0]:r[1]].all()]
    return runs


def report(
    counts: pd.DataFrame, users: list[str], period: str, rolling: int, label: str,
    peaks: int, distance: int, spans: list[tuple], solo: dict[str, list[tuple]],
    user_quiet: int, user_quiet_min: int, noun: str = "msgs",
) -> None:
    """Print the peaks and quiet spells that the chart marks."""
    if peaks:
        smoothed = f", on {rolling}-{unit(period)} avg" if rolling > 1 else ""
        print(f"\n=== Peaks (top {peaks} per user, ≥{distance} {unit(period)}s apart{smoothed}) ===")
        for u in users:
            s = counts[u].rolling(rolling, min_periods=1).mean() if rolling > 1 else counts[u]
            found = find_peaks(s, peaks, distance).items()
            print(f"{u}: " + ", ".join(f"{fmt_date(d, period)} ({v:,.1f})" if rolling > 1
                                       else f"{fmt_date(d, period)} ({v:,})" for d, v in found))

    if spans or label:
        print(f"\n=== Longest periods where both were {label} ===")
        if not spans:
            print("none found (try a higher --quiet-threshold)")
        for i, (start, end, length, msgs) in enumerate(spans, 1):
            print(f"#{i}: {fmt_span(start, end, period)}  "
                  f"({plural(length, period)}, {msgs} {noun})")

    if user_quiet:
        print(f"\n=== Individual {label} periods (≥{plural(user_quiet_min, period)}, "
              f"excluding gaps entirely inside a shared silence) ===")
        for u in users:
            runs = solo[u]
            print(f"{u}: {len(runs)} gap(s), {plural(sum(r[2] for r in runs), period)} in total")
            for i, (start, end, length, msgs) in enumerate(runs[:user_quiet], 1):
                print(f"   #{i}: {fmt_span(start, end, period)}  "
                      f"({plural(length, period)}, {msgs} {noun})")


def plot_messages_per_day(
    df: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    rolling: int = 0,
    period: str = "D",
    peaks: int = 5,
    peak_distance: int | None = None,
    quiet: int = 12,
    quiet_threshold: int = 5,
    quiet_min: int = 1,
    user_quiet: int = 6,
    user_quiet_min: int | None = None,
    axis: str = "log",
    total: bool = True,
    cumulative: bool = True,
    share: bool = True,
    metric: str = "messages",
) -> Path:
    """Line chart of messages per day/week/month for each user, plus a red total.

    peaks           -> label each user's top-n local peaks (0 = off)
    peak_distance   -> minimum periods between labelled peaks (default ~2 weeks)
    quiet           -> shade (grey) the n longest runs where *everyone* was quiet (0 = off)
    user_quiet      -> shade (user's colour) each user's n longest runs where *they* were
                       quiet but the others weren't (0 = off)
    quiet_threshold -> a period is quiet if messages <= this (0 = silent). Applies to the
                       combined total for `quiet` and to each user's own count for `user_quiet`
    quiet_min / user_quiet_min -> ignore runs shorter than this many periods
                       (user_quiet_min defaults to 3 days / 1 week / 1 month)
    axis            -> "log" (default) so the quiet majority of days stays readable next
                       to the occasional 900-message day; "linear" for the plain view
    cumulative      -> add a middle panel with each user's running total
    share           -> add a lower panel with each user's share of that period's messages
    metric          -> count "messages", or the "words" inside them
    total           -> draw the red line for both users combined
    """
    users = resolve_users(df, users)
    build, ylabel, noun = METRICS[metric]
    counts = resample_counts(build(df, users), period)
    if user_quiet_min is None:
        user_quiet_min = DEFAULT_USER_QUIET_MIN[period]
    if peak_distance is None:
        peak_distance = DEFAULT_PEAK_DISTANCE[period]
    label = "silent" if quiet_threshold == 0 else f"quiet (≤{quiet_threshold}/{unit(period)})"

    spans = (find_quiet_periods(counts.sum(axis=1), quiet, quiet_threshold, quiet_min)
             if quiet else [])
    solo = solo_quiet_runs(counts, users, quiet_threshold, user_quiet_min)
    report(counts, users, period, rolling, label, peaks, peak_distance, spans, solo,
           user_quiet, user_quiet_min, noun)

    return plot_lines(
        counts, f"{ylabel} per {unit(period).title()}", ylabel, out,
        rolling, period, peaks=peaks, peak_distance=peak_distance, quiet=spans,
        quiet_label=label,
        user_quiet={u: r[:user_quiet] for u, r in solo.items()} if user_quiet else None,
        axis=axis, total=total, cumulative=cumulative, share=share,
    )


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Draw the chart, and save the daily counts if a CSV was asked for."""
    out = plot_messages_per_day(
        df, a.users, a.out, a.rolling, a.period, peaks=a.peaks,
        peak_distance=a.peak_distance, quiet=a.quiet, quiet_threshold=a.quiet_threshold,
        quiet_min=a.quiet_min, user_quiet=a.user_quiet, user_quiet_min=a.user_quiet_min,
        axis=a.axis, total=a.total == "true", metric=a.metric)
    if a.csv:
        METRICS[a.metric][0](df, a.users).to_csv(a.csv)
        print(f"Daily counts saved to {Path(a.csv).resolve()}")
    return out


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
