from typing import Literal, Optional, Union
from django_app_rag.logging import get_logger_loguru
from django_app_rag.rag.infrastructur.faiss.retriever import FaissParentDocumentRetriever
from .embeddings import EmbeddingModelType, EmbeddingsModel, get_embedding_model
from .splitters import get_splitter
from functools import lru_cache
from pathlib import Path
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage

logger = get_logger_loguru(__name__)

# Add these type definitions at the top of the file
RetrieverType = Literal["contextual", "parent"]
RetrieverModel = Union[FaissParentDocumentRetriever]


def get_retriever(
    embedding_model_id: str,
    embedding_model_type: EmbeddingModelType = "huggingface",
    retriever_type: RetrieverType = "parent",
    k: int = 3,
    device: str = "cpu",
    vectorstore: str = "faiss",
    persistent_path: str = None,
    similarity_score_threshold: float = 0.5,
    child_chunk_size: int = 200,
    parent_chunk_size: int = 800,
    reranker_model_id: Optional[str] = None,
    use_hybrid_retrieval: bool = False,
) -> RetrieverModel:
    logger.info(
        f"Getting '{retriever_type}' retriever for '{embedding_model_type}' - '{embedding_model_id}' on '{device}' "
        f"with k={k}, threshold={similarity_score_threshold}, "
        f"child_chunk={child_chunk_size}, parent_chunk={parent_chunk_size}, "
        f"hybrid={use_hybrid_retrieval}, reranker={reranker_model_id}"
    )

    embedding_model = get_embedding_model(
        embedding_model_id, embedding_model_type, device
    )

    try:
        factory = RETRIEVER_TYPES[vectorstore][retriever_type]
        return factory(
            embedding_model,
            k,
            persistent_path,
            similarity_score_threshold,
            child_chunk_size=child_chunk_size,
            parent_chunk_size=parent_chunk_size,
            reranker_model_id=reranker_model_id,
            use_hybrid_retrieval=use_hybrid_retrieval,
        )
    except KeyError:
        raise ValueError(f"Invalid retriever type: {retriever_type}")


def get_parent_document_retriever(
    embedding_model: EmbeddingsModel,
    k: int = 3,
    persistent_path: str = None,
    similarity_score_threshold: float = 0.5,
    child_chunk_size: int = 200,
    parent_chunk_size: int = 800,
    reranker_model_id: Optional[str] = None,
    use_hybrid_retrieval: bool = False,
) -> FaissParentDocumentRetriever:
    # T4: child_chunk_size and parent_chunk_size are now configurable
    # instead of being hardcoded to 200 and 800.
    retriever = FaissParentDocumentRetriever(
        embedding_model=embedding_model,
        child_splitter=get_splitter(child_chunk_size),
        parent_splitter=get_splitter(parent_chunk_size),
        search_kwargs={"k": k},
        persistent_path=persistent_path,
        similarity_score_threshold=similarity_score_threshold,
        reranker_model_id=reranker_model_id,
        use_hybrid_retrieval=use_hybrid_retrieval,
    )

    return retriever


RETRIEVER_TYPES = {"faiss": {"parent": get_parent_document_retriever}}


@lru_cache(maxsize=128)
def get_chunk_text_by_uid(
    data_dir: str,
    uid: str,
    embedding_model_id: str,
    embedding_model_type: str = "huggingface",
) -> str:
    """
    Récupère le texte d'un chunk par son UID depuis l'index FAISS.

    T4: Le modèle d'embedding n'est plus hardcodé — il doit correspondre
    au modèle utilisé lors de l'indexation (lu depuis la config de la collection).

    Args:
        data_dir: Chemin vers le répertoire de données de la collection
        uid: L'UID du chunk à récupérer
        embedding_model_id: Modèle d'embedding utilisé pour l'indexation
        embedding_model_type: Type du modèle ("huggingface" ou "openai")

    Returns:
        Le texte du chunk ou None si non trouvé
    """
    try:
        if not Path(data_dir).exists():
            logger.warning(f"Data directory does not exist: {data_dir}")
            return None

        retriever = get_retriever(
            embedding_model_id=embedding_model_id,
            embedding_model_type=embedding_model_type,
            retriever_type="parent",
            k=1,
            device="cpu",
            vectorstore="faiss",
            persistent_path=data_dir,
        )

        docstore = retriever.vectorstore.docstore

        for chunk_id, chunk in docstore._dict.items():
            if chunk.metadata.get("id") == uid:
                logger.debug(f"Chunk found for UID {uid}")
                return chunk.page_content

        logger.warning(f"No chunk found for UID: {uid}")
        return None

    except Exception as e:
        logger.error(f"Error retrieving chunk {uid}: {str(e)}")
        return None


@lru_cache(maxsize=128)
def get_document_text_cached(document_id: str, data_dir: str, collection_name: str) -> dict:
    """
    Fonction cachée pour récupérer le texte d'un document depuis le DiskStorage.

    Args:
        document_id: ID du document à récupérer
        data_dir: Chemin vers le répertoire de données
        collection_name: Nom de la collection

    Returns:
        Le dictionnaire du document ou None si non trouvé
    """
    try:
        disk_storage = DiskStorage(data_dir=data_dir, collection_name=collection_name)
        documents = disk_storage.read([document_id])

        if not documents or len(documents) == 0:
            return None

        document = documents[0]
        return document.model_dump()

    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {str(e)}")
        return None
