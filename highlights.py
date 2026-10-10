#!/usr/bin/env python3
"""The whole history as one card of headline numbers: totals, records and habits.

    python highlights.py --dir data
    python highlights.py --dir data --gap 4
    python highlights.py --dir data --output-longest       # ten longest messages each
    python highlights.py --dir data --output-longest 25
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.conversations import (conversation_list, conversation_table, fastest_burst,
                                     first_of_day_counts, nudge_counts)
from chatstats.counts import (daily_counts, daily_links, is_question, selected,
                              signature_words)
from chatstats.formatting import fmt_date, fmt_secs, fmt_span
from chatstats.loading import DEFAULT_USERS
from chatstats.peaks import find_streaks
from chatstats.plotting import PAIR_COLOR, plt, save, user_colors

OUT = "out/highlights.png"
NEEDS = (cli.add_gap_args,)
PAIR_COLUMNS = 3
USER_COLUMNS = 2   # tiles side by side inside each user's part of the card
USER_ROW = 0.62    # height of a user tile, against 1.0 for a shared one
BURST = 100        # messages in the "fastest burst" tile
NUDGE_HOURS = 1.0
LONGEST = 10       # messages written by --output-longest when no number is given

Tile = tuple[str, str]  # the big number, and the line explaining it


def add_arguments(p) -> None:
    """Options for the highlights card."""
    g = p.add_argument_group("highlights")
    g.add_argument("--out", default=OUT, help="highlights card file")
    g.add_argument("--output-longest", type=int, nargs="?", const=LONGEST, metavar="N",
                   help=f"also write each user's N longest messages (default {LONGEST}) "
                        "to <username>.txt")


def pair_tiles(df: pd.DataFrame, users: list[str], conv: pd.DataFrame) -> list[Tile]:
    """The headline numbers that belong to both of us together."""
    sub = selected(df, users)
    daily = daily_counts(df, users).sum(axis=1)
    convs = conversation_list(conv)
    tiles = [
        (f"{len(sub):,}", f"messages, {fmt_span(daily.index[0], daily.index[-1], 'D')}"),
        (f"{sub['WordCount'].sum():,}", "words written"),
        (f"{(daily > 0).sum():,} of {len(daily):,}", "days with at least one message"),
    ]
    for start, end, length, _msgs in find_streaks(daily, 1):
        tiles.append((f"{length:,} days", f"longest streak, {fmt_span(start, end, 'D')}"))
    silence = sub["Timestamp"].diff()
    if silence.notna().any():
        tiles.append((f"{silence.max().total_seconds() / 86400:.1f} days",
                      f"longest silence, ending {fmt_date(sub.loc[silence.idxmax(), 'Date'], 'D')}"))
    tiles.append((f"{daily.max():,}", f"messages on the busiest day, {fmt_date(daily.idxmax(), 'D')}"))
    tiles.append((f"{len(convs):,}", f"conversations, typically {convs['Msgs'].median():.0f} "
                                     f"messages and {fmt_secs(convs['Mins'].median() * 60)}"))
    biggest = convs.loc[convs["Msgs"].idxmax()]
    tiles.append((f"{biggest['Msgs']:,}",
                  f"messages in one conversation, {fmt_secs(biggest['Mins'] * 60)} long, "
                  f"{fmt_date(biggest['Date'], 'D')}"))
    burst = fastest_burst(df, users, BURST)
    if burst:
        tiles.append((fmt_secs(burst[0]), f"fastest {BURST} messages, {burst[1]:%d %b %Y at %H:%M}"))
    hours = sub["Local"].dt.hour.value_counts()
    tiles.append((f"{hours.idxmax():02d}:00", f"busiest hour, {hours.max() / len(sub) * 100:.0f}% "
                                              f"of all messages"))
    weekdays = sub["Local"].dt.day_name().value_counts()
    tiles.append((weekdays.idxmax(), f"busiest weekday, {weekdays.max() / len(sub) * 100:.0f}% "
                                     f"of all messages"))
    tiles.append((f"{daily_links(df, users).to_numpy().sum():,}",
                  f"links and {sub['NAttachments'].sum():,} attachments shared"))
    return tiles


def user_tiles(df: pd.DataFrame, users: list[str], conv: pd.DataFrame) -> dict[str, list[Tile]]:
    """The same set of numbers for each of us, to read side by side."""
    sub = selected(df, users)
    starts = conv[conv["IsStart"]].groupby("User").size().reindex(users, fill_value=0)
    first = first_of_day_counts(df, users, "D").sum()
    nudges = nudge_counts(df, users, NUDGE_HOURS, "D").sum()
    links = daily_links(df, users).sum()
    asked = is_question(sub)
    words = signature_words(df, users)
    tiles = {}
    for u in users:
        mine = sub[sub["User"] == u]
        if mine.empty:
            continue
        longest = mine.loc[mine["WordCount"].idxmax()]
        tiles[u] = [
            (f"{len(mine):,}", "messages"),
            (f"{mine['WordCount'].sum():,}", f"words, {mine['WordCount'].mean():.1f} per message"),
            (f"{starts[u]:,}", f"conversations started, {starts[u] / max(starts.sum(), 1) * 100:.0f}% "
                               f"of them"),
            (f"{first[u]:,}", "days sending the first message"),
            (fmt_secs(conv.loc[conv["User"] == u, "ReplySecs"].median()),
             "typical time to reply in a conversation"),
            (f"{nudges[u]:,}", f"times spoke again after {NUDGE_HOURS:g}h unanswered"),
            (f"{asked[sub['User'] == u].sum():,}", "questions asked"),
            (f"{links[u]:,}", f"links and {mine['NAttachments'].sum():,} attachments sent"),
            (f"{longest['WordCount']:,} words", f"longest message, {fmt_date(longest['Date'], 'D')}"),
            (", ".join(words[u]) or "none", "signature words"),
        ]
    return tiles


def highlights_summary(pair: list[Tile], per_user: dict[str, list[Tile]]) -> None:
    """Print every tile, so the numbers can be read without opening the card."""
    print("\n=== Highlights ===")
    for big, caption in pair:
        print(f"{big:>22}  {caption}")
    for u, tiles in per_user.items():
        print(f"\n{u}")
        for big, caption in tiles:
            print(f"{big:>22}  {caption}")


def write_longest(df: pd.DataFrame, users: list[str], n: int, folder: str | Path = ".") -> list[Path]:
    """Write each user's `n` longest messages, longest first, to <username>.txt."""
    sub = selected(df, users)
    written = []
    for u in users:
        mine = sub[sub["User"] == u].sort_values("WordCount", ascending=False, kind="stable")
        blocks = [f"#{i}  {m['Local']:%d %b %Y at %H:%M}  ({m['WordCount']:,} words)\n{m['Content']}"
                  for i, (_idx, m) in enumerate(mine.head(n).iterrows(), 1)]
        path = Path(folder) / f"{u}.txt"
        path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        print(f"Longest messages saved to {path.resolve()}")
        written.append(path)
    return written


