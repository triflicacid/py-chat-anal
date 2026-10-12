#!/usr/bin/env python3
"""Each user's most-used words, one pie per user.

    python top_words.py
    python top_words.py --top 15
    python top_words.py --stopwords like know --keep yeah
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from chatstats import cli
from chatstats.counts import stop_list, word_frequencies
from chatstats.plotting import plt, readable_on, save, shades, user_colors

OUT = "out/top_words.png"
NEEDS = ()
# The most pies placed side by side, and the size of one in inches.
MAX_COLUMNS = 3
PIE_INCH = 5.4
# Below this share, a wedge has no room for its percentage.
LABEL_MIN_SHARE = 4.0


def add_arguments(p) -> None:
    """Options for the top words chart."""
    g = p.add_argument_group("top words")
    g.add_argument("--out", default=OUT, help="top words chart file")
    g.add_argument("--top", type=int, default=10, help="words per pie (default 10)")
    g.add_argument("--stopwords", nargs="+", default=[], metavar="WORD",
                   help="more words to leave out")
    g.add_argument("--keep", nargs="+", default=[], metavar="WORD",
                   help="words to count despite the stop list")
    g.add_argument("--min-length", type=int, default=3,
                   help="ignore words shorter than this (default 3)")
    g.add_argument("--columns", type=int,
                   help=f"pies per row (default: as many as fit, up to {MAX_COLUMNS})")
    g.add_argument("--csv", help="also save the full word counts to this CSV")


def said(table: pd.DataFrame, user: str) -> pd.Series:
    """The words one user used at all, however rare. Empty for a user who said none."""
    counts = table[user] if user in table else pd.Series(dtype=int)
    return counts[counts > 0]


def top_words_summary(table: pd.DataFrame, users: list[str], top: int = 10) -> None:
    """Print each user's top words with their counts and share of the pie."""
    print(f"\n=== Top {top} words per user ===")
    for u in users:
        vocab = said(table, u)
        counts = vocab.nlargest(top)
        if counts.empty:
            print(f"{u}: no words")
            continue
        print(f"{u}: " + ", ".join(f"{w} ({n:,})" for w, n in counts.items()))
        print(f"{' ' * len(u)}  {counts.sum():,} of {vocab.sum():,} counted words "
              f"({counts.sum() / vocab.sum() * 100:.1f}%), {len(vocab):,} distinct")


def draw_pie(ax, user: str, counts: pd.Series, color: str, total: int) -> None:
    """One user's words as a pie, biggest first from 12 o'clock, in shades of their colour."""
    if counts.empty:
        ax.text(0.5, 0.5, f"{user}\nno words", ha="center", va="center", fontsize=11,
                color="dimgrey", transform=ax.transAxes)
        ax.set_axis_off()
        return
    wedges, _labels, pcts = ax.pie(
        counts, labels=[f"{w}\n{n:,}" for w, n in counts.items()],
        colors=shades(color, len(counts)), startangle=90, counterclock=False,
        autopct=lambda p: f"{p:.0f}%" if p >= LABEL_MIN_SHARE else "",
        pctdistance=0.68, labeldistance=1.08,
        textprops=dict(fontsize=9), wedgeprops=dict(edgecolor="white", linewidth=1.2))
    for wedge, pct in zip(wedges, pcts):
        pct.set_color(readable_on(wedge.get_facecolor()))
        pct.set_fontsize(8.5)
    share = counts.sum() / total * 100 if total else 0.0
    ax.set_title(f"{user}\n{counts.sum():,} of {total:,} counted words ({share:.1f}%)",
                 fontsize=11, color=color, pad=8)


def plot_top_words(
    table: pd.DataFrame,
    users: list[str] | None = None,
    out: str | Path = OUT,
    top: int = 10,
    columns: int | None = None,
) -> Path:
    """A grid of pies, one per user."""
    users = list(users or table.columns)
    ncols = max(1, min(columns or MAX_COLUMNS, len(users)))
    nrows = math.ceil(len(users) / ncols)
    colors = user_colors(users)
    fig, axs = plt.subplots(nrows, ncols, squeeze=False,
                            figsize=(PIE_INCH * ncols, PIE_INCH * nrows + 0.9))
    cells = list(axs.flat)

    for ax, u in zip(cells, users):
        vocab = said(table, u)
        draw_pie(ax, u, vocab.nlargest(top), colors[u], int(vocab.sum()))
    for ax in cells[len(users):]:
        ax.set_visible(False)

    fig.suptitle(f"Top {top} Words per User", fontsize=14, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    return save(fig, out)


def run(df: pd.DataFrame, a: argparse.Namespace) -> Path:
    """Count the words, print the lists and draw the pies."""
    table = word_frequencies(df, a.users, stop_list(a.stopwords, a.keep), a.min_length)
    top_words_summary(table, a.users, a.top)
    if a.csv:
        table.sort_values(a.users[0], ascending=False).to_csv(a.csv)
        print(f"Word counts saved to {Path(a.csv).resolve()}")
    return plot_top_words(table, a.users, a.out, a.top, a.columns)


if __name__ == "__main__":
    cli.run_chart(NEEDS, add_arguments, run, __doc__)
