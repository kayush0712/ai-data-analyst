import os
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from helpers.dtype_helper import prepare_dataframe
from helpers.chart_helper import parse_chart_columns


def _pick_label_column(plot_df, cat_cols, y_col):
    preferred = (
        "employee", "name", "department",
        "category", "label",
    )

    for hint in preferred:
        for col in cat_cols:
            if hint in col.lower() and col != y_col:
                return col

    for col in cat_cols:
        if col != y_col:
            return col

    return None


def generate_chart(
    df,
    chart_type="bar",
    x_col=None,
    y_col=None,
    question=None,
):
    os.makedirs("generated_charts", exist_ok=True)

    plot_df = prepare_dataframe(df)

    if question and not x_col and not y_col:
        parsed_x, parsed_y = parse_chart_columns(
            plot_df,
            question,
        )
        x_col = x_col or parsed_x
        y_col = y_col or parsed_y

    numeric_cols = plot_df.select_dtypes(
        include="number"
    ).columns.tolist()

    cat_cols = plot_df.select_dtypes(
        include=["object", "string"]
    ).columns.tolist()

    if y_col and y_col not in plot_df.columns:
        y_col = None

    if x_col and x_col not in plot_df.columns:
        x_col = None

    if y_col and y_col not in numeric_cols:
        if pd.api.types.is_numeric_dtype(
            plot_df[y_col]
        ):
            numeric_cols.append(y_col)
        else:
            y_col = None

    if not numeric_cols and not y_col:
        return None

    if not y_col:
        y_col = numeric_cols[0]

    if not x_col:
        x_col = _pick_label_column(
            plot_df,
            cat_cols,
            y_col,
        )

    chart_id = str(uuid.uuid4())
    chart_path = f"generated_charts/{chart_id}.png"

    fig, ax = plt.subplots(figsize=(10, 6))

    try:
        if x_col and y_col and x_col != y_col:
            if x_col in cat_cols or not pd.api.types.is_numeric_dtype(
                plot_df[x_col]
            ):
                grouped = (
                    plot_df.groupby(
                        x_col,
                        dropna=False,
                    )[y_col]
                    .mean()
                    .dropna()
                    .sort_values(ascending=False)
                )

                if grouped.empty:
                    plt.close(fig)
                    return None

                grouped.plot(
                    kind="bar",
                    ax=ax,
                    color="#2563eb",
                )
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                ax.set_title(f"{y_col} by {x_col}")

            else:
                plot_df.plot(
                    x=x_col,
                    y=y_col,
                    kind=chart_type,
                    ax=ax,
                )
                ax.set_title(f"{y_col} vs {x_col}")

        else:
            series = plot_df[y_col].dropna()

            if series.empty:
                plt.close(fig)
                return None

            series.plot(
                kind="bar",
                ax=ax,
                color="#2563eb",
            )
            ax.set_ylabel(y_col)
            ax.set_title(f"{y_col}")

        ax.tick_params(axis="x", rotation=45)
        plt.tight_layout()
        plt.savefig(chart_path, dpi=120)
        plt.close(fig)

        return chart_path

    except Exception:
        plt.close(fig)
        return None
