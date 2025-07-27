from pathlib import Path

from loguru import logger
from zenml import pipeline

from ..steps.etl import add_quality_score, crawl
from ..steps.infrastructure import (
    read_documents_from_disk,
    save_documents_to_disk,
    upload_to_s3,
    combine_documents,
)
from ..steps.infrastructure.save_to_diskstorage import save_to_diskstorage


@pipeline
def etl_mixed(
    data_dir: Path,
    collection_name: str,
    to_s3: bool = False,
    max_workers: int = 10,
    quality_agent_model_id: str = "gpt-4o-mini",
    quality_agent_mock: bool = True,
    include_notion: bool = True,
    include_files: bool = True,
    include_urls: bool = True,
) -> None:
    """Pipeline ETL qui traite les données de Notion, fichiers et URLs."""
    
    notion_documents = None
    files_documents = None
    urls_documents = None
    
    # Traiter les données Notion
    if include_notion:
        notion_data_dir = data_dir / "notion"
        if notion_data_dir.exists() and any(notion_data_dir.iterdir()):
            logger.info(f"Reading notion data from {notion_data_dir}")
            notion_documents = read_documents_from_disk(
                data_directory=notion_data_dir, nesting_level=1
            )
    
    # Traiter les données de fichiers
    if include_files:
        files_data_dir = data_dir / "files"
        if files_data_dir.exists() and any(files_data_dir.iterdir()):
            logger.info(f"Reading files data from {files_data_dir}")
            files_documents = read_documents_from_disk(
                data_directory=files_data_dir, nesting_level=0
            )
    
    # Traiter les données d'URLs
    if include_urls:
        urls_data_dir = data_dir / "urls"
        if urls_data_dir.exists() and any(urls_data_dir.iterdir()):
            logger.info(f"Reading URLs data from {urls_data_dir}")
            urls_documents = read_documents_from_disk(
                data_directory=urls_data_dir, nesting_level=0
            )
    
    # Combiner tous les documents
    all_documents = combine_documents(
        notion_documents=notion_documents,
        files_documents=files_documents,
        urls_documents=urls_documents,
    )
    
    if not all_documents:
        logger.warning("No documents found to process")
        return
    
    
    # Crawler les URLs des documents (si applicable)
    crawled_documents = crawl(documents=all_documents, max_workers=max_workers)
    
    # Ajouter les scores de qualité
    enhanced_documents = add_quality_score(
        documents=crawled_documents,
        model_id=quality_agent_model_id,
        mock=quality_agent_mock,
        max_workers=max_workers,
    )

    # Sauvegarder les documents traités
    crawled_data_dir = data_dir / "crawled"
    logger.info(f"Saving processed data to {crawled_data_dir}")
    
    save_documents_to_disk(documents=enhanced_documents, output_dir=crawled_data_dir)
    
    if to_s3:
        upload_to_s3(
            folder_path=crawled_data_dir,
            s3_prefix="second_brain_course/crawled",
            after="save_documents_to_disk",
        )
    
    # Sauvegarder dans le stockage disque
    save_to_diskstorage(documents=enhanced_documents, collection_name=collection_name, data_dir=data_dir.as_posix()) 