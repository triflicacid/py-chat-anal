"""Day / week / month bucketing, and the shared date axis."""
from __future__ import annotations

import matplotlib.dates as mdates
import pandas as pd

# code -> (noun used in titles, pandas resample rule)
PERIODS = {"D": ("day", "D"), "W": ("week", "W-MON"), "M": ("month", "MS")}

# Default spacing between labelled peaks, in periods (~2 weeks / 1 month / 2 months).
DEFAULT_PEAK_DISTANCE = {"D": 14, "W": 4, "M": 2}
# Shortest solo gap worth showing, in periods (2 days / 1 week / 1 month).
DEFAULT_USER_QUIET_MIN = {"D": 2, "W": 1, "M": 1}


def unit(period: str) -> str:
    """The noun for one bucket: "day", "week" or "month"."""
    return PERIODS[period][0]


def plural(n: int, period: str) -> str:
    """"1 day", "3 weeks"."""
    return f"{n} {unit(period)}{'s' * (n != 1)}"


def resample_counts(counts: pd.DataFrame, period: str = "D") -> pd.DataFrame:
    """Re-bucket daily counts into days (D), weeks (W, starting Monday) or months (M)."""
    if period == "D":
        return counts
    return counts.resample(PERIODS[period][1], label="left", closed="left").sum()


def period_grouper(period: str) -> pd.Grouper:
    """The same buckets as resample_counts, for grouping a message-level frame."""
    return pd.Grouper(key="Date", freq=PERIODS[period][1], label="left", closed="left")


def period_start(dates: pd.Series, period: str) -> pd.Series:
    """The start of the bucket each date falls in, matching resample_counts."""
    span = {"D": "D", "W": "W-SUN", "M": "M"}[period]  # a W-SUN week starts on Monday
    return dates.dt.to_period(span).dt.start_time


def period_end(start: pd.Timestamp, period: str) -> pd.Timestamp:
    """Exclusive end of the bucket starting at `start` (for shading whole periods)."""
    return start + {"D": pd.Timedelta(days=1), "W": pd.Timedelta(weeks=1),
                    "M": pd.DateOffset(months=1)}[period]


def format_date_axis(ax, index: pd.DatetimeIndex, period: str) -> None:
    """Month labels on major ticks, a faint line + short day label for every week.

    Adapts to long ranges so labels never pile up:
      <= ~13 months : every month labelled, every Monday labelled ("06", "13", ...)
      <= 3 years    : every month labelled, weekly lines without labels
      longer        : every 3rd month labelled, no weekly lines
    """
    span_days = (index.max() - index.min()).days if len(index) else 0
    month_step = 1 if span_days <= 3 * 365 else 3

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=month_step))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.grid(True, which="major", axis="both", alpha=0.4)

    if period != "M" and span_days <= 3 * 365:
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
        ax.grid(True, which="minor", axis="x", alpha=0.2, linestyle=":")
        if span_days <= 400:
            ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d"))
            ax.tick_params(axis="x", which="minor", labelsize=7, labelcolor="grey")
            ax.tick_params(axis="x", which="major", pad=14, labelsize=9)
