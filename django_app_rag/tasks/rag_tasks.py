import dramatiq 
import json
import os
import time
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from django_app_rag.models import Source, Answer, Document
from django_app_rag.logging import get_logger
from django_app_rag.rag.agents.tools import QuestionAnswerTool, DiskStorageRetrieverTool

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """Statuts possibles pour une tâche RAG"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorInfo(BaseModel):
    """Informations détaillées sur une erreur"""
    message: str = Field(..., description="Message d'erreur principal")
    details: Optional[str] = Field(None, description="Détails techniques de l'erreur")
    error_type: Optional[str] = Field(None, description="Type d'erreur (exception class)")
    traceback: Optional[str] = Field(None, description="Traceback de l'erreur")


class RAGTaskResponse(BaseModel):
    """Réponse standardisée pour toutes les tâches RAG"""
    status: TaskStatus = Field(..., description="Statut global de la tâche")
    message: str = Field(..., description="Message descriptif du résultat")
    
    # Informations sur le traitement
    processed: int = Field(0, description="Nombre d'éléments traités avec succès")
    total: int = Field(0, description="Nombre total d'éléments à traiter")
    failed: int = Field(0, description="Nombre d'éléments en échec")
    
    # Informations d'erreur
    error: Optional[ErrorInfo] = Field(None, description="Erreur globale si la tâche a échoué")
    
    # Métadonnées
    source_id: Optional[int] = Field(None, description="ID de la source traitée")
    config_path: Optional[str] = Field(None, description="Chemin de configuration utilisé")
    execution_time: Optional[float] = Field(None, description="Temps d'exécution total en secondes")
    
    # Informations additionnelles
    warnings: List[str] = Field(default_factory=list, description="Avertissements non critiques")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")

    @validator('failed', pre=True, always=True)
    def set_failed_count(cls, v, values):
        """Calcule automatiquement le nombre d'échecs si non fourni"""
        if v is not None:
            return v
        if 'processed' in values and 'total' in values:
            return values['total'] - values['processed']
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la réponse en dictionnaire pour la sérialisation JSON"""
        return self.dict()

    def is_success(self) -> bool:
        """Vérifie si la tâche s'est terminée avec succès"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.PENDING]

    def has_errors(self) -> bool:
        """Vérifie s'il y a des erreurs dans la réponse"""
        return self.status == TaskStatus.FAILED or self.error is not None or self.failed > 0


def create_error_response(source_id: int, config_path: str, error: Exception, message: str = None) -> Dict[str, Any]:
    """Crée une réponse d'erreur standardisée sérialisable"""
    if message is None:
        message = "Erreur lors du processus QA"
    
    error_info = ErrorInfo(
        message=str(error),
        details=str(error),
        error_type=type(error).__name__,
        traceback=traceback.format_exc()
    )
    
    response = RAGTaskResponse(
        status=TaskStatus.FAILED,
        message=message,
        error=error_info,
        source_id=source_id,
        config_path=config_path,
        execution_time=0.0,
        warnings=[],
        metadata={}
    )
    
    return response.to_dict()


def create_success_response(source_id: int, config_path: str, processed: int, total: int, message: str = None, execution_time: float = 0.0) -> Dict[str, Any]:
    """Crée une réponse de succès standardisée sérialisable"""
    if message is None:
        message = f"Processus QA terminé avec succès. {processed} questions traitées sur {total}."
    
    response = RAGTaskResponse(
        status=TaskStatus.COMPLETED,
        message=message,
        processed=processed,
        total=total,
        source_id=source_id,
        config_path=config_path,
        execution_time=execution_time,
        warnings=[],
        metadata={}
    )
    
    return response.to_dict()


