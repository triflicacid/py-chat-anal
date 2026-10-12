"""Topics: named lists of words read from a file, and how often each comes up."""
from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

from .counts import URL, selected, word_pattern
from .loading import resolve_users
from .periods import resample_counts

TOPICS_FILE = "topics.toml"


def load_topics(path: str | Path = TOPICS_FILE) -> dict[str, list[str]]:
    """Read the topic file: one `name = ["word", ...]` line per topic, in file order."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No topic file at {path.resolve()}")
    with path.open("rb") as f:
        topics = tomllib.load(f)
    for name, words in topics.items():
        if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
            raise ValueError(f"{path.name}: topic {name!r} must be a list of words")
    return {name: words for name, words in topics.items() if words}


def topic_hits(df: pd.DataFrame, topics: dict[str, list[str]]) -> pd.DataFrame:
    """One True/False column per topic: does the message mention any of its words.

    Links are removed first, since the text of a URL is not something anyone said.
    """
    text = df["Content"].str.replace(URL, " ", regex=True)
    return pd.DataFrame({
        name: text.str.contains("|".join(word_pattern(w).pattern for w in words),
                                case=False, regex=True)
        for name, words in topics.items()}, index=df.index)


def topic_counts(
    df: pd.DataFrame,
    topics: dict[str, list[str]],
    users: list[str] | None = None,
    period: str = "W",
) -> pd.DataFrame:
    """Messages mentioning each topic per period, both users together.

    Two extra columns give the scale: `any` is messages mentioning at least one
    topic, and `messages` is every message sent. A message counts once for each
    topic it mentions, so the topic columns can add up to more than `any`.
    """
    users = resolve_users(df, users)
    sub = selected(df, users)
    hits = topic_hits(sub, topics)
    hits["any"] = hits.any(axis=1)
    hits["messages"] = True
    daily = hits.groupby(sub["Date"]).sum()
    full = pd.date_range(sub["Date"].min(), sub["Date"].max(), freq="D")
    return resample_counts(daily.reindex(full, fill_value=0), period)


def topic_counts_by_user(
    df: pd.DataFrame,
    topics: dict[str, list[str]],
    users: list[str] | None = None,
    period: str = "W",
) -> dict[str, pd.DataFrame]:
    """The topic_counts table for each user alone, all on one shared set of periods.

    Users with no messages are left out. The shared periods are what let the tables
    be drawn side by side on one date axis.
    """
    users = resolve_users(df, users)
    present = set(selected(df, users)["User"])
    tables = {u: topic_counts(df, topics, [u], period) for u in users if u in present}
    periods = pd.DatetimeIndex([])
    for table in tables.values():
        periods = periods.union(table.index)
    return {u: table.reindex(periods, fill_value=0) for u, table in tables.items()}
