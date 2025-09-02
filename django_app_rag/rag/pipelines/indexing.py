from zenml import pipeline
from django_app_rag.rag.logging_setup import get_logger
from typing import Union

logger = get_logger(__name__)
from ..embeddings import EmbeddingModelType
from ..retrievers import RetrieverType
from ..splitters import SummarizationType
from ..steps.compute_rag_vector_index import chunk_embed_load, filter_by_quality
from ..steps.infrastructure import read_documents_from_diskstorage


@pipeline
def compute_rag_vector_index(
    collection_name: str,
    fetch_limit: int,
    content_quality_score_threshold: float,
    retriever_type: RetrieverType,
    embedding_model_id: str,
    embedding_model_type: EmbeddingModelType,
    embedding_model_dim: int,
    chunk_size: int,
    vectorstore:str = "faiss",
    contextual_summarization_type: SummarizationType = "none",
    contextual_agent_model_id: str | None = None,
    contextual_agent_max_characters: int | None = None,
    mock: bool = False,
    processing_batch_size: int = 256,
    processing_max_workers: int = 10,
    device: str = "cpu",
    data_dir: str = "data",
    mode : str = "overwrite",
    id_documents: Union[list[str], None] = None
) -> None:
    """Computes and stores RAG vector index from documents in DiskStorage.

    This pipeline fetches documents from DiskStorage, filters them by quality,
    chunks the content, computes embeddings, and stores the results.

    Args:
        vectorstore:
        collection_name: Name of DiskStorage collection to fetch documents from and store results in
        fetch_limit: Maximum number of documents to fetch
        content_quality_score_threshold: Minimum quality score for documents to be included
        retriever_type: Type of retriever to use for vector search
        embedding_model_id: Identifier for the embedding model
        embedding_model_type: Type of embedding model (e.g. OpenAI, HuggingFace)
        embedding_model_dim: Dimension of the embedding vectors
        chunk_size: Size of text chunks for embedding
        contextual_summarization_type: Type of summarization to apply to chunks
        contextual_agent_model_id: Model ID for contextual summarization agent
        contextual_agent_max_characters: Maximum characters for contextual summaries
        mock: Whether to run in mock mode
        processing_batch_size: Batch size for parallel processing
        processing_max_workers: Number of worker threads for parallel processing
        device: Device to run embeddings on ('cpu' or 'cuda')

    Returns:
        None
    """
    documents = read_documents_from_diskstorage(
        collection_name=collection_name, limit=fetch_limit, data_dir=data_dir, mode=mode, id_documents=id_documents
    )

    documents_filtered = filter_by_quality(
        documents=documents,
        content_quality_score_threshold=content_quality_score_threshold,
    )
    
    chunk_embed_load(
        documents=documents_filtered,
        collection_name=collection_name,
        processing_batch_size=processing_batch_size,
        processing_max_workers=processing_max_workers,
        retriever_type=retriever_type,
        embedding_model_id=embedding_model_id,
        embedding_model_type=embedding_model_type,
        embedding_model_dim=embedding_model_dim,
        chunk_size=chunk_size,
        vectorstore=vectorstore,
        contextual_summarization_type=contextual_summarization_type,
        contextual_agent_model_id=contextual_agent_model_id,
        contextual_agent_max_characters=contextual_agent_max_characters,
        mock=mock,
        device=device,
        data_dir=data_dir,
    )
