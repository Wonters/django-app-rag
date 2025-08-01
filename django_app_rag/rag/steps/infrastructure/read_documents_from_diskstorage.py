from zenml import step
from typing_extensions import Annotated
from django_app_rag.rag.models import Document
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage
from loguru import logger
@step
def read_documents_from_diskstorage(
    collection_name: str,
    limit: int = 1000,
    data_dir: str = "data"
) -> Annotated[list[Document], "documents"]:
    storage = DiskStorage(model_class=Document, collection_name=collection_name, data_dir=data_dir)
    documents = storage.read()
    logger.info(f"Documents read from diskstorage: {len(documents)}")
    return documents