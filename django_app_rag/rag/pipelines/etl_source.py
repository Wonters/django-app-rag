from pathlib import Path
from loguru import logger
from zenml import pipeline
from ..steps.etl import add_quality_score, crawl
from ..steps.infrastructure import save_to_diskstorage
from ..steps.collect_file_data import extract_file_documents
from ..steps.collect_url_data import extract_url_documents
from ..steps.collect_notion_data import extract_notion_documents


@pipeline
def etl_single_source(
    data_dir: Path,
    collection_name: str,
    source_type: str,
    source_identifier: str,
    to_s3: bool = False,
    max_workers: int = 10,
    quality_agent_model_id: str = "gpt-4o-mini",
    quality_agent_mock: bool = True,
    storage_mode: str = "append",
) -> None:
    """
    Pipeline ETL pour traiter une seule source et l'ajouter à l'index existant.
    
    Args:
        data_dir: Chemin vers le répertoire de données
        collection_name: Nom de la collection
        source_type: Type de source ('file', 'url', 'notion')
        source_identifier: Identifiant de la source (chemin, URL, ID Notion)
        to_s3: Si True, les documents sont sauvegardés dans S3
        max_workers: Nombre de workers pour le crawler
        quality_agent_model_id: ID du modèle de qualité
        quality_agent_mock: Si True, le modèle de qualité est mock
        storage_mode: Mode de stockage - "overwrite" (écrase tout) ou "append" (ajoute)
    """
    
    # 1. Collecter les données de la source spécifique
    source_documents = None
    
    if source_type == "file":
        file_path = Path(source_identifier)
        if file_path.exists():
            logger.info(f"Traitement du fichier: {file_path}")
            source_documents = extract_file_documents(file_paths=[file_path])
    
    elif source_type == "url":
        logger.info(f"Traitement de l'URL: {source_identifier}")
        source_documents = extract_url_documents(urls=[source_identifier])
    
    elif source_type == "notion":
        logger.info(f"Traitement de la base Notion: {source_identifier}")
        source_documents = extract_notion_documents(notion_database_ids=[source_identifier])
    
    if not source_documents:
        logger.warning(f"Aucun document trouvé pour la source {source_identifier}")
        return
    
    # 2. Crawler les URLs des documents (si applicable)
    crawled_documents = crawl(documents=source_documents, max_workers=max_workers)
    
    # 3. Ajouter les scores de qualité
    enhanced_documents = add_quality_score(
        documents=crawled_documents,
        model_id=quality_agent_model_id,
        mock=quality_agent_mock,
        max_workers=max_workers,
    )
    
    # 4. Sauvegarder dans le stockage disque avec msgpack
    save_to_diskstorage(
        documents=enhanced_documents, 
        collection_name=collection_name, 
        data_dir=data_dir.as_posix(),
        mode=storage_mode
    )
    
    logger.info(f"Source {source_identifier} traitée avec le mode {storage_mode}")