@dramatiq.actor(
    queue_name="rag_tasks",
    actor_name="rag_app.tasks",
    time_limit=1000 * 60 * 10,
    max_retries=1,
    store_results=True,
)
def launch_qa_process(source_id: int, config_path: str):
    """
    Lance un processus Question/Réponse en utilisant Dramatiq.
    
    Args:
        source_id: ID de la source à analyser
        config: Configuration pour le processus RAG
    """
    start_time = time.time()
    try:
        logger.info(f"Démarrage du processus QA pour la source {source_id}")
        
                # Valider le chemin de configuration
        if not config_path:
            logger.error("Chemin de configuration manquant")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=ValueError("Chemin de configuration manquant"),
                message="Configuration invalide"
            )
        
        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            logger.error(f"Fichier de configuration introuvable: {config_path}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=FileNotFoundError(f"Fichier de configuration introuvable: {config_path}"),
                message="Configuration introuvable"
            )
        
        logger.info(f"Configuration validée: {config_path}")
        
        # Récupérer la source et ses questions
        try:
            source = Source.objects.prefetch_related('questions__answer').get(id=source_id)
            logger.info(f"Source récupérée: {source.title} (ID: {source_id})")
        except Source.DoesNotExist:
            logger.error(f"Source {source_id} non trouvée")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=ValueError(f"Source {source_id} non trouvée"),
                message="Source introuvable"
            )
        except Exception as source_error:
            logger.error(f"Erreur lors de la récupération de la source {source_id}: {source_error}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=source_error,
                message="Erreur lors de la récupération de la source"
            )
        
        try:
            questions = source.questions.all()
            logger.info(f"Questions récupérées: {questions.count()} questions trouvées")
        except Exception as questions_error:
            logger.error(f"Erreur lors de la récupération des questions pour la source {source_id}: {questions_error}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=questions_error,
                message="Erreur lors de la récupération des questions"
            )
        
        if not questions.exists():
            logger.warning(f"Aucune question trouvée pour la source {source_id}")
            return create_success_response(
                source_id=source_id,
                config_path=config_path,
                processed=0,
                total=0,
                message="Aucune question à traiter"
            )
        
        logger.info(f"Traitement de {questions.count()} questions pour la source {source_id}")
        
        # Initialiser les outils RAG
        try:
            logger.info(f"Initialisation de l'agent QA")
            agent_qa = QuestionAnswerTool()
            logger.info(f"Agent QA initialisé avec succès")
        except Exception as qa_error:
            logger.error(f"Erreur lors de l'initialisation de l'agent QA: {qa_error}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=qa_error,
                message="Erreur lors de l'initialisation des outils RAG"
            )
        
        try:
            logger.info(f"Initialisation de l'agent retriever avec config: {config_path}")
            agent_retriever = DiskStorageRetrieverTool(
                config_path=config_path_obj
            )
            logger.info(f"Agent retriever initialisé avec succès")
        except Exception as retriever_error:
            logger.error(f"Erreur lors de l'initialisation de l'agent retriever: {retriever_error}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=retriever_error,
                message="Erreur lors de l'initialisation des outils RAG"
            )
        
        processed_count = 0
        
        # Traiter chaque question
        for i, question in enumerate(questions):
            try:
                logger.info(f"Traitement de la question {i+1}/{questions.count()}: {question.title}")
                
                # Supprimer l'ancienne réponse
                try:
                    if hasattr(question, 'answer') and question.answer:
                        old_answer = question.answer
                        logger.info(f"Suppression de l'ancienne réponse pour la question {question.title}")
                        try:
                            old_answer.documents.clear()
                            old_answer.delete()
                            logger.debug(f"Ancienne réponse supprimée: {old_answer.id}")
                        except Exception as delete_error:
                            logger.error(f"Erreur lors de la suppression de l'ancienne réponse {old_answer.id}: {delete_error}")
                            # Continue with deletion
                except Exception as cleanup_error:
                    logger.error(f"Erreur lors du nettoyage de l'ancienne réponse pour la question {question.title}: {cleanup_error}")
                    # Continue with processing
                
                # Récupérer les documents pertinents
                try:
                    logger.info(f"Récupération des documents pour la question: {question.field}")
                    documents = agent_retriever.forward(question.field)
                    logger.info(f"Documents récupérés: {len(documents) if documents else 0} caractères")
                    
                    if not documents:
                        logger.warning(f"Aucun document récupéré pour la question {question.title}")
                        # Continue with empty documents
                except Exception as retrieval_error:
                    logger.error(f"Erreur lors de la récupération des documents pour la question {question.title}: {retrieval_error}")
                    documents = ""
                    # Continue with empty documents
                
                # Générer la réponse
                try:
                    logger.info(f"Génération de la réponse pour la question: {question.title}")
                    answer_data = agent_qa.forward(question.field, documents)
                    logger.info(f"Réponse brute générée: {len(answer_data) if answer_data else 0} caractères")
                    
                    if not answer_data:
                        logger.error(f"Aucune réponse générée pour la question {question.title}")
                        continue
                except Exception as answer_error:
                    logger.error(f"Erreur lors de la génération de la réponse pour la question {question.title}: {answer_error}")
                    continue
                
                # Parse the answer data
                try:
                    answer_json = json.loads(answer_data)
                    logger.info(f"Réponse parsée avec succès pour la question {question.title}")
                except json.JSONDecodeError as json_error:
                    logger.error(f"Erreur de parsing JSON pour la question {question.title}: {json_error}")
                    logger.error(f"Données brutes: {answer_data}")
                    # Skip this question and continue
                    continue
                
                logger.info(f"Réponse générée pour la question {question.title}: {answer_json.get('answer', '')[:100]}...")
                
                # Validate answer structure
                if not isinstance(answer_json, dict):
                    logger.error(f"Réponse invalide pour la question {question.title}: {type(answer_json)}")
                    continue
                
                if "answer" not in answer_json:
                    logger.error(f"Clé 'answer' manquante dans la réponse pour la question {question.title}")
                    continue
                
                # Créer la réponse
                try:
                    answer_instance = Answer.objects.create(
                        title=f"Réponse automatique {i+1}",
                        field=answer_json.get("answer", "Aucune réponse générée"),
                        question=question
                    )
                    logger.info(f"Réponse créée avec succès: {answer_instance.id}")
                except Exception as create_error:
                    logger.error(f"Erreur lors de la création de la réponse pour la question {question.title}: {create_error}")
                    continue
                
                # Créer et associer les documents sources
                if "sources" in answer_json and isinstance(answer_json["sources"], list):
                    source_documents = []
                    for doc in answer_json["sources"]:
                        if isinstance(doc, dict):
                            try:
                                doc_instance = Document.objects.create(
                                    title=doc.get("title", "Document sans titre"),
                                    uid=doc.get("id", f"doc_{i}_{len(source_documents)}"),
                                    similarity_score=doc.get("similarity_score", 0.0),
                                    url=doc.get("url", ""),
                                )
                                source_documents.append(doc_instance)
                                logger.debug(f"Document créé avec succès: {doc_instance.id}")
                            except Exception as doc_create_error:
                                logger.error(f"Erreur lors de la création du document pour la question {question.title}: {doc_create_error}")
                                continue
                        else:
                            logger.warning(f"Document invalide dans les sources: {doc}")
                    
                    if source_documents:
                        try:
                            answer_instance.documents.set(source_documents)
                            answer_instance.save()
                            logger.info(f"Documents sources associés: {len(source_documents)}")
                        except Exception as assoc_error:
                            logger.error(f"Erreur lors de l'association des documents pour la question {question.title}: {assoc_error}")
                            # Continue without documents
                    else:
                        logger.warning(f"Aucun document source valide pour la question {question.title}")
                else:
                    logger.info(f"Aucune source document pour la question {question.title}")
                
                processed_count += 1
                logger.info(f"Question {question.title} traitée avec succès")
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la question {question.title}: {e}")
                logger.error(f"Type d'erreur: {type(e).__name__}")
                logger.error(f"Traceback complet: ", exc_info=True)
                # Continuer avec la question suivante
                continue
        
        execution_time = time.time() - start_time
        logger.info(f"Processus QA terminé pour la source {source_id}. {processed_count} questions traitées.")
        
        return create_success_response(
            source_id=source_id,
            config_path=config_path,
            processed=processed_count,
            total=questions.count(),
            message=f"Processus QA terminé avec succès. {processed_count} questions traitées.",
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Erreur lors du processus QA pour la source {source_id}: {e}")
        logger.error(f"Type d'erreur: {type(e).__name__}")
        logger.error(f"Traceback complet: ", exc_info=True)
        
        return create_error_response(
            source_id=source_id,
            config_path=config_path,
            error=e,
            message="Erreur lors du processus QA"
        )
