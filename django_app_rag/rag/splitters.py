from typing import Callable, Literal, Union, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from django_app_rag.logging import get_logger_loguru
from django_app_rag.rag.monitoring.processing_monitor import ProcessingContext
from django_app_rag.rag.mixins.task_processing_mixin import DocumentProcessingMixin, TaskConfig

logger = get_logger_loguru(__name__)

import copy
from .agents import (
    ContextualSummarizationAgent,
    SimpleSummarizationAgent,
)

# Add type definitions at the top of the file
SummarizationType = Literal["contextual", "simple", "none"]
SummarizationAgent = Union[ContextualSummarizationAgent, SimpleSummarizationAgent]


def get_splitter(
    chunk_size: int, summarization_type: SummarizationType = "none", **kwargs
) -> RecursiveCharacterTextSplitter:
    """Returns a token-based text splitter with overlap.

    Args:
        chunk_size: Number of tokens for each text chunk.
        summarization_type: Type of summarization to use ("contextual" or "simple").
        **kwargs: Additional keyword arguments passed to the summarization agent.

    Returns:
        RecursiveCharacterTextSplitter: A configured text splitter instance with
            summarization capabilities.
    """

    chunk_overlap = int(0.15 * chunk_size)

    logger.info(
        f"Getting splitter with chunk size: {chunk_size} and overlap: {chunk_overlap}"
    )

    if summarization_type == "none":
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    if summarization_type == "contextual":
        handler = ContextualSummarizationAgent(**kwargs)
    elif summarization_type == "simple":
        handler = SimpleSummarizationAgent(**kwargs)

    # Extract max_concurrent_requests for ThreadPoolExecutor
    max_concurrent_requests = kwargs.get("max_concurrent_requests", 20)

    return HandlerRecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        handler=handler,
        max_concurrent_requests=max_concurrent_requests,
    )


class HandlerRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter, DocumentProcessingMixin[Tuple[str, dict], List[LangChainDocument]]):
    """A text splitter that can apply custom handling to chunks after splitting.

    This class extends RecursiveCharacterTextSplitter to allow post-processing of text chunks
    through a handler function. If no handler is provided, chunks are returned unchanged.
    """

    def __init__(
        self,
        handler: Callable[[str, list[str]], list[str]] | None = None,
        max_concurrent_requests: int = 20,
        memory_limit_mb: int = 1024,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the splitter with an optional handler function.

        Args:
            handler: Optional callable that takes the original text and list of chunks,
                and returns a modified list of chunks. If None, chunks are returned unchanged.
            max_concurrent_requests: Maximum number of worker threads for parallel processing.
            memory_limit_mb: Memory limit in MB for processing (default: 1024MB).
            *args: Additional positional arguments passed to RecursiveCharacterTextSplitter.
            **kwargs: Additional keyword arguments passed to RecursiveCharacterTextSplitter.
        """
        super().__init__(*args, **kwargs)
        
        # Initialize the mixin
        config = TaskConfig(
            max_workers=max_concurrent_requests,
            batch_size=1,  # Process one text at a time
            timeout_per_item=180,
            timeout_total=300,
            memory_limit_mb=memory_limit_mb,
            heartbeat_interval=15
        )
        DocumentProcessingMixin.__init__(self, "document_splitting", config)

        self.handler = handler if handler is not None else lambda _, x: x

    def process_single_item(self, item: Tuple[str, dict], item_index: int) -> List[LangChainDocument]:
        """
        Process a single text-metadata pair into document chunks.
        
        Args:
            item: Tuple of (text, metadata)
            item_index: Index of the item in the batch
            
        Returns:
            List of LangChainDocument chunks
        """
        text, metadata = item
        return self._process_single_text(text, metadata, item_index)
    
    def validate_item(self, item: Tuple[str, dict]) -> bool:
        """
        Validate a text-metadata pair.
        
        Args:
            item: Tuple of (text, metadata)
            
        Returns:
            True if valid, False otherwise
        """
        text, metadata = item
        return bool(text and isinstance(text, str) and isinstance(metadata, dict))

    def create_documents(
        self, texts: List[str], metadatas: Optional[List[dict]] = None
    ) -> List[LangChainDocument]:
        """Create documents from a list of texts with parallel processing."""
        _metadatas = metadatas or [{}] * len(texts)
        
        # If handler is the default lambda, process sequentially
        if self.handler.__class__.__name__ == '<lambda>':
            return super().create_documents(texts, _metadatas)
        
        logger.info(f"Starting parallel processing of {len(texts)} documents with {self.config.max_workers} workers")
        
        # Use the mixin's robust processing logic
        return self._process_texts_robustly(texts, _metadatas)
    
    def _process_texts_robustly(self, texts: List[str], metadatas: List[dict]) -> List[LangChainDocument]:
        """Process texts using the mixin's robust processing logic."""
        documents = []
        
        # Check memory before starting
        if not self._check_memory_usage():
            logger.warning("Memory usage high, reducing concurrent requests")
            self.config.max_workers = max(1, self.config.max_workers // 2)
        
        # Use monitoring context for document processing
        with ProcessingContext("document_splitting", self.config.heartbeat_interval) as monitor:
            # Use ThreadPoolExecutor for parallel processing of multiple documents
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                # Submit tasks for each text
                futures = {
                    executor.submit(self._process_single_text, text, metadatas[i], i): i 
                    for i, text in enumerate(texts)
                }
                
                completed_count = 0
                failed_count = 0
                
                # Collect results with improved error handling and monitoring
                for future in as_completed(futures, timeout=self.config.timeout_total):
                    try:
                        doc_chunks = future.result(timeout=self.config.timeout_per_item)
                        documents.extend(doc_chunks)
                        completed_count += 1
                        
                        # Update monitoring
                        monitor.update_activity(processed=1, failed=0)
                        
                        # Check memory usage periodically
                        if completed_count % 20 == 0 and not self._check_memory_usage():
                            logger.warning("Memory usage high during processing, consider reducing batch size")
                        
                        # Log progress every 10 documents
                        if completed_count % 10 == 0:
                            logger.info(f"Processed {completed_count}/{len(texts)} documents successfully")
                            
                    except TimeoutError:
                        text_index = futures[future]
                        logger.error(f"Timeout processing document {text_index} after {self.config.timeout_per_item} seconds")
                        failed_count += 1
                        monitor.update_activity(processed=0, failed=1)
                        # Continue processing other documents
                        
                    except Exception as e:
                        text_index = futures[future]
                        logger.error(f"Error processing document {text_index}: {str(e)}")
                        failed_count += 1
                        monitor.update_activity(processed=0, failed=1)
                        # Continue processing other documents even if one fails
            
            logger.info(f"Document processing completed: {completed_count} successful, {failed_count} failed")
            return documents
    
    def _process_single_text(self, text: str, metadata: dict, text_index: int) -> List[LangChainDocument]:
        """Process a single text and return its document chunks.
        
        Args:
            text: The text to process
            metadata: Metadata for the text
            text_index: Index of the text in the original list
            
        Returns:
            List[LangChainDocument]: List of document chunks for this text
        """
        try:
            # Validate input
            if not text or not isinstance(text, str):
                logger.warning(f"Invalid text for document {text_index}: {type(text)}")
                return []
            
            # Split text with error handling
            try:
                chunks = self.split_text(text)
            except Exception as e:
                logger.error(f"Error splitting text {text_index}: {str(e)}")
                return []
            
            # Use debug level to reduce logging in multi-threaded context
            logger.debug(f"Splitting text {text_index} into {len(chunks)} chunks")
            documents = []
            
            # Récupérer l'ID du document parent
            parent_id = metadata.get("id", f"doc_{text_index}")
            
            index = 0
            previous_chunk_len = 0
            for chunk_index, chunk in enumerate(chunks):
                try:
                    # Validate chunk
                    if not chunk or not isinstance(chunk, str):
                        logger.warning(f"Invalid chunk {chunk_index} for document {text_index}")
                        continue
                    
                    chunk_metadata = copy.deepcopy(metadata)
                    
                    # Générer un ID unique pour chaque chunk
                    chunk_id = f"{parent_id}_chunk_{chunk_index:03d}"
                    chunk_metadata["id"] = chunk_id
                    chunk_metadata["chunk_index"] = chunk_index
                    chunk_metadata["parent_id"] = parent_id
                    
                    if self._add_start_index:
                        offset = index + previous_chunk_len - self._chunk_overlap
                        index = text.find(chunk, max(0, offset))
                        chunk_metadata["start_index"] = index
                        previous_chunk_len = len(chunk)
                    
                    # Créer le document avec l'ID unique
                    new_doc = LangChainDocument(
                        page_content=chunk, 
                        metadata=chunk_metadata
                    )
                    
                    # S'assurer que l'ID est bien défini
                    if hasattr(new_doc, 'metadata') and 'id' in new_doc.metadata:
                        # Use debug level to reduce logging in multi-threaded context
                        logger.debug(f"Chunk créé: ID={new_doc.metadata['id']}, Parent={parent_id}, Index={chunk_index}")
                    
                    documents.append(new_doc)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_index} for document {text_index}: {str(e)}")
                    continue
            
            logger.debug(f"Successfully processed document {text_index} into {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Critical error processing document {text_index}: {str(e)}")
            return []

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks and apply the handler function.

        Args:
            text: The input text to split.

        Returns:
            list[str]: The processed text chunks after splitting and handling.
        """
        chunks = super().split_text(text)
        # Apply handler directly (parallelization is now in create_documents)
        return self.handler(text, chunks)
