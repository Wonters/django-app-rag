from typing import Callable, Literal, Union, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from django_app_rag.rag.logging_setup import get_logger

logger = get_logger(__name__)

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


class HandlerRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    """A text splitter that can apply custom handling to chunks after splitting.

    This class extends RecursiveCharacterTextSplitter to allow post-processing of text chunks
    through a handler function. If no handler is provided, chunks are returned unchanged.
    """

    def __init__(
        self,
        handler: Callable[[str, list[str]], list[str]] | None = None,
        max_concurrent_requests: int = 20,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the splitter with an optional handler function.

        Args:
            handler: Optional callable that takes the original text and list of chunks,
                and returns a modified list of chunks. If None, chunks are returned unchanged.
            max_concurrent_requests: Maximum number of worker threads for parallel processing.
            *args: Additional positional arguments passed to RecursiveCharacterTextSplitter.
            **kwargs: Additional keyword arguments passed to RecursiveCharacterTextSplitter.
        """
        super().__init__(*args, **kwargs)

        self.handler = handler if handler is not None else lambda _, x: x
        self.max_concurrent_requests = max_concurrent_requests

    def create_documents(
        self, texts: List[str], metadatas: Optional[List[dict]] = None
    ) -> List[LangChainDocument]:
        """Create documents from a list of texts with parallel processing."""
        _metadatas = metadatas or [{}] * len(texts)
        documents = []
        
        # If handler is the default lambda, process sequentially
        if self.handler.__class__.__name__ == '<lambda>':
            return super().create_documents(texts, _metadatas)
        
        # Use ThreadPoolExecutor for parallel processing of multiple documents
        with ThreadPoolExecutor(max_workers=self.max_concurrent_requests) as executor:
            # Submit tasks for each text
            futures = [
                executor.submit(self._process_single_text, text, _metadatas[i], i)
                for i, text in enumerate(texts)
            ]
            
            # Collect results
            for future in as_completed(futures):
                try:
                    doc_chunks = future.result(timeout=120)  # 2 minute timeout per document
                    documents.extend(doc_chunks)
                except Exception as e:
                    logger.warning(f"Error processing document: {str(e)}")
                    # Continue processing other documents even if one fails
        
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
        chunks = self.split_text(text)
        logger.info(f"Splitting text {text_index} into {len(chunks)} chunks")
        documents = []
        
        # Récupérer l'ID du document parent
        parent_id = metadata.get("id", f"doc_{text_index}")
        
        index = 0
        previous_chunk_len = 0
        for chunk_index, chunk in enumerate(chunks):
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
                logger.debug(f"Chunk créé: ID={new_doc.metadata['id']}, Parent={parent_id}, Index={chunk_index}")
            
            documents.append(new_doc)
        
        return documents

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
