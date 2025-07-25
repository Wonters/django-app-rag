from zenml import step
from typing_extensions import Annotated
from django_app_rag.rag.models import Document
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage

@step
def save_to_diskstorage(
    documents: list,
    collection_name: str
) -> Annotated[bool, "success"]:
    storage = DiskStorage(model_class=Document, collection_name=collection_name)
    storage.save(documents)
    return True 