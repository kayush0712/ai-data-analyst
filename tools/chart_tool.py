import math
import os
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from helpers.dtype_helper import prepare_dataframe
from helpers.chart_helper import parse_chart_columns


# ── Config ────────────────────────────────────────────────────────────────────

FIGSIZE              = (12, 6)
BAR_COLOR            = "#2563EB"
SCATTER_COLOR        = "#2563EB"
LINE_COLOR           = "#2563EB"
NUMERIC_X_BIN_THRESH = 20   # bin x-axis if unique numeric values exceed this
ROTATE_THRESH        = 12   # rotate x labels if tick count exceeds this


# ── Utilities ─────────────────────────────────────────────────────────────────

def _is_numeric(df: pd.DataFrame, col: str) -> bool:
    return pd.api.types.is_numeric_dtype(df[col])


def _unique_count(series: pd.Series) -> int:
    return series.nunique(dropna=True)


def _bin_numeric_series(series: pd.Series) -> pd.Series:
    """Bin a continuous numeric series into labelled range intervals."""
    n_unique = _unique_count(series)
    n_bins = max(5, min(20, int(math.ceil(math.log2(n_unique) + 1))))
    try:
        binned = pd.cut(series, bins=n_bins)
    except Exception:
        return series

    def _fmt(interval) -> str:
        lo, hi = interval.left, interval.right
        if lo == int(lo) and hi == int(hi):
            return f"{int(lo):,}–{int(hi):,}"
        return f"{lo:.1f}–{hi:.1f}"

    return binned.map(_fmt)


def _aggregate(df: pd.DataFrame, x_col: str, y_col: str) -> tuple[pd.Series, pd.Series]:
    """Group by x_col and return mean of y_col."""
    grouped = (
        df.groupby(x_col, observed=True)[y_col]
        .mean()
        .dropna()
        .reset_index()
    )
    return grouped[x_col], grouped[y_col]


def _pick_label_column(df: pd.DataFrame, cat_cols: list, y_col: str):
    """
    Auto-pick a categorical x-axis column.
    Never picks temporal columns (year/date/month etc.)
    """
    _skip = ("year", "date", "month", "quarter", "time", "period")

    def _is_temporal(col: str) -> bool:
        return any(kw in col.lower() for kw in _skip)

    preferred = ("employee", "name", "department", "category", "label", "city")
    for hint in preferred:
        for col in cat_cols:
            if hint in col.lower() and col != y_col and not _is_temporal(col):
                return col

    for col in cat_cols:
        if col != y_col and not _is_temporal(col):
            return col

    return None


def _is_valid_chart_path(path) -> bool:
    """Return True only if path is a real generated chart file."""
    if not path or not isinstance(path, str):
        return False
    normalized = path.replace("\\", "/")
    return normalized.startswith("generated_charts/") and normalized.endswith(".png")


# ── Chart-type decision ───────────────────────────────────────────────────────

def _decide_chart_type(df: pd.DataFrame, x_col, y_col) -> str:
    """
    Pick the best chart type:
      x=None, y set       -> histogram
      y=None              -> bar
      both numeric,
        x high-card       -> scatter
        x is year-like    -> line
        x low-card        -> bar
      categorical x       -> bar
    """
    # No x → distribution of y
    if x_col is None and y_col is not None:
        return "histogram"

    # No y → nothing sensible to show
    if y_col is None:
        return "bar"

    x_num = _is_numeric(df, x_col)
    y_num = _is_numeric(df, y_col)
    x_unique = _unique_count(df[x_col])

    if x_num and y_num:
        if x_unique > NUMERIC_X_BIN_THRESH:
            return "scatter"
        if any(kw in x_col.lower() for kw in ("year", "date", "month", "quarter")):
            return "line"
        return "bar"

    return "bar"


# ── Renderers ─────────────────────────────────────────────────────────────────

