"""Chart scaffolding every script shares, plus the line renderer two of them use."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to file without needing a display
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from .formatting import fmt_date
from .peaks import find_peaks
from .periods import DEFAULT_PEAK_DISTANCE, format_date_axis, period_end, unit

DPI = 150
# Space left above the tallest line for peak labels, as a multiple of the data
# ceiling. A log axis needs a far larger factor, because the same multiple covers
# much less height there than it does on a linear one.
PEAK_HEADROOM_LOG = 5.0
PEAK_HEADROOM_LINEAR = 1.32        # plus PER_LINE for each line drawn
PEAK_HEADROOM_PER_LINE = 0.10
LOG_TICKS = (0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1_000, 2_000, 5_000, 10_000)
# Heights of the optional lower panels, against 3.0 for the main one. The cumulative
# panel is deliberately short: it is there for the overall trend, not for reading
# values off. PANEL_INCH is the figure height each unit of panel height adds.
MAIN_PANEL_HEIGHT = 3.0
CUMULATIVE_PANEL_HEIGHT = 0.8
SHARE_PANEL_HEIGHT = 1.0
PANEL_INCH = 1.8


# Each user keeps the same colour in every chart, so a line, a shaded span and a bar
# for one person always agree. Keyed by lowercased username.
USER_COLORS = {
    "megamoleys": "#3B2E8F",   # navy leaning purple
    "triflicacid": "#E8730C",  # orange
}
# Used for any username not named above, in order. Red is left out so nothing competes
# with the crimson total line.
SPARE_COLORS = ("C2", "C4", "C5", "C6", "C7", "C8", "C9")
# Quantities belonging to the pair rather than to one person: the combined total,
# and the conversations they share.
TOTAL_COLOR = "crimson"
PAIR_COLOR = "#3F4A54"
# Topics, which are neither a person nor the pair. Orange, navy and crimson are left
# out because each already means something specific in these charts.
TOPIC_COLORS = ("#2CA02C", "#17BECF", "#BCBD22", "#8C564B", "#E377C2", "#7F7F7F",
                "#1B9E77", "#A6761D", "#66A61E", "#9467BD", "#D4A6C8", "#4E9A9A")
# The dates --relationship-dividers marks on every chart, and the label for each.
RELATIONSHIP_DIVIDERS = (("got together", "2025-11-30"), ("broke up", "2026-09-19"))
DIVIDER_COLOR = "black"
DATE_FORMATTERS = (mdates.DateFormatter, mdates.AutoDateFormatter, mdates.ConciseDateFormatter)
_dividers: list[tuple[pd.Timestamp, str]] = []  # filled by show_dividers
# Sequential ramp for magnitude, one hue running light to dark. Teal deliberately:
# orange and navy already mean a specific person everywhere else in these charts.
HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "rhythm", ["#F3FAF9", "#A8D9D3", "#4A9E95", "#1E6B64", "#0C3B37"])


def diverging_cmap(low: str, high: str) -> LinearSegmentedColormap:
    """A ramp from one colour through white to another, for a difference between two.

    Grey marks cells with nothing to compare, which keeps them apart from the white
    of an even match.
    """
    return LinearSegmentedColormap.from_list("difference", [low, "white", high]).with_extremes(
        bad="#E4E4E4")


def user_colors(users) -> dict[str, str]:
    """One stable colour per user, so lines, shading and bars always agree.

    A user named in USER_COLORS keeps that colour whichever order --users lists them
    in, which is what stops two charts disagreeing about who is who.
    """
    spare = iter(SPARE_COLORS)
    colors = {}
    for u in users:
        fixed = USER_COLORS.get(str(u).lower())
        colors[u] = fixed if fixed else next(spare, "C7")
    return colors


def show_dividers(on: bool) -> None:
    """Turn the relationship dividers on or off for every chart drawn from here on."""
    _dividers[:] = [(pd.Timestamp(day), label) for label, day in RELATIONSHIP_DIVIDERS] if on else []


def dividers() -> list[tuple[pd.Timestamp, str]]:
    """The dates to mark and the label for each; empty unless they were turned on."""
    return list(_dividers)


def divider_positions(starts: pd.DatetimeIndex, period: str) -> list[tuple[float, str]]:
    """Where each divider falls on an axis that counts periods instead of dates.

    `starts` is the start of each period in order. A date part of the way through
    a period lands that far between its two edges, and one outside them is left out.
    """
    found = []
    for date, label in _dividers:
        i = starts.searchsorted(date, side="right") - 1
        if i < 0:
            continue
        part = (date - starts[i]) / (period_end(starts[i], period) - starts[i])
        if part < 1:
            found.append((i + part, label))
    return found


def draw_dividers(ax, positions: list[tuple[float, str]], vertical: bool = True,
                  labels: bool = True) -> None:
    """Draw a line across the axes at each position, with its label beside it.

    A vertical line is labelled at the foot of the axes, which is where these charts
    have the most room; the top is where peak labels and legends go.
    """
    box = dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8)
    for pos, label in positions:
        (ax.axvline if vertical else ax.axhline)(pos, color=DIVIDER_COLOR, linewidth=1.2,
                                                 alpha=0.85, zorder=8)
        if labels and vertical:
            ax.annotate(label, xy=(pos, 0), xycoords=ax.get_xaxis_transform(), xytext=(-4, 4),
                        textcoords="offset points", rotation=90, ha="right", va="bottom",
                        fontsize=8, color=DIVIDER_COLOR, zorder=8, bbox=box)
        elif labels:
            ax.annotate(label, xy=(1, pos), xycoords=ax.get_yaxis_transform(), xytext=(-4, 4),
                        textcoords="offset points", ha="right", va="bottom",
                        fontsize=8, color=DIVIDER_COLOR, zorder=8, bbox=box)


def _divide_date_axes(fig) -> None:
    """Mark the dividers on every panel whose x axis is dates.

    Done here, as the figure is saved, so that no chart has to ask for it. Only the
    first panel is labelled; on the ones under it the lines speak for themselves.
    """
    labelled = False
    for ax in fig.axes:
        if not ax.get_visible() or not isinstance(ax.xaxis.get_major_formatter(), DATE_FORMATTERS):
            continue
        low, high = ax.get_xlim()
        inside = [(mdates.date2num(date), label) for date, label in _dividers
                  if low <= mdates.date2num(date) <= high]
        draw_dividers(ax, inside, labels=not labelled)
        labelled = labelled or bool(inside)


def save(fig, out: str | Path) -> Path:
    """Write the figure, close it, and say where it went. Its folder is made if missing."""
    _divide_date_axes(fig)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"Chart saved to {out.resolve()}")
    return out


def chart_title(ax, title: str, note: str = "", lift: float = 0.0) -> None:
    """A chart's title, with an optional line of explanation under it in small grey type.

    The title names what is plotted and nothing else; how to read the chart goes in
    the note. `lift` raises both, in points, to clear tick labels along the top edge.
    """
    ax.set_title(title, fontsize=12, pad=6 + lift + (14 if note else 0))
    if note:
        ax.annotate(note, xy=(0.5, 1), xycoords="axes fraction", xytext=(0, 5 + lift),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9,
                    color="dimgrey")


def legend_below(ax, ncol: int = 4) -> None:
    """Legend under the axes, where it cannot cover an annotation."""
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=ncol,
              frameon=False, fontsize=9)


def place_peak_labels(ax, fig, labels: list[tuple], box_w: float = 62, box_h: float = 24) -> None:
    """Annotate peaks, nudging each label upwards until it clears the ones already placed.

    `labels` is [(date, value, text, color)]. Works in points (1/72 inch) so the
    spacing is the same whatever the data scale. Lower peaks are placed first, so
    a higher peak's label stacks above a lower neighbour's rather than hiding it.
    """
    to_pts = 72 / fig.dpi
    placed: list[tuple[float, float, float]] = []  # (x_centre, y_bottom, y_top) in points
    for date, value, text, color in sorted(labels, key=lambda l: l[1]):
        x, y = (c * to_pts for c in ax.transData.transform((mdates.date2num(date), value)))
        offset = 12.0
        while any(abs(x - px) < box_w and y + offset < ptop and y + offset + box_h > pbot
                  for px, pbot, ptop in placed):
            offset += 4
        placed.append((x, y + offset, y + offset + box_h))
        ax.annotate(
            text, xy=(date, value), xytext=(0, offset), textcoords="offset points",
            ha="center", va="bottom", fontsize=7.5, color=color, zorder=7, annotation_clip=False,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=0.6, alpha=0.9),
            arrowprops=dict(arrowstyle="-", color=color, lw=0.6),
        )


def span_label(ax, start, end, period, text, y, color) -> None:
    """Label the middle of a shaded span; rotate when the span is narrow."""
    stop = period_end(end, period)
    length = (stop - start).days
    ax.text(start + (stop - start) / 2, y, text, transform=ax.get_xaxis_transform(),
            ha="center", va="center", fontsize=7.5, color=color, zorder=6,
            rotation=90 if length < 10 * (1 if period == "D" else 7) else 0)


def rolling_sums(counts: pd.DataFrame, rolling: int = 0) -> pd.DataFrame:
    """Counts summed over the rolling window, so that a share or a rate taken from
    them covers the same stretch as a rolling-average line drawn above it."""
    return counts.rolling(rolling, min_periods=1).sum() if rolling > 1 else counts


def rolling_line(ax, series: pd.Series, color: str, label: str, rolling: int = 0,
                 period: str = "W", smoothed: pd.Series | None = None) -> None:
    """One line, or with `rolling` its average drawn over a faint copy of the raw line.

    `smoothed` replaces the plain rolling mean, for a ratio whose smooth form has to
    be worked out from rolling sums rather than by averaging the ratio itself.
    """
    if rolling > 1:
        if smoothed is None:
            smoothed = series.rolling(rolling, min_periods=1).mean()
        ax.plot(series.index, series, linewidth=0.6, alpha=0.25, color=color)
        ax.plot(smoothed.index, smoothed, linewidth=2, color=color,
                label=f"{label} ({rolling}-{unit(period)} avg)")
    else:
        ax.plot(series.index, series, color=color, linewidth=1.6,
                marker="o" if len(series) <= 60 else None, markersize=3, label=label)


def stack_date_axis(axes, index: pd.DatetimeIndex, period: str) -> None:
    """Give a stack of panels sharing one x axis its dates.

    The date axis belongs to the lowest panel; the rest keep their grid but drop it.
    """
    format_date_axis(axes[-1], index, period)
    for other in axes[:-1]:
        other.grid(True, which="major", alpha=0.4)
        other.grid(True, which="minor", axis="x", alpha=0.2, linestyle=":")
        other.tick_params(axis="x", which="both", labelbottom=False)


def narrow_date_axis(ax) -> None:
    """Thin out a date axis for a panel that shares the figure's width with others.

    A narrow panel has no room for a day label under every week, so those go and
    the month labels are tilted to fit.
    """
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.tick_params(axis="x", which="major", pad=3, labelsize=7.5, labelrotation=45)


def legend_under_figure(fig, ax, ncol: int = 4) -> None:
    """One legend under every panel, taken from the lines drawn on `ax`."""
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=ncol,
               frameon=False, fontsize=9)


def cumulative_panel(ax, counts: pd.DataFrame, total: bool = False) -> None:
    """Running total of each column, so slope is the rate and a flat stretch is silence.

    Always linear, whatever the main panel uses. A running total is already a sum, and
    a log axis would flatten exactly the changes in slope this panel exists to show.
    """
    colors = user_colors(counts.columns)
    for u in counts.columns:
        running = counts[u].cumsum()
        ax.plot(running.index, running, color=colors[u], linewidth=1.6,
                label=f"{u}: {running.iloc[-1]:,}")
    if total and len(counts.columns) > 1:
        running = counts.sum(axis=1).cumsum()
        ax.plot(running.index, running, color=TOTAL_COLOR, linewidth=1.2, alpha=0.85,
                label=f"total: {running.iloc[-1]:,}")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Cumulative")
    ax.yaxis.set_major_locator(plt.MaxNLocator(3))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:,.0f}"))
    ax.legend(loc="upper left", frameon=False, fontsize=7.5, ncol=len(counts.columns) + 1)


def share_panel(ax, counts: pd.DataFrame, period: str, ylabel: str = "Share (%)") -> None:
    """Stacked area showing each column's share of its period total, out of 100%.

    A dashed line at 50% makes parity easy to read. Periods in which nothing happened
    at all are left blank rather than drawn as an even split between nobody.
    """
    colors = user_colors(counts.columns)
    total = counts.sum(axis=1)
    share = counts.div(total.where(total > 0), axis=0) * 100  # NaN where nothing happened
    # step="post" draws each value up to the *next* point, so repeat the last row at the
    # end of its period; otherwise the final bucket would have zero width.
    end = period_end(share.index[-1], period)
    share = pd.concat([share, share.iloc[[-1]].set_axis([end])])
    total = pd.concat([total, total.iloc[[-1]].set_axis([end])])
    base = pd.Series(0.0, index=share.index)
    for u in counts.columns:
        upper = base + share[u]
        ax.fill_between(share.index, base, upper, where=total > 0, color=colors[u],
                        alpha=0.55, linewidth=0, step="post", label=f"{u} share")
        base = upper.fillna(base)
    ax.axhline(50, color="black", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_ylim(0, 100)
    ax.set_ylabel(ylabel)


def plot_lines(
    counts: pd.DataFrame,
    title: str,
    ylabel: str,
    out: str | Path,
    rolling: int = 0,
    period: str = "D",
    peaks: int = 0,
    peak_distance: int | None = None,
    quiet: list[tuple] | None = None,
    quiet_label: str = "quiet",
    user_quiet: dict[str, list[tuple]] | None = None,
    axis: str = "linear",
    total: bool = False,
    cumulative: bool = False,
    share: bool = False,
    smooth_share: bool = False,
    note: str = "",
) -> Path:
    """One line per column of `counts`, over a date axis.

    peaks       -> label the top-n local peaks of each line (on the smoothed line if rolling)
    quiet       -> spans when everyone was quiet: shaded grey
    user_quiet  -> {user: spans} when just that user was quiet: shaded in their faint colour
    axis        -> "log" to keep a handful of 900-message days from flattening the rest
    total       -> add a red line for the combined total across all columns
    cumulative  -> add a lower panel with the running total of each column
    share       -> add a lower panel with each column's share of the period total
    smooth_share -> take that share over the rolling window instead of one period,
                    for counts too small to give a steady share period by period
    note        -> a line of explanation under the title
    """
    noun = unit(period)
    span_days = (counts.index.max() - counts.index.min()).days
    width = 14 if span_days <= 550 else min(24, 14 * span_days / 550)
    # Extra panels stack under the main one, in this order, sharing its date axis.
    extras = [h for h, wanted in ((CUMULATIVE_PANEL_HEIGHT, cumulative),
                                  (SHARE_PANEL_HEIGHT, share)) if wanted]
    if extras:
        fig, axs = plt.subplots(1 + len(extras), 1,
                                figsize=(width, 6.5 + PANEL_INCH * sum(extras)), sharex=True,
                                gridspec_kw={"height_ratios": [MAIN_PANEL_HEIGHT] + extras})
        ax, lower_axes = axs[0], list(axs[1:])
    else:
        fig, ax = plt.subplots(figsize=(width, 6.5))
        lower_axes = []
    distance = peak_distance if peak_distance is not None else DEFAULT_PEAK_DISTANCE[period]
    colors = user_colors(counts.columns)
    peak_labels: list[tuple] = []  # placed at the end, once the axis limits are final

    # --- shading (behind the lines) -----------------------------------------
    for k, (user, spans) in enumerate((user_quiet or {}).items()):
        for i, (start, end, length, _msgs) in enumerate(spans):
            ax.axvspan(start, period_end(end, period), color=colors[user], alpha=0.12,
                       linewidth=0, zorder=0,
                       label=f"{user} {quiet_label} (top {len(spans)})" if i == 0 else None)
            span_label(ax, start, end, period,
                       f"{user} #{i + 1}: {length} {noun}{'s' * (length != 1)}",
                       0.30 - 0.14 * k, colors[user])

    for i, (start, end, length, _msgs) in enumerate(quiet or []):
        ax.axvspan(start, period_end(end, period), color="grey", alpha=0.25, linewidth=0,
                   zorder=0.5,
                   label=f"both {quiet_label} (top {len(quiet)})" if i == 0 else None)
        span_label(ax, start, end, period, f"both #{i + 1}: {length} {noun}{'s' * (length != 1)}",
                   0.55, "dimgrey")

    # --- lines and peak labels ----------------------------------------------
    for user in counts.columns:
        series, color = counts[user], colors[user]
        if rolling > 1:
            ax.plot(series.index, series, linewidth=0.6, alpha=0.25, color=color)
            shown = series.rolling(rolling, min_periods=1).mean()
            ax.plot(series.index, shown, linewidth=2, color=color,
                    label=f"{user} ({rolling}-{noun} avg)")
        else:
            shown = series
            ax.plot(series.index, series, linewidth=1.5 if period != "D" else 1.2, color=color,
                    marker="o" if len(series) <= 60 else None, markersize=3, label=user)

        if peaks:
            for date, value in find_peaks(shown, peaks, distance).items():
                text = f"{series[date]:,}" if rolling <= 1 else f"{value:.1f} avg"
                peak_labels.append((date, value, f"{text}\n{fmt_date(date, period, short=True)}",
                                    color))
                ax.plot(date, value, "o", color=color, markersize=5, zorder=5)

    # Combined total, last so it sits over the user lines. It carries no peak labels;
    # those belong to the individual lines.
    if total and len(counts.columns) > 1:
        combined = counts.sum(axis=1)
        drawn = combined.rolling(rolling, min_periods=1).mean() if rolling > 1 else combined
        ax.plot(combined.index, drawn, color=TOTAL_COLOR, linewidth=1.1, alpha=0.85, zorder=4,
                label=f"total ({combined.sum():,})")

    # --- axes ----------------------------------------------------------------
    chart_title(ax, title, note)
    ax.set_ylabel(ylabel)
    if axis == "log":
        # symlog, not log: silent days are real zeros, and a plain log axis would drop
        # them without a word. Below linthresh the axis is linear, so 0 has a place.
        ax.set_yscale("symlog", linthresh=1, linscale=0.4)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:,.0f}"))
        ax.yaxis.set_minor_formatter(plt.NullFormatter())
        ceiling = max(counts.sum(axis=1).max() if total else counts.max().max(), 1)
        ax.set_yticks([t for t in LOG_TICKS if t <= ceiling * 2])
    ax.set_ylim(bottom=0)
    if peaks:  # leave headroom for the labels
        headroom = (PEAK_HEADROOM_LOG if axis == "log" else
                    PEAK_HEADROOM_LINEAR + PEAK_HEADROOM_PER_LINE * len(counts.columns))
        ax.set_ylim(top=ax.get_ylim()[1] * headroom)
    # Fill the extra panels in the order they were stacked.
    panels = iter(lower_axes)
    if cumulative:
        cumulative_panel(next(panels), counts, total=total)
    if share:
        share_panel(next(panels), rolling_sums(counts, rolling) if smooth_share else counts,
                    period, ylabel=f"Share of {ylabel.lower()} (%)")

    stack_date_axis([ax] + lower_axes, counts.index, period)
    ax.set_xlim(counts.index.min() - pd.Timedelta(days=2),
                period_end(counts.index.max(), period) + pd.Timedelta(days=2))
    place_peak_labels(ax, fig, peak_labels)

    if lower_axes:
        # One legend under the stack, taken from the lines rather than the panels.
        legend_under_figure(fig, ax, ncol=5)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
    else:
        legend_below(ax, ncol=5)
        fig.tight_layout()
    return save(fig, out)
