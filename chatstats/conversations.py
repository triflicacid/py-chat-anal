"""Conversation structure: turns, who starts, how long an answer takes.

Two views of the same stream:

  conversation_table  splits at `gap_hours` of silence, times replies within one
  handover_times      every speaker change, no cutoff, so an overnight wait counts
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .counts import per_day, period_stats, selected
from .formatting import fmt_secs
from .loading import resolve_users
from .periods import resample_counts


def conversation_table(
    df: pd.DataFrame, users: list[str] | None = None, gap_hours: float = 2.0
) -> pd.DataFrame:
    """The selected users' messages, annotated with conversation structure.

    A new conversation starts after `gap_hours` of silence. Adds columns:
      User         canonical username
      ConvID       conversation number
      IsStart      True for the first message of a conversation
      ReplySecs    seconds since the other person's last message, on the first
                   message of each turn; NaN otherwise and on starters
    """
    users = resolve_users(df, users)
    sub = selected(df, users)
    delta = sub["Timestamp"].diff()
    sub["IsStart"] = delta.isna() | (delta > pd.Timedelta(hours=gap_hours))
    sub["ConvID"] = sub["IsStart"].cumsum()
    is_reply = (sub["User"] != sub["User"].shift()) & ~sub["IsStart"]
    sub["ReplySecs"] = delta.dt.total_seconds().where(is_reply)
    return sub


def conversation_list(conv: pd.DataFrame) -> pd.DataFrame:
    """One row per conversation: start, starter, how many took part, messages, length."""
    out = conv.groupby("ConvID").agg(Date=("Date", "first"), Start=("Timestamp", "min"),
                                     End=("Timestamp", "max"), Msgs=("ID", "size"),
                                     Starter=("User", "first"), Users=("User", "nunique"))
    out["Mins"] = (out["End"] - out["Start"]).dt.total_seconds() / 60
    return out


def fastest_burst(df: pd.DataFrame, users: list[str] | None = None,
                  size: int = 100) -> tuple[float, pd.Timestamp] | None:
    """(seconds, start) of the shortest run of `size` messages, or None if too few."""
    users = resolve_users(df, users)
    sub = selected(df, users)
    if len(sub) < size:
        return None
    took = (sub["Timestamp"].shift(-(size - 1)) - sub["Timestamp"]).dt.total_seconds()
    return float(took.min()), sub.loc[took.idxmin(), "Local"]


def _turns(df: pd.DataFrame, users: list[str], nudge_hours: float = 1.0) -> pd.DataFrame:
    """The selected users' messages, numbered by turn and flagged where one is a nudge."""
    sub = selected(df, users)
    same_speaker = sub["User"] == sub["User"].shift()
    sub["Turn"] = (~same_speaker).cumsum()
    # A nudge: the sender got no answer and spoke again anyway.
    gap = sub["Timestamp"].diff().dt.total_seconds().where(same_speaker)
    sub["IsNudge"] = gap > nudge_hours * 3600
    return sub


def turn_counts(
    df: pd.DataFrame, users: list[str] | None = None, period: str = "W"
) -> pd.DataFrame:
    """Turns per period per user, dated by first message. A turn is one person's run."""
    users = resolve_users(df, users)
    sub = _turns(df, users)
    return resample_counts(per_day(sub[sub["Turn"] != sub["Turn"].shift()], users), period)


def nudge_counts(
    df: pd.DataFrame, users: list[str] | None = None, nudge_hours: float = 1.0,
    period: str = "W",
) -> pd.DataFrame:
    """Nudges sent per period per user, each dated by the nudge itself."""
    users = resolve_users(df, users)
    sub = _turns(df, users, nudge_hours)
    return resample_counts(per_day(sub, users, sub["IsNudge"].astype(int)), period)


def first_of_day_counts(
    df: pd.DataFrame, users: list[str] | None = None, period: str = "W",
    day_start: float = 5.0,
) -> pd.DataFrame:
    """Days on which each user sent the first message, per period.

    The day turns over at `day_start` local, so 1am belongs to the night before.
    """
    users = resolve_users(df, users)
    sub = selected(df, users)
    day = (sub["Local"] - pd.Timedelta(hours=day_start)).dt.tz_localize(None).dt.normalize()
    first = sub.groupby(day)["User"].first()
    daily = first.groupby([first.index, first]).size().unstack(fill_value=0)
    full = pd.date_range(day.min(), day.max(), freq="D")
    return resample_counts(daily.reindex(index=full, columns=users, fill_value=0), period)


def handover_times(
    df: pd.DataFrame, users: list[str] | None = None, nudge_hours: float = 1.0
) -> pd.DataFrame:
    """Every speaker change and how long the answer took, with no cutoff.

    One row per handover:
      Waiter     who spoke last and then waited
      Responder  who eventually came back
      Secs       the waiter's last message -> the responder's first
      Nudges     messages the waiter sent into the silence, after `nudge_hours`
      At         when the wait started
    """
    users = resolve_users(df, users)
    sub = _turns(df, users, nudge_hours)
    turns = sub.groupby("Turn").agg(User=("User", "first"), Start=("Timestamp", "min"),
                                    End=("Timestamp", "max"), Nudges=("IsNudge", "sum"))
    if len(turns) < 2:
        return pd.DataFrame(columns=["Waiter", "Responder", "Secs", "Nudges", "At"])
    return pd.DataFrame({
        "Waiter": turns["User"].to_numpy()[:-1],
        "Responder": turns["User"].to_numpy()[1:],
        "Secs": (turns["Start"].to_numpy()[1:] - turns["End"].to_numpy()[:-1])
                / np.timedelta64(1, "s"),
        # Nudges belong to the turn that was doing the waiting.
        "Nudges": turns["Nudges"].to_numpy()[:-1],
        "At": turns["End"].to_numpy()[:-1],
    })


