import dramatiq
from pathlib import Path
from django.conf import settings
from django_app_rag.logging import get_logger
from django_app_rag.logging import get_logger_loguru
from django_app_rag.logging import get_subprocess_logger
import subprocess as sp
import sys
from django_app_rag.models import Collection, Source
from django.utils import timezone
import traceback


logger = get_logger_loguru(__name__)

SCRIPT_PATH = Path(__file__).parent.parent / "rag" / "run.py"





def run_rag_process(script_path: Path, name: str, config_path: Path):
    """
    Lance un processus RAG en utilisant Dramatiq.

    Args:
        script_path: Chemin du script RAG
        name: Nom du processus RAG
        config_path: Chemin de la configuration RAG
        
    Returns:
        bool: True si le processus s'est terminé avec succès, False sinon
    """
    try:
        logger.info(f"Démarrage du processus RAG '{name}'")
        logger.info(f"Script: {script_path}")
        logger.info(f"Config: {config_path}")
        
        # Créer un logger spécifique pour ce sous-processus
        subprocess_logger, subprocess_log_file = get_subprocess_logger(name)
        logger.info(f"Fichier de log du sous-processus '{name}': {subprocess_log_file}")
        
        with sp.Popen(
            [sys.executable, str(script_path), name, "--config", config_path],
            stderr=sp.PIPE,
            stdout=sp.PIPE,
            text=True,
            bufsize=1,
        ) as process:
            logger.info(f"Processus '{name}' lancé (PID: {process.pid})")
            
            # Logs du sous-processus avec son propre logger et fichier (nettoyage ANSI automatique)
            for line in process.stdout:
                if line.strip():  # Ignorer les lignes vides
                    subprocess_logger.info(line.rstrip())
            
            for line in process.stderr:
                if line.strip():  # Ignorer les lignes vides
                    subprocess_logger.error(line.rstrip())
            
            # Attendre la fin du processus et récupérer le code de retour
            return_code = process.wait()
            
            if return_code == 0:
                logger.info(f"Processus RAG '{name}' terminé avec succès")
                return True
            else:
                logger.error(f"Processus RAG '{name}' a échoué avec le code de retour {return_code}")
                return False
                
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du processus RAG '{name}': {e}")
        return False


def launch_rag_indexing_process(
    script_path: Path,
    config_path: Path,
):
    """
    Lance un processus ETL en utilisant Dramatiq.
    
    Returns:
        dict: Dictionnaire contenant l'état du processus avec les clés:
            - status: "success" ou "fail"
            - message: Message descriptif du résultat
            - details: Détails des étapes qui ont réussi ou échoué
    """
    results = {}
    
    logger.info("=" * 60)
    logger.info("Début du processus ETL complet")
    logger.info("=" * 60)
    
    # Étape 1: Retrieve
    logger.info("=== ÉTAPE 1/3: RETRIEVE ===")
    retrieve_success = run_rag_process(script_path, "retrieve", config_path)
    results["retrieve"] = "success" if retrieve_success else "fail"
    
    if not retrieve_success:
        logger.error("Étape Retrieve a échoué - Arrêt du processus ETL")
        return {
            "status": "fail",
            "message": "Le processus ETL a échoué lors de l'étape Retrieve",
            "details": results
        }
    
    # Étape 2: ETL
    logger.info("=== ÉTAPE 2/3: ETL ===")
    etl_success = run_rag_process(script_path, "etl", config_path)
    results["etl"] = "success" if etl_success else "fail"
    
    if not etl_success:
        logger.error("Étape ETL a échoué - Arrêt du processus ETL")
        return {
            "status": "fail",
            "message": "Le processus ETL a échoué lors de l'étape ETL",
            "details": results
        }
    
    # Étape 3: Index
    logger.info("=== ÉTAPE 3/3: INDEX ===")
    index_success = run_rag_process(script_path, "index", config_path)
    results["index"] = "success" if index_success else "fail"
    
    if not index_success:
        logger.error("Étape Index a échoué - Arrêt du processus ETL")
        return {
            "status": "fail",
            "message": "Le processus ETL a échoué lors de l'étape Index",
            "details": results
        }
    
    # Toutes les étapes ont réussi
    logger.info("=" * 60)
    logger.info("Processus ETL terminé avec succès - Toutes les étapes complétées")
    logger.info("=" * 60)
    return {
        "status": "success",
        "message": "Le processus ETL s'est terminé avec succès",
        "details": results
    }


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
        logger.info(
            f"Début de l'initialisation de la collection {collection_id} en mode {storage_mode}"
        )
        collection = Collection.objects.get(id=collection_id)
        result = launch_rag_indexing_process(
            SCRIPT_PATH,
            collection.get_rag_config(),
        )
        
        # Vérifier le statut du processus ETL
        if result["status"] == "fail":
            logger.error(f"Le processus ETL a échoué: {result['message']}")
            return {
                "status": "error",
                "error": result["message"],
                "collection_id": collection_id,
                "details": result
            }
        
        collection.sources.update(is_indexed_at=timezone.now())
        for source in collection.sources.all():
            source.compute_quality_score()
        return {
            "status": "success",
            "message": f"Collection {collection_id} initialisée en mode {storage_mode} avec succès",
            "collection_id": collection_id,
            "storage_mode": storage_mode,
            "details": result,
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
        logger.info(
            f"Début du traitement de la source {source_id} en mode {storage_mode}"
        )
        source = Source.objects.get(id=source_id)
        collection = source.collection
        result = launch_rag_indexing_process(
            SCRIPT_PATH,
            collection.get_rag_config(source=source),
        )

        # Vérifier le statut du processus ETL
        if result["status"] == "fail":
            logger.error(f"Le processus ETL a échoué: {result['message']}")
            return {
                "status": "error",
                "error": result["message"],
                "source_id": source_id,
                "details": result
            }

        # Mettre à jour le timestamp d'indexation
        source.is_indexed_at = timezone.now()
        source.save()
        source.compute_quality_score()
        

        return {
            "status": "success",
            "message": f"Source {source_id} traitée en mode {storage_mode} avec succès",
            "source_id": source_id,
            "storage_mode": storage_mode,
            "details": result,
        }

    except Exception as e:
        logger.error(f"Erreur lors du traitement de la source {source_id}: {traceback.format_exc()}")
        return {"status": "error", "error": str(e), "source_id": source_id}
