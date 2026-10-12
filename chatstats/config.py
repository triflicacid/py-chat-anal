"""The optional config file."""
from __future__ import annotations

import tomllib
from datetime import date, datetime
from pathlib import Path

CONFIG_FILE = "config.toml"
USERNAMES_TABLE = "usernames"
KEY_DATES_KEY = "key_dates"

_path: Path = Path(CONFIG_FILE)
_cache: dict | None = None


def use_config(path: str | Path = CONFIG_FILE) -> None:
    """Point every later lookup at this config file."""
    global _path, _cache
    _path, _cache = Path(path), None


def load_config(path: str | Path | None = None) -> dict:
    """Read the config file, or an empty config when there is none. Cached."""
    global _cache
    if path is None and _cache is not None:
        return _cache
    file = _path if path is None else Path(path)
    config = {}
    if file.exists():
        with file.open("rb") as f:
            config = tomllib.load(f)
    if path is None:
        _cache = config
    return config


def configured_colors(path: str | Path | None = None) -> dict[str, str]:
    """username (lower case) -> colour, in the order the file lists them."""
    name = (_path if path is None else Path(path)).name
    table = load_config(path).get(USERNAMES_TABLE, {})
    if not isinstance(table, dict):
        raise ValueError(f"{name}: [{USERNAMES_TABLE}] must be a table of "
                         f'user = "colour" entries')
    colors = {}
    for user, color in table.items():
        if not isinstance(color, str):
            raise ValueError(f"{name}: the colour for {user!r} must be a string, "
                             f'or "" to let matplotlib pick one')
        colors[user.strip().lower()] = color.strip()
    return colors


def _one_date(entry, name: str) -> tuple[date, str]:
    """One `key_dates` entry as (day, label). The label is "" when none was given."""
    if isinstance(entry, dict):
        unknown = set(entry) - {"date", "label"}
        if unknown:
            raise ValueError(f"{name}: a {KEY_DATES_KEY} entry takes date and label, "
                             f"not {', '.join(sorted(unknown))}")
        if "date" not in entry:
            raise ValueError(f"{name}: the {KEY_DATES_KEY} entry {entry!r} has no date")
        label = entry.get("label", "")
        if not isinstance(label, str):
            raise ValueError(f"{name}: the label for {entry['date']} must be a string")
        return _one_date(entry["date"], name)[0], label.strip()
    if isinstance(entry, datetime):  # charts bucket by day; drop the time
        return entry.date(), ""
    if isinstance(entry, date):
        return entry, ""
    if isinstance(entry, str):
        try:
            return date.fromisoformat(entry.strip()), ""
        except ValueError:
            raise ValueError(f"{name}: {entry!r} is not a date; write it as 2026-09-19, "
                             f"with no quotes") from None
    raise ValueError(f"{name}: {entry!r} is not a date or a "
                     f"{{ date = ..., label = ... }} entry")


def key_dates(path: str | Path | None = None) -> list[tuple[date, str]]:
    """The dates to mark and the label for each, oldest first.

    An entry is a date, or a table of `date` and `label`.
    """
    name = (_path if path is None else Path(path)).name
    listed = load_config(path).get(KEY_DATES_KEY, [])
    if isinstance(listed, (str, dict)) or not isinstance(listed, list):
        raise ValueError(f"{name}: {KEY_DATES_KEY} must be a list of dates")
    return sorted((_one_date(entry, name) for entry in listed), key=lambda d: d[0])
