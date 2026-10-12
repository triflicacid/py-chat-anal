"""Reading the export CSVs into one tidy frame of messages."""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from .config import configured_colors

EXPECTED_COLUMNS = [
    "ID", "Timestamp", "Username", "Display Name", "Server Nickname",
    "Content", "Forwarded Content", "Attachments", "Embeds", "Reactions",
]
FILE_GLOB = "page-*.csv"

# A Discord snowflake's top 42 bits are milliseconds since 2015-01-01T00:00:00Z.
DISCORD_EPOCH_MS = 1_420_070_400_000
DEFAULT_TZ = "Europe/London"  # timezone the export's wall-clock times were written in

# These columns hold counts, not text.
COUNT_COLUMNS = ("Attachments", "Embeds", "Reactions")


def _page_number(path: Path) -> int:
    """NN from page-NN.csv, for numeric sorting."""
    m = re.search(r"page-(\d+)", path.stem)
    return int(m.group(1)) if m else 0


def _detect_delimiter(path: Path) -> str:
    """The delimiter: exports may be comma- or tab-separated."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        header = f.readline()
    try:
        return csv.Sniffer().sniff(header, delimiters=",\t;").delimiter
    except csv.Error:
        return "\t" if header.count("\t") > header.count(",") else ","


def load_file(path: Path) -> pd.DataFrame:
    """One export page, with its columns checked."""
    df = pd.read_csv(
        path,
        sep=_detect_delimiter(path),
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
        engine="python",  # copes with multi-line quoted message content
    )
    df.columns = [c.strip() for c in df.columns]
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    df["SourceFile"] = path.name
    return df


def snowflake_times(ids: pd.Series) -> pd.Series:
    """Exact UTC send time decoded from message IDs; NaT where an ID is not a snowflake.

    Parsed straight to int64: snowflakes exceed float64's exact range.
    """
    ok = ids.str.fullmatch(r"\d{1,19}").fillna(False)
    out = pd.Series(pd.NaT, index=ids.index, dtype="datetime64[ns, UTC]")
    if ok.any():
        ms = (ids[ok].astype("int64").to_numpy() >> 22) + DISCORD_EPOCH_MS
        out.loc[ok] = pd.to_datetime(ms, unit="ms", utc=True)
    return out


def load_messages(
    directory: str | Path = ".", pattern: str = FILE_GLOB, tz: str = DEFAULT_TZ
) -> pd.DataFrame:
    """Load every export page, combine, de-duplicate and resolve timestamps.

    `tz` reads the wall-clock column and sets the local day and hour buckets.
    """
    files = sorted(Path(directory).glob(pattern), key=_page_number)
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} in {Path(directory).resolve()}")

    df = pd.concat([load_file(p) for p in files], ignore_index=True)

    # Pages overlap at the boundaries; message IDs are unique.
    df = df.drop_duplicates(subset="ID", keep="first")

    # Prefer the ID's exact time; fall back to the wall-clock column read in `tz`.
    # An hour repeated or skipped at a DST change is not one instant, so -> NaT, dropped.
    wall = pd.to_datetime(df["Timestamp"], errors="coerce", format="mixed")
    fallback = wall.dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    exact = snowflake_times(df["ID"])
    df["Timestamp"] = exact.fillna(fallback)

    fell_back = df["Timestamp"].notna() & exact.isna()
    if fell_back.any():
        print(f"Note: {fell_back.sum():,} row(s) had no usable message ID; used the {tz} "
              f"wall-clock time, which is only accurate to the minute")
    bad = df["Timestamp"].isna().sum()
    if bad:
        print(f"Warning: dropped {bad} row(s) with unresolvable timestamps")
    df = df.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)

    df["Username"] = df["Username"].str.strip()
    # Buckets follow the local clock, so a late-night message lands on the right night.
    df["Local"] = df["Timestamp"].dt.tz_convert(tz)
    df["Date"] = df["Local"].dt.tz_localize(None).dt.normalize()
    for col in COUNT_COLUMNS:
        df[f"N{col}"] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["HasAttachment"] = df["NAttachments"] > 0
    df["WordCount"] = df["Content"].str.split().str.len().fillna(0).astype(int)

    print(f"Loaded {len(df):,} messages from {len(files)} file(s)")
    return df


def discover_users(df: pd.DataFrame) -> list[str]:
    """Every username in the export."""
    counts = df["Username"].str.strip().value_counts()
    seen: dict[str, str] = {}  # lower case -> spelling, busiest user first
    for name in counts.index:
        if name:
            seen.setdefault(name.lower(), name)
    named = configured_colors()
    return ([seen[u] for u in named if u in seen]
            + [name for u, name in seen.items() if u not in named])


def resolve_users(df: pd.DataFrame, users: list[str] | None = None) -> list[str]:
    """The usernames to work with: the ones asked for, or everyone in the export."""
    return list(users) if users else discover_users(df)
