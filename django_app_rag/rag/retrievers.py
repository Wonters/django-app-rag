from typing import Literal, Union
from django_app_rag.rag.logging_setup import get_logger

logger = get_logger(__name__)

from django_app_rag.rag.infrastructur.faiss.retriever import FaissParentDocumentRetriever
from .embeddings import EmbeddingModelType, EmbeddingsModel, get_embedding_model
from .splitters import get_splitter

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
    similarity_score_threshold: float = 0.5
) -> RetrieverModel:
    logger.info(
        f"Getting '{retriever_type}' retriever for '{embedding_model_type}' - '{embedding_model_id}' on '{device}' "
        f"with {k} top results and similarity threshold {similarity_score_threshold}"
    )

    embedding_model = get_embedding_model(
        embedding_model_id, embedding_model_type, device
    )

    try:
        return RETRIEVER_TYPES[vectorstore][retriever_type](embedding_model, k, persistent_path, similarity_score_threshold)
    except KeyError:
        raise ValueError(f"Invalid retriever type: {retriever_type}")



def get_parent_document_retriever(
    embedding_model: EmbeddingsModel, k: int = 3, persistent_path: str = None, similarity_score_threshold: float = 0.5
) -> FaissParentDocumentRetriever:
    retriever = FaissParentDocumentRetriever(
        embedding_model=embedding_model,
        child_splitter=get_splitter(200),
        parent_splitter=get_splitter(800),
        search_kwargs={"k": k},
        persistent_path=persistent_path,
        similarity_score_threshold=similarity_score_threshold,
    )

    return retriever


RETRIEVER_TYPES = {"faiss": {"parent": get_parent_document_retriever}}
