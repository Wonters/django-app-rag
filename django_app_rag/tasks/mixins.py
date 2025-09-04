from rest_framework.response import Response
from django_dramatiq.models import Task
from rest_framework import status
from .handler import TaskResultManager
from ..logging import get_logger_loguru

logger = get_logger_loguru(__name__)

class TaskViewMixin:
    """
    Mixin for generalizing task management functionality.
    
    Provides common methods for:
    - _format_task_response: Standardized task response formatting
    - launch_task: Launch a task with given parameters
    - get_task_status: Get the status of a task
    """
    queue_name = "default"
    
    def _format_task_response(
        self, status, message, task_id, error=None, result=None, http_status=200
    ):
        """
        Format a standardized task response.

        Args:
            status (str): Task status ('pending', 'running', 'completed', 'failed', 'unknown')
            message (str): Human-readable message
            task_id (str): Task identifier
            error (str, optional): Error message if applicable
            result (dict, optional): Task result data
            http_status (int): HTTP status code

        Returns:
            Response: Formatted JSON response
        """
        try:
            response_data = {"status": status, "message": message, "task_id": task_id}

            if error is not None:
                response_data["error"] = error

            if result is not None:
                response_data["result"] = result

            logger.debug(f"Réponse formatée: {response_data}")
            return Response(response_data, status=http_status)
        except Exception as e:
            logger.error(f"Erreur lors du formatage de la réponse: {e}")
            # Fallback response
            fallback_data = {
                "status": "failed",
                "message": "Erreur lors du formatage de la réponse",
                "task_id": task_id,
                "error": str(e)
            }
            return Response(fallback_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def launch_task(self, task_func, task_kwargs, success_message, error_message):
        """
        Launch a task with the given parameters.

        Args:
            task_func: The task function to execute
            task_kwargs (dict): Keyword arguments for the task
            success_message (str): Success message to return
            error_message (str): Error message to return

        Returns:
            Response: Formatted task response
        """
        try:
            logger.info(f"Lancement de la tâche {getattr(task_func, 'actor_name', 'unknown')} avec kwargs: {task_kwargs}")
            task = task_func.send_with_options(kwargs=task_kwargs)
            logger.info(f"Tâche lancée avec succès, message_id: {task.message_id}")
            return self._format_task_response(
                status="pending",
                message=success_message,
                task_id=task.message_id,
            )
        except Exception as e:
            logger.error(f"Erreur lors du lancement de la tâche {getattr(task_func, 'actor_name', 'unknown')}: {e}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            logger.error(f"Traceback complet: ", exc_info=True)
            return self._format_task_response(
                status="failed",
                message=error_message,
                task_id=None,
                error=str(e),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_task_status(self, task_id, task_name="Tâche"):
        """
        Get the status of a task.

        Args:
            task_id (str): Task identifier
            task_name (str): Human-readable task name for messages

        Returns:
            Response: Formatted task status response
        """
        try:
            task = Task.tasks.get(id=task_id)
            
            # Initialize task manager with error handling
            try:
                task_manager = TaskResultManager()
                logger.info(f"⛏ Task status: {task.status} | Task ID: {task_id} | Queue: {task.queue_name}")
                
                # Log additional task information for debugging
                logger.info(f"Task details - Actor: {task.actor_name}, Args: {task.message.args}, Kwargs: {task.message.kwargs}")
            except Exception as manager_error:
                logger.error(f"Erreur lors de l'initialisation du TaskResultManager: {manager_error}")
                return self._format_task_response(
                    status="failed",
                    message=f"{task_name} - Erreur de configuration",
                    task_id=task_id,
                    error=f"Erreur de configuration: {str(manager_error)}",
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            
            # Check if task status is None or invalid
            if task.status is None:
                logger.error(f"Statut de tâche None pour la tâche {task_id}")
                return self._format_task_response(
                    status="failed",
                    message=f"{task_name} - Statut invalide",
                    task_id=task_id,
                    error="Statut de tâche None",
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            
            if task.status == Task.STATUS_ENQUEUED:
                return self._format_task_response(
                    status="pending",
                    message=f"{task_name} en attente de traitement",
                    task_id=task_id,
                )

            elif task.status == Task.STATUS_RUNNING:
                return self._format_task_response(
                    status="running",
                    message=f"{task_name} en cours d'exécution",
                    task_id=task_id,
                )

            elif task.status == Task.STATUS_DONE:
                # Task completed, get the result
                try:
                    result = task_manager.get_task_result(task_id)
                    logger.info(f"Task result: {result}")
                except Exception as result_error:
                    logger.error(f"Erreur lors de la récupération du résultat pour la tâche {task_id}: {result_error}")
                    return self._format_task_response(
                        status="failed",
                        message=f"{task_name} terminée mais erreur lors de la récupération du résultat",
                        task_id=task_id,
                        error=f"Erreur de récupération: {str(result_error)}",
                        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                # Check if result exists and contains error information
                if result is not None:
                    logger.info(f"Type de résultat: {type(result)}, Contenu: {result}")
                    
                    # Check if the result contains error information
                    if isinstance(result, dict):
                        if "error" in result and result["error"]:
                            # Task completed but with errors
                            error_message = (
                                result.get("error")
                                or result.get("exception")
                                or result.get("failed")
                                or "Erreur inconnue"
                            )
                            logger.error(f"Tâche {task_id} terminée avec des erreurs: {error_message}")
                            
                            # Force le status de la tâche à failed en base
                            try:
                                task.status = Task.STATUS_FAILED
                                task.save(update_fields=["status"])
                                logger.info(f"Statut de la tâche {task_id} mis à jour vers FAILED")
                            except Exception as save_error:
                                logger.error(f"Erreur lors de la sauvegarde du statut FAILED: {save_error}")
                            
                            return self._format_task_response(
                                status="failed",
                                message=f"{task_name} terminée avec des erreurs",
                                task_id=task_id,
                                error=error_message,
                                result=result,
                                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )
                        else:
                            # Task completed successfully with results
                            logger.info(f"Tâche {task_id} terminée avec succès")
                            return self._format_task_response(
                                status="completed",
                                message=f"{task_name} terminée avec succès",
                                task_id=task_id,
                                result=result,
                            )
                    elif isinstance(result, Exception):
                        # Result is an exception object
                        logger.error(f"Tâche {task_id} terminée avec une exception: {result}")
                        return self._format_task_response(
                            status="failed",
                            message=f"{task_name} terminée avec une exception",
                            task_id=task_id,
                            error=str(result),
                            result={"exception": str(result)},
                            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                    else:
                        # Result exists but is not a dict or exception - assume success
                        logger.info(f"Tâche {task_id} terminée avec un résultat de type {type(result)}")
                        return self._format_task_response(
                            status="completed",
                            message=f"{task_name} terminée avec succès",
                            task_id=task_id,
                            result=result,
                        )
                else:
                    # No result available - this could indicate a problem
                    logger.warning(f"Tâche {task_id} terminée mais aucun résultat disponible")
                    return self._format_task_response(
                        status="completed",
                        message=f"{task_name} terminée mais aucun résultat disponible",
                        task_id=task_id,
                        result={"warning": "Aucun résultat retourné par la tâche"},
                    )

            elif task.status == Task.STATUS_FAILED:
                # Task failed, get error details
                logger.error(f"Tâche {task_id} marquée comme échouée dans la base de données")
                error_message = "💥 Unknown error"
                result_data = None

                # Try to get more detailed error information
                try:
                    result = task_manager.get_task_result(task_id)
                    if result and isinstance(result, dict) and "error" in result:
                        error_message = result["error"]
                        result_data = result
                        logger.info(f"Résultat d'erreur récupéré pour la tâche {task_id}: {error_message}")
                    else:
                        logger.warning(f"Aucun résultat d'erreur détaillé trouvé pour la tâche {task_id}")
                except Exception as result_error:
                    logger.warning(f"Impossible de récupérer le résultat détaillé pour la tâche {task_id}: {result_error}")
                    pass

                return self._format_task_response(
                    status="failed",
                    message=f"{task_name} échouée",
                    task_id=task_id,
                    error=error_message,
                    result=result_data,
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            else:
                # Unknown status
                logger.warning(f"Statut de tâche inattendu: {task.status} (type: {type(task.status)}) pour la tâche {task_id}")
                
                # Try to get more information about the task
                try:
                    result = task_manager.get_task_result(task_id)
                    if result:
                        logger.info(f"Résultat disponible pour la tâche {task_id} avec statut inconnu: {result}")
                except Exception as result_error:
                    logger.warning(f"Impossible de récupérer le résultat pour la tâche {task_id} avec statut inconnu: {result_error}")
                
                return self._format_task_response(
                    status="unknown",
                    message=f"Statut inconnu: {task.status}",
                    task_id=task_id,
                )

        except Task.DoesNotExist:
            logger.error(f"Tâche {task_id} non trouvée dans la base de données")
            return self._format_task_response(
                status="failed",
                message="Tâche non trouvée",
                task_id=task_id,
                error="Tâche non trouvée",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut de la tâche {task_id}: {e}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            logger.error(f"Traceback complet: ", exc_info=True)
            return self._format_task_response(
                status="failed",
                message="Erreur lors de la récupération du statut",
                task_id=task_id,
                error=str(e),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
