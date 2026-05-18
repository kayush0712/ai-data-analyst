from difflib import get_close_matches

def find_matching_dataset(
    selected_filename,
    all_datasets
):

    filenames = [
        dataset["filename"]
        for dataset in all_datasets
    ]

    for dataset in all_datasets:

        if dataset["filename"] == selected_filename:
            return dataset

    for dataset in all_datasets:

        if dataset["filename"].lower() == selected_filename.lower():
            return dataset

    close = get_close_matches(
        selected_filename,
        filenames,
        n=1,
        cutoff=0.5
    )

    if close:

        for dataset in all_datasets:

            if dataset["filename"] == close[0]:
                return dataset

    return None