def reply_time_stats(
    conv: pd.DataFrame, users: list[str], period: str = "W", min_replies: int = 3
) -> dict[str, pd.DataFrame]:
    """Median and quartiles of reply time per period per user, in seconds.

    Periods under `min_replies` are left blank.
    """
    return period_stats(conv.dropna(subset=["ReplySecs"]), users, "ReplySecs",
                        period, min_replies, index_from=conv)


def _conversation_counts(
    rows: pd.DataFrame, conv: pd.DataFrame, users: list[str], period: str
) -> pd.DataFrame:
    """Count `rows`, one per conversation, per period per user over the range of `conv`."""
    daily = rows.groupby(["Date", "User"]).size().unstack(fill_value=0)
    full = pd.date_range(conv["Date"].min(), conv["Date"].max(), freq="D")
    return resample_counts(daily.reindex(index=full, columns=users, fill_value=0), period)


def initiator_counts(conv: pd.DataFrame, users: list[str], period: str = "W") -> pd.DataFrame:
    """Conversations started per period per user."""
    return _conversation_counts(conv[conv["IsStart"]], conv, users, period)


def ender_counts(conv: pd.DataFrame, users: list[str], period: str = "W") -> pd.DataFrame:
    """Conversations ended per period per user: who sent the last message of each."""
    return _conversation_counts(conv.groupby("ConvID").tail(1), conv, users, period)


def starter_summary(conv: pd.DataFrame, users: list[str], gap_hours: float) -> None:
    """Print how many conversations there were and who opened them."""
    print(f"\n=== Conversations (new conversation after {gap_hours:g}h of silence) ===")
    convs = conv.groupby("ConvID").agg(Starter=("User", "first"), Msgs=("ID", "size"),
                                       Start=("Timestamp", "min"), End=("Timestamp", "max"))
    convs["Minutes"] = (convs["End"] - convs["Start"]).dt.total_seconds() / 60
    print(f"Conversations: {len(convs):,}  "
          f"(median {convs['Msgs'].median():.0f} messages, {convs['Minutes'].median():.0f} min long)")
    for u in users:
        mine = convs[convs["Starter"] == u]
        print(f"{u}: started {len(mine):,} ({len(mine) / len(convs) * 100:.1f}%), "
              f"median length of those: {mine['Msgs'].median():.0f} msgs"
              if len(mine) else f"{u}: started 0")


def reply_summary(conv: pd.DataFrame, users: list[str]) -> None:
    """Print reply-time percentiles for replies inside a conversation."""
    print("\n=== Reply times (within a conversation) ===")
    for u in users:
        r = conv.loc[conv["User"] == u, "ReplySecs"].dropna()
        if r.empty:
            print(f"{u}: no replies found")
            continue
        print(f"{u}: median {fmt_secs(r.median())}, "
              f"within 1 min {(r <= 60).mean() * 100:.0f}%, within 5 min {(r <= 300).mean() * 100:.0f}%, "
              f"slowest 10% take over {fmt_secs(r.quantile(0.9))}  ({len(r):,} replies)")


def response_summary(hand: pd.DataFrame, users: list[str], nudge_hours: float = 1.0) -> None:
    """Print the uncensored response-time distribution, plus who waits on whom."""
    print("\n=== Time to get a response (no conversation cutoff) ===")
    marks = [10, 60, 300, 3600]
    head = "".join(f"{'<=' + fmt_secs(m):>11}" for m in marks)
    print(f"{'responder':<14}{'n':>7}{head}{'median':>10}{'p90':>9}{'p99':>9}{'longest':>10}")
    for u in users:
        x = hand.loc[hand["Responder"] == u, "Secs"]
        if x.empty:
            print(f"{u:<14}{'no handovers':>7}")
            continue
        pct = "".join(f"{(x <= m).mean() * 100:10.0f}%" for m in marks)
        print(f"{u:<14}{len(x):>7,}{pct}"
              f"{fmt_secs(x.median()):>10}{fmt_secs(x.quantile(0.9)):>9}"
              f"{fmt_secs(x.quantile(0.99)):>9}{fmt_secs(x.max()):>10}")

    print("\n=== Waiting (the same handovers, seen from the other side) ===")
    for u in users:
        x = hand.loc[hand["Waiter"] == u]
        if x.empty:
            continue
        long = x.loc[x["Secs"] > 3600, "Secs"]
        median_long = fmt_secs(long.median()) if len(long) else "n/a"
        print(f"{u:<14} waited {len(x):,} times; {len(long):,} over 1h "
              f"({len(long) / len(x) * 100:.1f}%), median of those {median_long}; "
              f"nudged {int(x['Nudges'].sum()):,} times "
              f"(spoke again after {nudge_hours:g}h of no answer)")
