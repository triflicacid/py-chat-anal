"""The printed overview: totals per user, daily activity, weekday and hour."""
from __future__ import annotations

import pandas as pd

from .counts import daily_counts
from .loading import resolve_users

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def summarise(df: pd.DataFrame, users: list[str] | None = None) -> pd.DataFrame:
    """Print an overview and return a per-user summary table."""
    users = resolve_users(df, users)
    start, end = df["Timestamp"].min(), df["Timestamp"].max()
    n_days = (df["Date"].max() - df["Date"].min()).days + 1

    print("\n=== Overview ===")
    print(f"Messages:   {len(df):,}")
    print(f"Date range: {start:%Y-%m-%d} to {end:%Y-%m-%d} ({n_days:,} days)")
    print(f"Authors:    {df['Username'].nunique()}")

    per_user = (
        df.groupby("Username")
        .agg(
            Messages=("ID", "size"),
            Words=("WordCount", "sum"),
            MsgsWithAttachment=("HasAttachment", "sum"),
            Attachments=("NAttachments", "sum"),
            Reactions=("NReactions", "sum"),
            FirstMessage=("Timestamp", "min"),
            LastMessage=("Timestamp", "max"),
            ActiveDays=("Date", "nunique"),
        )
        .sort_values("Messages", ascending=False)
    )
    per_user["Share%"] = (per_user["Messages"] / len(df) * 100).round(1)
    per_user["AvgWords/Msg"] = (per_user["Words"] / per_user["Messages"]).round(1)
    per_user["Msgs/ActiveDay"] = (per_user["Messages"] / per_user["ActiveDays"]).round(1)

    print("\n=== Per user ===")
    print(per_user.drop(columns=["FirstMessage", "LastMessage"]).to_string())

    daily = daily_counts(df, users)
    print("\n=== Daily activity (selected users) ===")
    for u in users:
        s = daily[u]
        if s.sum() == 0:
            print(f"{u}: no messages found")
            continue
        print(f"{u}: mean {s.mean():.1f}/day, median {s.median():.0f}, "
              f"busiest {s.idxmax():%Y-%m-%d} ({s.max()} msgs), "
              f"silent on {(s == 0).sum():,} of {len(s):,} days")

    weekday = df.groupby(df["Local"].dt.day_name()).size().rename_axis(None)
    print("\n=== Messages by weekday ===")
    print(weekday.reindex(WEEKDAYS, fill_value=0).to_string())

    hourly = df.groupby(df["Local"].dt.hour).size()
    print(f"\nBusiest hour ({df['Local'].dt.tz}): "
          f"{hourly.idxmax():02d}:00 ({hourly.max():,} msgs)")
    return per_user
