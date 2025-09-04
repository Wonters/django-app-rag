import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Generator, Optional
from langchain_core.documents import Document as LangChainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from django_app_rag.logging import get_logger_loguru
from tqdm import tqdm
from zenml.steps import step
from django_app_rag.rag.retrievers import (
    EmbeddingModelType,
    get_retriever,
    get_splitter,
    RetrieverType,
)
from django_app_rag.rag.splitters import SummarizationType
from django_app_rag.rag.monitoring.processing_monitor import ProcessingContext
from django_app_rag.rag.mixins.task_processing_mixin import DocumentProcessingMixin, TaskConfig, TaskResult

logger = get_logger_loguru(__name__)

MAX_CONCURRENT_REQUESTS = 10


class DocumentBatchProcessor(DocumentProcessingMixin[LangChainDocument, None]):
    """Processor for batches of documents using the robust task processing mixin."""
    
    def __init__(self, retriever: Any, splitter: RecursiveCharacterTextSplitter, 
                 batch_size: int = 4, max_workers: int = 2):
        """
        Initialize the document batch processor.
        
        Args:
            retriever: Document retriever instance
            splitter: Text splitter instance
            batch_size: Number of documents per batch
            max_workers: Maximum number of worker threads
        """
        config = TaskConfig(
            max_workers=max_workers,
            batch_size=batch_size,
            timeout_per_item=300,  # 5 minutes per batch
            timeout_total=600,     # 10 minutes total
            max_consecutive_failures=3,
            memory_limit_mb=1024,
            heartbeat_interval=30
        )
        super().__init__("document_batch_processing", config)
        
        self.retriever = retriever
        self.splitter = splitter
    
    def process_single_item(self, item: LangChainDocument, item_index: int) -> None:
        """
        Process a single document.
        
        Args:
            item: The document to process
            item_index: Index of the document in the batch
            
        Returns:
            None (side effect: adds documents to retriever)
        """
        # Extract text and metadata
        text = item.page_content
        metadata = item.metadata
        
        if not text:
            logger.warning(f"Empty content for document {item_index}")
            return
        
        # Split document into chunks
        try:
            split_docs = self.splitter.create_documents([text], [metadata])
            
            if split_docs:
                # Add to retriever
                self.retriever.add_documents(split_docs)
                logger.debug(f"Successfully processed document {item_index} into {len(split_docs)} chunks")
            else:
                logger.warning(f"No chunks generated for document {item_index}")
                
        except Exception as e:
            logger.error(f"Error processing document {item_index}: {str(e)}")
            raise
    
    def validate_item(self, item: LangChainDocument) -> bool:
        """
        Validate a document item.
        
        Args:
            item: The document to validate
            
        Returns:
            True if valid, False otherwise
        """
        return bool(item and hasattr(item, 'page_content') and item.page_content)

@step()
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
    
    # Use the robust document processor
    processor = DocumentBatchProcessor(
        retriever=retriever,
        splitter=splitter,
        batch_size=processing_batch_size,
        max_workers=processing_max_workers
    )
    
    result = processor.process_items(docs)
    
    if not result.success:
        logger.error(f"Document processing failed: {result.error_message}")
    else:
        logger.info(f"Successfully processed {result.processed_count} documents in {result.total_time:.2f}s")



# Legacy function kept for backward compatibility
def process_docs(
    retriever: Any,
    docs: list[LangChainDocument],
    splitter: RecursiveCharacterTextSplitter,
    batch_size: int = 4,
    max_workers: int = 2,
    monitor: Optional[Any] = None,
) -> list[None]:
    """Legacy function - use DocumentBatchProcessor instead.
    
    This function is kept for backward compatibility but should be replaced
    with DocumentBatchProcessor for better error handling and monitoring.
    """
    logger.warning("Using legacy process_docs function. Consider using DocumentBatchProcessor instead.")
    
    processor = DocumentBatchProcessor(
        retriever=retriever,
        splitter=splitter,
        batch_size=batch_size,
        max_workers=max_workers
    )
    
    result = processor.process_items(docs)
    return [None] * result.processed_count  # Return legacy format


# Legacy functions removed - functionality moved to DocumentBatchProcessor
