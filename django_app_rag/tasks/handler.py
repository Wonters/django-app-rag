import dramatiq
from dramatiq.results.backends import RedisBackend
from django.conf import settings
from django.utils.module_loading import import_string
import redis
import json
from typing import Optional, Dict, Any
from django_dramatiq.models import Task
import logging
from dramatiq import Message

logger = logging.getLogger(__name__)


class TaskResultManager:
    """
    Utilitaire pour gérer les résultats des tâches Dramatiq avec dramatiq-result
    """
    
    def __init__(self):
        try:
            cfg = settings.DRAMATIQ_RESULT_BACKEND
            logger.info(f"Configuration DRAMATIQ_RESULT_BACKEND: {cfg}")
            
            backend_cls = import_string(cfg["BACKEND"])  # ex: RedisBackend
            logger.info(f"Classe backend importée: {backend_cls}")
            
            self.backend = backend_cls(**cfg["BACKEND_OPTIONS"])
            logger.info(f"TaskResultManager initialisé avec succès - Backend: {cfg['BACKEND']}")
            
            # Test Redis connection if using Redis backend
            if "redis" in cfg["BACKEND"].lower():
                try:
                    redis_client = cfg["BACKEND_OPTIONS"]["client"]
                    redis_client.ping()
                    logger.info("Connexion Redis testée avec succès")
                except Exception as redis_error:
                    logger.warning(f"Problème de connexion Redis: {redis_error}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du TaskResultManager: {e}")
            logger.error(f"Configuration DRAMATIQ_RESULT_BACKEND: {cfg if 'cfg' in locals() else 'Non définie'}")
            raise

    def create_message(self, message_id: str):
        """
        Crée un message Dramatiq avec l'ID donné
        
        Args:
            message_id: L'ID du message Dramatiq
            
        Returns:
            Un message Dramatiq
        """
        try:
            task = Task.tasks.get(id=message_id)
            logger.info(f"Tâche trouvée: {task.id}, status: {task.status}, queue: {task.queue_name}, actor: {task.actor_name}")
            
            message = Message(
                    queue_name=task.queue_name,
                    actor_name=task.actor_name,
                    args=task.message.args,
                    kwargs=task.message.kwargs,
                    options=task.message.options,
                    message_id=task.id,
                    message_timestamp=0
                )
            logger.info(f"Message créé avec succès pour la tâche {message_id}")
            return message
        except Task.DoesNotExist:
            logger.error(f"Tâche {message_id} non trouvée dans la base de données")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la création du message pour la tâche {message_id}: {e}")
            raise
    
    def get_task_result(self, message_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Récupère le résultat d'une tâche par son message_id
        
        Args:
            message_id: L'ID du message Dramatiq
            timeout: Timeout en secondes pour attendre le résultat
            
        Returns:
            Le résultat de la tâche ou None si pas disponible
        """
        try:
            logger.info(f"Tentative de récupération du résultat pour la tâche {message_id} avec timeout {timeout}s")
            
            # Create a mock message object with the message_id
            message = self.create_message(message_id)
            logger.info(f"Message créé pour la tâche {message_id}: queue={message.queue_name}, actor={message.actor_name}")
            
            result = self.backend.get_result(message, block=True, timeout=timeout * 1000)  # timeout en millisecondes
            logger.info(f"Résultat récupéré pour la tâche {message_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résultat pour {message_id}: {e}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            return None
    
    def wait_for_task_completion(self, message_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Attend la completion d'une tâche et retourne son résultat
        
        Args:
            message_id: L'ID du message Dramatiq
            timeout: Timeout en secondes
            
        Returns:
            Le résultat de la tâche ou None si timeout
        """
        try:
            # Create a mock message object with the message_id
            message = self.create_message(message_id)
            
            result = self.backend.get_result(message, block=True, timeout=timeout * 1000)
            return result
        except Exception as e:
            logger.error(f"Timeout ou erreur pour la tâche {message_id}: {e}")
            return None
    
    def is_task_completed(self, message_id: str) -> bool:
        """
        Vérifie si une tâche est terminée
        
        Args:
            message_id: L'ID du message Dramatiq
            
        Returns:
            True si la tâche est terminée, False sinon
        """
        try:
            # Create a mock message object with the message_id
            message = self.create_message(message_id)
            
            result = self.backend.get_result(message, block=False, timeout=0)
            return result is not None
        except:
            return False
    
    def get_task_status(self, message_id: str) -> Dict[str, Any]:
        """
        Récupère le statut d'une tâche
        
        Args:
            message_id: L'ID du message Dramatiq
            
        Returns:
            Dictionnaire avec le statut de la tâche
        """
        try:
            # Create a mock message object with the message_id
            message = self.create_message(message_id)
            
            result = self.backend.get_result(message, block=False, timeout=0)
            if result is not None:
                return {
                    'status': 'completed',
                    'result': result
                }
            else:
                return {
                    'status': 'pending',
                    'result': None
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'result': None
            }


