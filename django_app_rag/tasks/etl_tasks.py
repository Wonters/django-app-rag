import dramatiq
from pathlib import Path
from django.conf import settings
from django_app_rag.logging import get_logger
import subprocess as sp
import sys
from django_app_rag.models import Collection, Source
from django.utils import timezone
logger = get_logger(__name__)

SCRIPT_PATH = Path(__file__).parent.parent / "rag" / "run.py"

def run_rag_process(script_path: Path, name: str, config_path: Path):
    """
    Lance un processus RAG en utilisant Dramatiq.

    Args:
        script_path: Chemin du script RAG
        name: Nom du processus RAG
        config_path: Chemin de la configuration RAG
    """
    with sp.Popen(
        [sys.executable, str(script_path), name, "--config", config_path],
        stderr=sp.PIPE,
        stdout=sp.PIPE,
        text=True,
        bufsize=1,
    ) as process:
        for line in process.stdout:
            logger.info(line.rstrip())
        for line in process.stderr:
            logger.error(line.rstrip())
        process.wait()

def launch_rag_indexing_process(script_path: Path, retrieve_config_path: Path, etl_config_path: Path, index_config_path: Path):
    """
    Lance un processus ETL en utilisant Dramatiq.
    """
    run_rag_process(script_path, "retrieve", retrieve_config_path)
    run_rag_process(script_path, "etl", etl_config_path)
    run_rag_process(script_path, "index", index_config_path)

    logger.info(f"Processus ETL terminé avec succès")


@dramatiq.actor(
    queue_name="etl_tasks",
    actor_name="rag_app.etl_collection",
    time_limit=1000 * 60 * 60,
    max_retries=1,
    store_results=True,
)
def indexing_collection_task(collection_id: int, storage_mode: str = "overwrite"):
    """
    Tâche Dramatiq pour initialiser une collection en récupérant les données des sources,
    effectuant des analyses de qualité et formatant les données.
    
    Args:
        collection_id: ID de la collection à initialiser
        storage_mode: Mode de stockage - "overwrite" (écrase tout) ou "append" (ajoute)
    """
    try:
        logger.info(f"Début de l'initialisation de la collection {collection_id} en mode {storage_mode}")
        collection = Collection.objects.get(id=collection_id)
        launch_rag_indexing_process(SCRIPT_PATH,  collection.rag_retrieve_config(), collection.rag_etl_config(), collection.rag_index_config())
        collection.sources.update(is_indexed_at=timezone.now())
        return {
                "status": "success",
                "message": f"Collection {collection_id} initialisée en mode {storage_mode} avec succès",
                "collection_id": collection_id,
                "storage_mode": storage_mode,
            }

    except Exception as e:
        logger.error(
            f"Erreur lors de l'initialisation de la collection {collection_id}: {e}"
        )
        return {"status": "error", "error": str(e), "collection_id": collection_id}


@dramatiq.actor(
    queue_name="etl_tasks",
    actor_name="rag_app.etl_source",
    time_limit=1000 * 60 * 20,
    max_retries=1,
    store_results=True,
)
def indexing_source_task(source_id: int, storage_mode: str = "append"):
    """
    Tâche Dramatiq pour traiter une source avec mode configurable.
    
    Args:
        source_id: ID de la source à traiter
        storage_mode: Mode de stockage - "overwrite" (écrase tout) ou "append" (ajoute)
    """
    try:
        logger.info(f"Début du traitement de la source {source_id} en mode {storage_mode}")
        source = Source.objects.get(id=source_id)
        collection = source.collection
        
        # Déterminer le type de source et l'identifiant
        if source.type == Source.FILE and source.file:
            source_type = "file"
            source_identifier = source.file.path
        elif source.type == Source.URL and source.link:
            source_type = "url"
            source_identifier = source.link
        elif source.type == Source.NOTION and source.notion_db_ids:
            source_type = "notion"
            source_identifier = source.notion_db_ids.split(",")[0].strip()
        else:
            raise ValueError(f"Type de source non supporté: {source.type}")
        
        # Lancer le pipeline ETL pour source unique via run.py
        run_rag_process(SCRIPT_PATH, "etl-source", collection.rag_etl_source_config(source_type, source_identifier, storage_mode))
        
        # Mettre à jour le timestamp d'indexation
        source.is_indexed_at = timezone.now()
        source.save()
        
        return {
            "status": "success",
            "message": f"Source {source_id} traitée en mode {storage_mode} avec succès",
            "source_id": source_id,
            "storage_mode": storage_mode,
        }

    except Exception as e:
        logger.error(
            f"Erreur lors du traitement de la source {source_id}: {e}"
        )
        return {"status": "error", "error": str(e), "source_id": source_id}