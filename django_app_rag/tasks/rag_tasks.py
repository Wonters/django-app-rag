import dramatiq 
import json
import time
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from django_app_rag.models import Source, Answer, Document
from django_app_rag.logging import get_logger_loguru
from django_app_rag.rag.agents.tools import QuestionAnswerTool, DiskStorageRetrieverTool

logger = get_logger_loguru(__name__, "qa.log")


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


def _validate_config_path(config_path: str) -> Path:
    """
    Validate and return config path as Path object.

    Raises:
        ValueError: If config_path is missing or file doesn't exist
    """
    if not config_path:
        raise ValueError("Chemin de configuration manquant")

    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable: {config_path}")

    logger.info(f"Configuration validée: {config_path}")
    return config_path_obj


def _get_source_with_questions(source_id: int):
    """
    Retrieve source and its questions.

    Returns:
        Tuple of (source, questions)

    Raises:
        Source.DoesNotExist: If source not found
    """
    source = Source.objects.prefetch_related('questions__answer').get(id=source_id)
    logger.info(f"Source récupérée: {source.title} (ID: {source_id})")

    questions = source.questions.all()
    logger.info(f"Questions récupérées: {questions.count()} questions trouvées")

    return source, questions


def _initialize_rag_agents(config_path: Path):
    """
    Initialize RAG agents (QA and Retriever).

    Returns:
        Tuple of (agent_qa, agent_retriever)

    Raises:
        Exception: If initialization fails
    """
    logger.info("Initialisation de l'agent QA")
    agent_qa = QuestionAnswerTool()
    logger.info("Agent QA initialisé avec succès")

    logger.info(f"Initialisation de l'agent retriever avec config: {config_path}")
    agent_retriever = DiskStorageRetrieverTool(config_path=config_path)
    logger.info("Agent retriever initialisé avec succès")

    return agent_qa, agent_retriever


def _delete_old_answer(question):
    """Delete old answer for a question if exists."""
    try:
        if hasattr(question, 'answer') and question.answer:
            old_answer = question.answer
            logger.info(f"Suppression de l'ancienne réponse pour la question {question.title}")
            old_answer.documents.clear()
            old_answer.delete()
            logger.debug(f"Ancienne réponse supprimée: {old_answer.id}")
    except Exception as cleanup_error:
        logger.error(f"Erreur lors du nettoyage de l'ancienne réponse pour {question.title}: {cleanup_error}")


def _retrieve_documents(agent_retriever, question_field: str) -> str:
    """
    Retrieve documents for a question.

    Returns:
        JSON string of retrieved documents (empty string if error)
    """
    try:
        logger.info(f"Récupération des documents pour: {question_field}")
        documents = agent_retriever.forward(question_field)

        # Parse to log document count
        try:
            docs_data = json.loads(documents) if documents else {}
            doc_count = docs_data.get('total_count', 0) if isinstance(docs_data, dict) else 0
            logger.info(f"Documents récupérés: {doc_count}")
        except json.JSONDecodeError:
            logger.info(f"Documents récupérés: JSON invalide (longueur: {len(documents) if documents else 0})")

        return documents or ""
    except Exception as retrieval_error:
        logger.error(f"Erreur lors de la récupération des documents: {retrieval_error}")
        return ""


def _generate_answer(agent_qa, question_field: str, documents: str) -> Optional[dict]:
    """
    Generate answer for a question using retrieved documents.

    Returns:
        Parsed answer JSON dict, or None if error
    """
    try:
        logger.info(f"Génération de la réponse pour: {question_field}")
        answer_data = agent_qa.forward(question_field, documents)
        logger.info(f"Réponse brute générée: {len(answer_data) if answer_data else 0} caractères")

        if not answer_data:
            logger.error("Aucune réponse générée")
            return None

        # Parse JSON
        answer_json = json.loads(answer_data)
        logger.info(f"Réponse parsée avec succès: {json.dumps(answer_json, ensure_ascii=False)[:200]}...")

        # Handle list response
        if isinstance(answer_json, list) and len(answer_json) > 0:
            answer_json = answer_json[0]
            logger.info("Réponse extraite de la liste")

        # Validate structure
        if not isinstance(answer_json, dict):
            logger.error(f"Réponse invalide: type {type(answer_json)}")
            return None

        if "answer" not in answer_json:
            logger.error("Clé 'answer' manquante dans la réponse")
            return None

        return answer_json

    except json.JSONDecodeError as json_error:
        logger.error(f"Erreur de parsing JSON: {json_error}")
        return None
    except Exception as answer_error:
        logger.error(f"Erreur lors de la génération de la réponse: {answer_error}")
        return None


def _create_answer_instance(question, answer_json: dict, index: int) -> Optional[Answer]:
    """
    Create Answer instance from answer JSON.

    Returns:
        Created Answer instance, or None if error
    """
    try:
        answer_instance = Answer.objects.create(
            title=f"Réponse automatique {index+1}",
            field=answer_json.get("answer", "Aucune réponse générée"),
            question=question
        )
        logger.info(f"Réponse créée avec succès: {answer_instance.id}")
        return answer_instance
    except Exception as create_error:
        logger.error(f"Erreur lors de la création de la réponse pour {question.title}: {create_error}")
        return None


