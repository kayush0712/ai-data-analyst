from config import TABLE_DISPLAY_LIMIT

from services import dataset_service

register_dataset = dataset_service.register_dataset
list_datasets = dataset_service.list_datasets
set_active_dataset = dataset_service.set_active_dataset
get_dataset = dataset_service.get_dataset
update_dataset_dataframe = (
    dataset_service.update_dataset_dataframe
)

ACTIVE_DATASET_ID = None
