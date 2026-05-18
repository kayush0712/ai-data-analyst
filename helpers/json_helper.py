import math

import numpy as np
import pandas as pd


def _sanitize_value(value):
    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

        return value

    if isinstance(value, (np.floating, np.integer)):
        item = value.item()

        if isinstance(item, float) and (
            math.isnan(item) or math.isinf(item)
        ):
            return None

        return item

    if pd.isna(value):
        return None

    return value


def dataframe_to_records(df, limit=100):
    subset = df.head(limit)
    records = []

    for row in subset.to_dict(orient="records"):
        clean_row = {}

        for key, value in row.items():
            clean_row[key] = _sanitize_value(value)

        records.append(clean_row)

    return records
