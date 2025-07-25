from typing import Literal, Union
from loguru import logger

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
    vectorstore: str = "faiss"
) -> RetrieverModel:
    logger.info(
        f"Getting '{retriever_type}' retriever for '{embedding_model_type}' - '{embedding_model_id}' on '{device}' "
        f"with {k} top results"
    )

    embedding_model = get_embedding_model(
        embedding_model_id, embedding_model_type, device
    )

    try:
        return RETRIEVER_TYPES[vectorstore][retriever_type](embedding_model, k)
    except KeyError:
        raise ValueError(f"Invalid retriever type: {retriever_type}")



def get_parent_document_retriever(
    embedding_model: EmbeddingsModel, k: int = 3
) -> FaissParentDocumentRetriever:
    retriever = FaissParentDocumentRetriever(
        embedding_model=embedding_model,
        child_splitter=get_splitter(200),
        parent_splitter=get_splitter(800),
        search_kwargs={"k": k},
    )

    return retriever


RETRIEVER_TYPES = {"faiss": {"parent": get_parent_document_retriever}}