def _rotate_xticks(ax, n: int) -> None:
    if n > ROTATE_THRESH:
        ax.set_xticklabels(
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
            fontsize=max(6, 9 - n // 15),
        )


def _smart_ylim(y_vals):
    """
    Return (ymin, ymax) for year-like or compressed-range y values.
    Returns None to let matplotlib use its default (0-based) otherwise.
    """
    try:
        vals = [v for v in y_vals if v is not None]
        if not vals:
            return None
        lo, hi = min(vals), max(vals)
        if 1900 <= lo and hi <= 2100:           # year column
            return lo - 1, hi + 1
        if lo > 0 and hi > 0 and (lo / hi) > 0.5:  # compressed range
            pad = (hi - lo) * 0.1 or hi * 0.05
            return lo - pad, hi + pad
    except Exception:
        pass
    return None


def _render_bar(ax, x_vals, y_vals, x_label: str, y_label: str, title: str, binned: bool) -> None:
    xs = [str(v) for v in x_vals]
    ax.bar(xs, y_vals, color=BAR_COLOR, width=0.6)
    ax.set_xlabel(f"{x_label}  (grouped into ranges)" if binned else x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    _rotate_xticks(ax, len(xs))
    ylim = _smart_ylim(y_vals)
    if ylim is not None:
        ax.set_ylim(bottom=ylim[0], top=ylim[1])


def _render_scatter(ax, x_vals, y_vals, x_label: str, y_label: str, title: str) -> None:
    ax.scatter(x_vals, y_vals, color=SCATTER_COLOR, alpha=0.65, s=45, edgecolors="none")
    try:
        m, b = np.polyfit(x_vals.astype(float), y_vals.astype(float), 1)
        xs = np.linspace(x_vals.min(), x_vals.max(), 300)
        ax.plot(xs, m * xs + b, color="#DC2626", linewidth=1.5,
                linestyle="--", label="trend")
        ax.legend(fontsize=9)
    except Exception:
        pass
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)


def _render_line(ax, x_vals, y_vals, x_label: str, y_label: str, title: str) -> None:
    ax.plot(list(x_vals), list(y_vals), color=LINE_COLOR,
            linewidth=2, marker="o", markersize=5)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    _rotate_xticks(ax, len(x_vals))


def _render_histogram(ax, y_vals, y_label: str, title: str) -> None:
    ax.hist(y_vals.dropna(), bins="auto", color=BAR_COLOR, edgecolor="white")
    ax.set_xlabel(y_label)
    ax.set_ylabel("count")
    ax.set_title(title)


# ── Main public function ──────────────────────────────────────────────────────

def generate_chart(
    df: pd.DataFrame,
    chart_type: str = "bar",
    x_col=None,
    y_col=None,
    question: str = None,
) -> str:
    """
    Generate a chart PNG and return its file path, or None on failure.
    """
    os.makedirs("generated_charts", exist_ok=True)
    plot_df = prepare_dataframe(df.copy())

    # ── 1. Parse columns from question ───────────────────────────────────────
    if question and not (x_col and y_col):
        parsed_x, parsed_y = parse_chart_columns(plot_df, question)
        x_col = x_col or parsed_x
        y_col = y_col or parsed_y

    # Remember if x was explicitly mentioned — if not, don't auto-pick one
    x_was_explicit = x_col is not None

    numeric_cols = plot_df.select_dtypes(include="number").columns.tolist()
    cat_cols     = plot_df.select_dtypes(include=["object", "string"]).columns.tolist()

    # ── 2. Validate columns ───────────────────────────────────────────────────
    if x_col and x_col not in plot_df.columns:
        x_col = None
        x_was_explicit = False
    if y_col and y_col not in plot_df.columns:
        y_col = None
    if y_col and not _is_numeric(plot_df, y_col):
        y_col = None

    # Fallback y to first numeric column
    if not y_col:
        y_col = numeric_cols[0] if numeric_cols else None
    if not y_col:
        return None

    # Only auto-pick x when user explicitly asked for two columns
    # ("salary by department") — not for single-column ("show salary")
    if not x_col and x_was_explicit:
        x_col = _pick_label_column(plot_df, cat_cols, y_col)
    elif not x_col:
        x_col = None   # histogram path

    # ── 3. Decide chart type ──────────────────────────────────────────────────
    smart_type = _decide_chart_type(plot_df, x_col, y_col)

    # ── 4. Prepare data ───────────────────────────────────────────────────────
    needs_binning = False
    x_vals = None
    y_vals = None

    if smart_type == "histogram":
        y_vals = plot_df[y_col]

    elif smart_type == "scatter":
        x_vals = plot_df[x_col]
        y_vals = plot_df[y_col]

    else:  # bar or line
        if x_col:
            if _is_numeric(plot_df, x_col) and _unique_count(plot_df[x_col]) > NUMERIC_X_BIN_THRESH:
                needs_binning = True
                plot_df = plot_df.copy()
                plot_df["__x_binned__"] = _bin_numeric_series(plot_df[x_col])
                x_vals, y_vals = _aggregate(plot_df, "__x_binned__", y_col)
            else:
                x_vals, y_vals = _aggregate(plot_df, x_col, y_col)
                if smart_type == "bar":
                    order = y_vals.argsort()[::-1]
                    x_vals = x_vals.iloc[order].reset_index(drop=True)
                    y_vals = y_vals.iloc[order].reset_index(drop=True)
        else:
            # x_col is None but type is bar — fall back to histogram
            smart_type = "histogram"
            y_vals = plot_df[y_col]

    # ── 5. Titles & labels ────────────────────────────────────────────────────
    x_label = (f"{x_col} (range)" if needs_binning else x_col) or ""
    y_label = y_col or ""

    if smart_type == "histogram":
        title = f"Distribution of {y_col}"
    elif smart_type == "scatter":
        title = f"{y_col} vs {x_col}"
    else:
        title = f"{y_col} by {x_col}"

    # ── 6. Render ─────────────────────────────────────────────────────────────
    chart_path = f"generated_charts/{uuid.uuid4()}.png"
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    try:
        if smart_type == "histogram":
            _render_histogram(ax, y_vals, y_label, title)
        elif smart_type == "scatter" and x_vals is not None and y_vals is not None:
            _render_scatter(ax, x_vals, y_vals, x_label, y_label, title)
        elif smart_type == "line" and x_vals is not None and y_vals is not None:
            _render_line(ax, x_vals, y_vals, x_label, y_label, title)
        elif x_vals is not None and y_vals is not None:
            _render_bar(ax, x_vals, y_vals, x_label, y_label, title, needs_binning)
        else:
            # Final safety net — if x_vals somehow still None, show histogram
            _render_histogram(ax, plot_df[y_col], y_label, f"Distribution of {y_col}")

        plt.tight_layout()
        plt.savefig(chart_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return chart_path

    except Exception:
        import traceback
        traceback.print_exc()
        plt.close(fig)
        return None