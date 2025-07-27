from pathlib import Path

from zenml import pipeline

from ..steps.infrastructure import read_documents_from_disk
from ..steps.infrastructure.save_to_diskstorage import save_to_diskstorage


@pipeline
def etl_precomputed(
    data_dir: Path,
    collection_name: str,
) -> None:
    crawled_data_dir = data_dir / "crawled"
    documents = read_documents_from_disk(
        data_directory=crawled_data_dir, nesting_level=0
    )
    save_to_diskstorage(documents=documents, collection_name=collection_name)
