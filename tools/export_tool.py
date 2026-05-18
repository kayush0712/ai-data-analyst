import uuid

def export_csv(df):

    export_id = str(uuid.uuid4())

    export_path = (
        f"generated_csv/{export_id}.csv"
    )

    df.to_csv(
        export_path,
        index=False
    )

    return export_path