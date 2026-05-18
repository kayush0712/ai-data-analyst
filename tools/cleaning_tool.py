import pandas as pd

def clean_dataset(df):

    cleaned_df = df.copy()

    cleaned_df = cleaned_df.drop_duplicates()

    numeric_cols = cleaned_df.select_dtypes(
        include="number"
    ).columns

    cleaned_df[numeric_cols] = cleaned_df[
        numeric_cols
    ].fillna(
        cleaned_df[numeric_cols].mean()
    )

    object_cols = cleaned_df.select_dtypes(
        include="object"
    ).columns

    cleaned_df[object_cols] = cleaned_df[
        object_cols
    ].fillna("Unknown")

    cleaned_df.columns = [

        col.strip().lower().replace(
            " ",
            "_"
        )

        for col in cleaned_df.columns
    ]

    return cleaned_df