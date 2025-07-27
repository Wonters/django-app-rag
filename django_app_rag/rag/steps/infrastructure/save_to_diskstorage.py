from zenml import step
from typing_extensions import Annotated
from django_app_rag.rag.models import Document
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage

@step
def save_to_diskstorage(
    documents: list,
    collection_name: str,
    data_dir: str = "data"
) -> Annotated[bool, "success"]:
    storage = DiskStorage(model_class=Document, collection_name=collection_name, data_dir=data_dir)
    storage.save(documents)
    return True 