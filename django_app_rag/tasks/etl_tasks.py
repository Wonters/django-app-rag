import dramatiq
from pathlib import Path
from django.conf import settings
from django_app_rag.logging import get_logger
import subprocess as sp
import sys
from django_app_rag.models import Collection

logger = get_logger(__name__)


def launch_rag_process(script_path: Path, name: str, config_path: Path):
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


@dramatiq.actor(
    queue_name="etl_tasks",
    actor_name="rag_app.etl",
    time_limit=1000 * 60 * 10,
    max_retries=1,
    store_results=True,
)
def initialize_collection_task(collection_id: int):
    """
    Tâche Dramatiq pour initialiser une collection en récupérant les données des sources,
    effectuant des analyses de qualité et formatant les données.

    Args:
        collection_id: ID de la collection à initialiser
        data_dir: Répertoire de données (par défaut "data")
    """
    try:
        logger.info(f"Début de l'initialisation de la collection {collection_id}")
        collection = Collection.objects.get(id=collection_id)
        script_path = Path(__file__).parent.parent / "rag" / "run.py"
        launch_rag_process(script_path, "retrieve", collection.rag_retrieve_config())
        launch_rag_process(script_path, "etl", collection.rag_etl_config())
        launch_rag_process(script_path, "index", collection.rag_index_config())

        logger.info(
            f"Initialisation de la collection {collection_id} terminée avec succès"
        )

        return {
            "status": "success",
            "message": f"Collection {collection_id} initialisée avec succès",
            "collection_id": collection_id,
        }

    except Exception as e:
        logger.error(
            f"Erreur lors de l'initialisation de la collection {collection_id}: {e}"
        )
        return {"status": "error", "error": str(e), "collection_id": collection_id}