def _create_source_documents(answer_json: dict, answer_instance: Answer, index: int):
    """Create and associate source documents to answer."""
    if "sources" not in answer_json or not isinstance(answer_json["sources"], list):
        logger.info("Aucune source document")
        return

    source_documents = []
    for doc in answer_json["sources"]:
        if not isinstance(doc, dict):
            logger.warning(f"Document invalide dans les sources: {doc}")
            continue

        try:
            doc_instance = Document.objects.create(
                title=doc.get("title", "Document sans titre"),
                uid=doc.get("id", f"doc_{index}_{len(source_documents)}"),
                similarity_score=doc.get("similarity_score", 0.0),
                url=doc.get("url", ""),
            )
            source_documents.append(doc_instance)
            logger.debug(f"Document créé: {doc_instance.id}")
        except Exception as doc_create_error:
            logger.error(f"Erreur lors de la création du document: {doc_create_error}")

    if source_documents:
        try:
            answer_instance.documents.set(source_documents)
            answer_instance.save()
            logger.info(f"Documents sources associés: {len(source_documents)}")
        except Exception as assoc_error:
            logger.error(f"Erreur lors de l'association des documents: {assoc_error}")
    else:
        logger.warning("Aucun document source valide")


def _process_single_question(question, index: int, total: int, agent_retriever, agent_qa) -> bool:
    """
    Process a single question: retrieve documents, generate answer, create instances.

    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        logger.info(f"Traitement de la question {index+1}/{total}: {question.title}")

        # Delete old answer
        _delete_old_answer(question)

        # Retrieve documents
        documents = _retrieve_documents(agent_retriever, question.field)
        if not documents:
            logger.warning(f"Aucun document récupéré pour {question.title}")

        # Generate answer
        answer_json = _generate_answer(agent_qa, question.field, documents)
        if not answer_json:
            logger.error(f"Impossible de générer une réponse pour {question.title}")
            return False

        # Create answer instance
        answer_instance = _create_answer_instance(question, answer_json, index)
        if not answer_instance:
            return False

        # Create and associate source documents
        _create_source_documents(answer_json, answer_instance, index)

        logger.info(f"Question {question.title} traitée avec succès")
        return True

    except Exception as e:
        logger.error(f"Erreur lors du traitement de la question {question.title}: {e}")
        logger.error(f"Type d'erreur: {type(e).__name__}")
        logger.error("Traceback complet: ", exc_info=True)
        return False


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
        config_path: Chemin vers le fichier de configuration RAG

    Returns:
        Dict containing task response with status, processed count, and metadata
    """
    start_time = time.time()

    try:
        logger.info("--------------------------------")
        logger.info(f"🚀 Démarrage du processus QA pour la source {source_id}")

        # Validate configuration path
        try:
            config_path_obj = _validate_config_path(config_path)
        except (ValueError, FileNotFoundError) as config_error:
            logger.error(f"Erreur de configuration: {config_error}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=config_error,
                message="Configuration invalide ou introuvable"
            )

        # Get source and questions
        try:
            source, questions = _get_source_with_questions(source_id)
        except Source.DoesNotExist:
            logger.error(f"Source {source_id} non trouvée")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=ValueError(f"Source {source_id} non trouvée"),
                message="Source introuvable"
            )
        except Exception as source_error:
            logger.error(f"Erreur lors de la récupération de la source: {source_error}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=source_error,
                message="Erreur lors de la récupération de la source"
            )

        # Check if there are questions to process
        if not questions.exists():
            logger.warning(f"Aucune question trouvée pour la source {source_id}")
            return create_success_response(
                source_id=source_id,
                config_path=config_path,
                processed=0,
                total=0,
                message="Aucune question à traiter"
            )

        logger.info(f"Traitement de {questions.count()} questions")

        # Initialize RAG agents
        try:
            agent_qa, agent_retriever = _initialize_rag_agents(config_path_obj)
        except Exception as init_error:
            logger.error(f"Erreur lors de l'initialisation des agents: {init_error}")
            return create_error_response(
                source_id=source_id,
                config_path=config_path,
                error=init_error,
                message="Erreur lors de l'initialisation des outils RAG"
            )

        # Process each question
        processed_count = 0
        total_count = questions.count()

        for i, question in enumerate(questions):
            success = _process_single_question(
                question, i, total_count, agent_retriever, agent_qa
            )
            if success:
                processed_count += 1

        # Return results
        execution_time = time.time() - start_time
        logger.info(f"Processus QA terminé. {processed_count}/{total_count} questions traitées.")

        return create_success_response(
            source_id=source_id,
            config_path=config_path,
            processed=processed_count,
            total=total_count,
            message=f"Processus QA terminé. {processed_count} questions traitées sur {total_count}.",
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Erreur globale lors du processus QA: {e}")
        logger.error(f"Type d'erreur: {type(e).__name__}")
        logger.error("Traceback complet: ", exc_info=True)

        return create_error_response(
            source_id=source_id,
            config_path=config_path,
            error=e,
            message="Erreur lors du processus QA"
        )
