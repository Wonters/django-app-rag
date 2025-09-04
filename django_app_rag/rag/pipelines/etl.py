from pathlib import Path
from django_app_rag.logging import get_logger_loguru
from zenml import pipeline
from ..steps.etl import add_quality_score, crawl
from ..steps.infrastructure import (
    read_documents_from_disk,
    combine_documents,
    move_tmp_files,
)
from ..steps.infrastructure.save_to_diskstorage import save_to_diskstorage

logger = get_logger_loguru(__name__)

@pipeline(enable_cache=True)
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
    storage_mode: str = "overwrite",
) -> None:
    """Pipeline ETL qui traite les données de Notion, fichiers et URLs. Avec un crawler pour les URLs enfants et un agent de qualité.
    
    Args:
        data_dir: Chemin vers le répertoire de données
        collection_name: Nom de la collection
        to_s3: Si True, les documents sont sauvegardés dans S3
        max_workers: Nombre de workers pour le crawler
        quality_agent_model_id: ID du modèle de qualité
        quality_agent_mock: Si True, le modèle de qualité est mock
        include_notion: Si True, les documents de Notion sont inclus
        include_files: Si True, les documents de fichiers sont inclus
        include_urls: Si True, les documents d'URLs sont inclus
        storage_mode: Mode de stockage - "overwrite" (écrase tout) ou "append" (ajoute)
    """
    logger.info("--------------------------------")
    logger.info(f"Storage mode: {storage_mode}")
    logger.info(f"Data dir: {data_dir}")
    logger.info(f"Collection name: {collection_name}")
    logger.info(f"To s3: {to_s3}")
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Quality agent model id: {quality_agent_model_id}")
    logger.info(f"Quality agent mock: {quality_agent_mock}")
    logger.info(f"Include notion: {include_notion}")
    logger.info(f"Include files: {include_files}")
    logger.info(f"Include urls: {include_urls}")
    logger.info("--------------------------------")
    notion_documents = None
    files_documents = None
    urls_documents = None

    root_data_dir = data_dir

    if storage_mode == "append":
        data_dir = data_dir / "tmp"
    
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
    
    # Sauvegarder dans le stockage disque avec msgpack
    save_to_diskstorage(
        documents=enhanced_documents, 
        collection_name=collection_name, 
        data_dir=root_data_dir.as_posix(),
        mode=storage_mode
    )
    move_tmp_files(data_dir=root_data_dir, storage_mode=storage_mode)