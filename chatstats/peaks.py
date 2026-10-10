"""Finding the points worth labelling and the stretches worth shading."""
from __future__ import annotations

import pandas as pd

Run = tuple[pd.Timestamp, pd.Timestamp, int, int]


def find_peaks(series: pd.Series, n: int = 5, distance: int = 14) -> pd.Series:
    """Top-n local peaks, at least `distance` periods apart.

    Greedy: take the highest point, rule out everything within `distance`
    of it, repeat. Each pick is therefore the maximum of its neighbourhood.
    Returns the chosen points (index = date), in date order.
    """
    s = series[series > 0]
    chosen: list[pd.Timestamp] = []
    positions = {d: i for i, d in enumerate(series.index)}
    for date in s.sort_values(ascending=False, kind="stable").index:
        if len(chosen) >= n:
            break
        if all(abs(positions[date] - positions[c]) > distance for c in chosen):
            chosen.append(date)
    return series.loc[sorted(chosen)]


def _runs(total: pd.Series, wanted: pd.Series, min_length: int) -> list[Run]:
    """Every unbroken run of periods flagged in `wanted`, in date order."""
    runs: list[Run] = []
    start = None
    for i, flag in enumerate(list(wanted.to_numpy()) + [False]):  # sentinel closes a trailing run
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start >= min_length:
                runs.append((total.index[start], total.index[i - 1], i - start,
                             int(total.iloc[start:i].sum())))
            start = None
    return runs


def find_quiet_periods(
    total: pd.Series, n: int | None = 3, threshold: int = 0, min_length: int = 1
) -> list[Run]:
    """The n longest runs (all of them if n is None) where `total` stays <= `threshold`.

    Returns (first_period, last_period, length_in_periods, messages_in_run),
    longest first; ties are broken by fewest messages.
    """
    runs = _runs(total, total <= threshold, min_length)
    runs.sort(key=lambda r: (-r[2], r[3], r[0]))
    return runs[:n]


def find_streaks(total: pd.Series, n: int | None = 3, min_length: int = 1) -> list[Run]:
    """The n longest unbroken runs (all of them if n is None) where `total` is above zero.

    Returns the same tuples as find_quiet_periods, longest first; ties are broken by
    most messages.
    """
    runs = _runs(total, total > 0, min_length)
    runs.sort(key=lambda r: (-r[2], -r[3], r[0]))
    return runs[:n]
