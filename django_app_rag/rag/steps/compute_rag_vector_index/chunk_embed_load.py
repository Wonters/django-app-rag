from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Generator

from langchain_core.documents import Document as LangChainDocument

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from tqdm import tqdm
from zenml.steps import step
from pathlib import Path
from django_app_rag.rag.retrievers import (
    EmbeddingModelType,
    get_retriever,
    get_splitter,
    RetrieverType,
)
from django_app_rag.rag.splitters import SummarizationType
from django_app_rag.rag.models import Document
from django_app_rag.rag.settings import settings

from django_app_rag.rag.infrastructur.faiss import FaissDBIndex
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage
from django_app_rag.rag.models import Collection

DBINDEX = {"faiss": FaissDBIndex}

MAX_CONCURRENT_REQUESTS = 10

@step(enable_cache=False)
def chunk_embed_load(
    documents: list,
    collection_name: str,
    processing_batch_size: int,
    processing_max_workers: int,
    retriever_type: RetrieverType,
    embedding_model_id: str,
    embedding_model_type: EmbeddingModelType,
    embedding_model_dim: int,
    chunk_size: int,
    vectorstore: str = "faiss",
    contextual_summarization_type: SummarizationType = "none",
    contextual_agent_model_id: str | None = None,
    contextual_agent_max_characters: int | None = None,
    mock: bool = False,
    device: str = "cpu",
    data_dir: str = None,
) -> None:
    """Process documents by chunking, embedding, and loading into MongoDB.

    Args:
        vectorstore: Type of storage used (atlas mongo or faiss).
        documents: List of documents to process.
        collection_name: Name of MongoDB collection to store documents.
        processing_batch_size: Number of documents to process in each batch.
        processing_max_workers: Maximum number of concurrent processing threads.
        retriever_type: Type of retriever to use for document processing.
        embedding_model_id: Identifier for the embedding model.
        embedding_model_type: Type of embedding model to use.
        embedding_model_dim: Dimension of the embedding vectors.
        chunk_size: Size of text chunks for splitting documents.
        contextual_summarization_type: Type of summarization to apply. Defaults to "none".
        contextual_agent_model_id: ID of the model used for contextual summarization. Defaults to None.
        contextual_agent_max_characters: Maximum characters for contextual summarization. Defaults to None.
        mock: Whether to use mock processing. Defaults to False.
        device: Device to run embeddings on ('cpu', 'cuda' or 'mps). Defaults to 'cpu'.
    """

    retriever = get_retriever(
        embedding_model_id=embedding_model_id,
        embedding_model_type=embedding_model_type,
        retriever_type=retriever_type,
        device=device,
        vectorstore=vectorstore,
        persistent_path=data_dir,
    )
    splitter = get_splitter(
        chunk_size=chunk_size,
        summarization_type=contextual_summarization_type,
        model_id=contextual_agent_model_id,
        max_characters=contextual_agent_max_characters,
        mock=mock,
        max_concurrent_requests=processing_max_workers,
    )


    docs = [
        LangChainDocument(
            page_content=doc.content, metadata=doc.metadata.model_dump()
        )
        for doc in documents
        if doc
    ]
    logger.info(f"Processing {len(docs)} documents for chunk embedding")
    process_docs(
        retriever,
        docs,
        splitter=splitter,
        batch_size=processing_batch_size,
        max_workers=processing_max_workers,
    )

    index = DBINDEX[vectorstore](
        retriever=retriever,
    )
    index.create(
        embedding_dim=embedding_model_dim,
        is_hybrid=retriever_type == "contextual",
    )


def process_docs(
    retriever: Any,
    docs: list[LangChainDocument],
    splitter: RecursiveCharacterTextSplitter,
    batch_size: int = 4,
    max_workers: int = 2,
) -> list[None]:
    """Process LangChain documents into Faiss using thread pool.

    Args:
        retriever: Faiss document retriever instance.
        docs: List of LangChain documents to process.
        splitter: Text splitter instance for chunking documents.
        batch_size: Number of documents to process in each batch.
        max_workers: Maximum number of concurrent threads.

    Returns:
        List of None values representing completed batch processing results.
    """
    batches = list(get_batches(docs, batch_size))
    results = []
    total_docs = len(docs)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_batch, retriever, batch, splitter)
            for batch in batches
        ]

        with tqdm(total=total_docs, desc="Processing documents") as pbar:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                pbar.update(batch_size)

    return results


def get_batches(
    docs: list[LangChainDocument], batch_size: int
) -> Generator[list[LangChainDocument], None, None]:
    """Return batches of documents to ingest into MongoDB.

    Args:
        docs: List of LangChain documents to batch.
        batch_size: Number of documents in each batch.

    Yields:
        Generator[list[LangChainDocument]]: Batches of documents of size batch_size.
    """
    for i in range(0, len(docs), batch_size):
        logger.info(f"Batch {i} of {len(docs)}")
        yield docs[i : i + batch_size]


def process_batch(
    retriever: Any,
    batch: list[LangChainDocument],
    splitter: RecursiveCharacterTextSplitter,
) -> None:
    """Ingest batches of documents into MongoDB by splitting and embedding.

    Args:
        retriever: MongoDB Atlas document retriever instance.
        batch: List of documents to ingest in this batch.
        splitter: Text splitter instance for chunking documents.

    Raises:
        Exception: If there is an error processing the batch of documents.
    """
    try:
        logger.info(f"Splitting {len(batch)} documents")
        
        # The splitter now handles parallelization internally
        split_docs = splitter.split_documents(batch)
        
        if split_docs:
            retriever.add_documents(split_docs)
            logger.info(f"Successfully processed {len(batch)} documents with {len(split_docs)} chunks.")
        else:
            logger.warning(f"No chunks generated for batch of {len(batch)} documents")
            
    except Exception as e:
        logger.warning(f"Error processing batch of {len(batch)} documents: {str(e)}")
