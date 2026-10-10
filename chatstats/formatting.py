"""Human-readable durations and dates, shared by the printed summaries and the axes."""
from __future__ import annotations

import pandas as pd

from .periods import period_end


def fmt_secs(s: float, _pos=None) -> str:
    """Seconds as "45s", "1m 25s", "12m", "3.7h". Doubles as a matplotlib formatter."""
    if s < 60:
        return f"{s:.0f}s"
    if s < 600:  # under 10 min, keep the seconds: "1m 25s"
        m, sec = divmod(round(s), 60)
        return f"{m}m" if sec == 0 else f"{m}m {sec:02d}s"
    if s < 3600:
        return f"{s / 60:.0f}m"
    return f"{s / 3600:.0f}h" if s % 3600 == 0 else f"{s / 3600:.1f}h"


def fmt_date(d: pd.Timestamp, period: str, short: bool = False) -> str:
    """'05 Jan 2025' / 'Jan 2025', or with short=True '05/01' / 'Jan' (no year)."""
    if short:
        return d.strftime("%b" if period == "M" else "%d/%m")
    return d.strftime("%b %Y" if period == "M" else "%d %b %Y")


def fmt_span(start: pd.Timestamp, end: pd.Timestamp, period: str) -> str:
    """Inclusive date range covering the buckets from `start` to `end`."""
    last = period_end(end, period) - pd.Timedelta(days=1)
    return f"{fmt_date(start, period)} to {fmt_date(last, period)}"
