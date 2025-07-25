from zenml import step
from typing_extensions import Annotated
from django_app_rag.rag.models import Document
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage

@step
def read_documents_from_diskstorage(
    collection_name: str,
    limit: int = 1000,
) -> Annotated[list[Document], "documents"]:
    storage = DiskStorage(model_class=Document, collection_name=collection_name)
    documents = storage.read()
    return documents