def _draw_tiles(ax, tiles: list[Tile], left: float, width: float, top: float, columns: int,
                row: float, size: float, color: str) -> None:
    """Lay tiles out in a grid: the big number, with its caption underneath."""
    for i, (big, caption) in enumerate(tiles):
        x = left + (i % columns + 0.5) * width / columns
        y = top + (i // columns + 0.5) * row
        ax.text(x, y - 0.13 * row, big, ha="center", va="center", fontsize=size,
                fontweight="bold", color=color)
        ax.text(x, y + 0.27 * row, caption, ha="center", va="center",
                fontsize=9.5 if row >= 1 else 9, color="dimgrey")


def plot_highlights(
    pair: list[Tile],
    per_user: dict[str, list[Tile]],
    out: str | Path = OUT,
) -> Path:
    """Draw the card: a grid of shared tiles, then a grid of tiles for each user.

    Everything is text placed on one invisible axes, measured in tiles across and
    rows down, so the layout follows however many tiles there are.
    """
    colors = user_colors(per_user)
    pair_rows = -(-len(pair) // PAIR_COLUMNS)
    user_rows = max((-(-len(t) // USER_COLUMNS) for t in per_user.values()), default=0)
    users_top = pair_rows + 0.75
    rows = users_top + user_rows * USER_ROW
    fig, ax = plt.subplots(figsize=(14, 1.45 * rows + 0.9))
    ax.set_xlim(0, PAIR_COLUMNS)
    ax.set_ylim(rows, -0.45)
    ax.axis("off")
    ax.text(PAIR_COLUMNS / 2, -0.25, "Highlights", ha="center", va="center",
            fontsize=20, fontweight="bold", color=PAIR_COLOR)

    _draw_tiles(ax, pair, 0, PAIR_COLUMNS, 0, PAIR_COLUMNS, 1.0, 30, PAIR_COLOR)
    ax.plot([0.1, PAIR_COLUMNS - 0.1], [pair_rows + 0.1] * 2, color="lightgrey", linewidth=0.8)
    width = PAIR_COLUMNS / max(len(per_user), 1)
    for k, (u, tiles) in enumerate(per_user.items()):
        ax.text((k + 0.5) * width, pair_rows + 0.42, u, ha="center", va="center", fontsize=14,
                fontweight="bold", color=colors[u])
        _draw_tiles(ax, tiles, k * width, width, users_top, USER_COLUMNS, USER_ROW, 18,
                    colors[u])
    fig.tight_layout()
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Work out the tiles, print them and draw the card."""
    conv = conversation_table(df, a.users, a.gap)
    pair = pair_tiles(df, a.users, conv)
    per_user = user_tiles(df, a.users, conv)
    highlights_summary(pair, per_user)
    if a.output_longest:
        write_longest(df, a.users, a.output_longest)
    return plot_highlights(pair, per_user, a.out)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
