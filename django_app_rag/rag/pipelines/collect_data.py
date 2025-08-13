from pathlib import Path
from typing import Optional

from loguru import logger
from zenml import pipeline

from ..steps.collect_file_data import extract_file_documents
from ..steps.collect_url_data import extract_url_documents
from ..steps.collect_notion_data import (
    extract_notion_documents,
    extract_notion_documents_metadata,
)
from ..steps.infrastructure import save_documents_to_disk, upload_to_s3


@pipeline(enable_cache=False)
def collect_data(
    data_dir: Path,
    file_paths: Optional[list[Path]] = None,
    urls: Optional[list[str]] = None,
    notion_database_ids: Optional[list[str]] = None,
    to_s3: bool = False,
    max_workers: int = 10,
) -> None:
    """
    Pipeline unifiée pour collecter des données depuis différentes sources :
    - Fichiers locaux
    - URLs web
    - Bases de données Notion
    
    Args:
        data_dir: Répertoire de sortie pour les données collectées
        file_paths: Liste des chemins de fichiers à traiter
        urls: Liste des URLs à traiter
        notion_database_ids: Liste des IDs de bases de données Notion
        to_s3: Si True, upload les données vers S3
        max_workers: Nombre maximum de workers pour le traitement des URLs
    """
    invocation_ids = []
    
    # Collecte des données depuis les fichiers
    if file_paths:
        file_data_dir = data_dir / "files"
        file_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Collecting content from {len(file_paths)} files")
        documents_data = extract_file_documents(file_paths=file_paths)
        
        result = save_documents_to_disk(
            documents=documents_data,
            output_dir=file_data_dir,
        )
        invocation_ids.append(result.invocation_id)
    
    # Collecte des données depuis les URLs
    if urls:
        url_data_dir = data_dir / "urls"
        url_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Collecting content from {len(urls)} URLs")
        documents_data = extract_url_documents(urls=urls, max_workers=max_workers)
        
        result = save_documents_to_disk(
            documents=documents_data,
            output_dir=url_data_dir,
        )
        invocation_ids.append(result.invocation_id)
    
    # Collecte des données depuis Notion
    if notion_database_ids:
        notion_data_dir = data_dir / "notion"
        notion_data_dir.mkdir(parents=True, exist_ok=True)
        
        for index, database_id in enumerate(notion_database_ids):
            logger.info(f"Collecting pages from database '{database_id}'")
            documents_metadata = extract_notion_documents_metadata(database_id=database_id)
            documents_data = extract_notion_documents(documents_metadata=documents_metadata)
            
            result = save_documents_to_disk(
                documents=documents_data,
                output_dir=notion_data_dir / f"database_{index}",
            )
            invocation_ids.append(result.invocation_id)
    
    # Upload vers S3 si demandé
    if to_s3 and invocation_ids:
        # Upload des fichiers
        if file_paths:
            upload_to_s3(
                folder_path=data_dir / "files",
                s3_prefix="second_brain_course/files",
                after=invocation_ids,
            )
        
        # Upload des URLs
        if urls:
            upload_to_s3(
                folder_path=data_dir / "urls",
                s3_prefix="second_brain_course/urls",
                after=invocation_ids,
            )
        
        # Upload de Notion
        if notion_database_ids:
            upload_to_s3(
                folder_path=data_dir / "notion",
                s3_prefix="second_brain_course/notion",
                after=invocation_ids,
            )
    
    logger.info("Data collection pipeline completed successfully") 