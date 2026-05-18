import pandas as pd

def build_dataset_summary(df):

    summary_lines = []

    summary_lines.append(
        f"Rows: {df.shape[0]}"
    )

    summary_lines.append(
        f"Columns: {df.shape[1]}"
    )

    summary_lines.append(
        "\nCOLUMN DETAILS:"
    )

    for col in df.columns:

        summary_lines.append(
            f"- {col} ({df[col].dtype})"
        )

    summary_lines.append(
        "\nSAMPLE DATA:"
    )

    summary_lines.append(
        df.head(5).to_string(index=False)
    )

    return "\n".join(summary_lines)