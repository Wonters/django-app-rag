import time
import threading
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict, Callable, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from django_app_rag.logging import get_logger_loguru
from django_app_rag.rag.monitoring.processing_monitor import ProcessingContext

logger = get_logger_loguru(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class TaskConfig:
    """Configuration for task processing."""
    max_workers: int = 4
    batch_size: int = 10
    timeout_per_item: int = 180  # 3 minutes
    timeout_total: int = 600  # 10 minutes
    max_consecutive_failures: int = 3
    memory_limit_mb: int = 1024
    heartbeat_interval: int = 30
    progress_log_interval: int = 10


@dataclass
class TaskResult:
    """Result of task processing."""
    success: bool
    processed_count: int
    failed_count: int
    total_time: float
    error_message: Optional[str] = None


class TaskProcessingMixin(ABC, Generic[T, R]):
    """
    Mixin for robust parallel task processing with monitoring and error handling.
    
    This mixin provides a standardized way to process items in parallel with:
    - Timeout management
    - Circuit breaker pattern
    - Memory monitoring
    - Progress tracking
    - Error recovery
    """
    
    def __init__(self, task_name: str, config: Optional[TaskConfig] = None):
        """
        Initialize the task processing mixin.
        
        Args:
            task_name: Name of the task for monitoring
            config: Task configuration, uses defaults if None
        """
        self.task_name = task_name
        self.config = config or TaskConfig()
        self._lock = threading.Lock()
    
    @abstractmethod
    def process_single_item(self, item: T, item_index: int) -> R:
        """
        Process a single item. Must be implemented by subclasses.
        
        Args:
            item: The item to process
            item_index: Index of the item in the batch
            
        Returns:
            The processed result
            
        Raises:
            Exception: If processing fails
        """
        pass
    
    @abstractmethod
    def validate_item(self, item: T) -> bool:
        """
        Validate an item before processing. Must be implemented by subclasses.
        
        Args:
            item: The item to validate
            
        Returns:
            True if item is valid, False otherwise
        """
        pass
    
    def _check_memory_usage(self) -> bool:
        """Check if memory usage is within limits."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.config.memory_limit_mb:
                logger.warning(f"Memory usage {memory_mb:.1f}MB exceeds limit {self.config.memory_limit_mb}MB")
                return False
            return True
        except Exception as e:
            logger.warning(f"Could not check memory usage: {str(e)}")
            return True
    
    def _adjust_workers_for_memory(self) -> int:
        """Adjust number of workers based on memory usage."""
        if not self._check_memory_usage():
            adjusted_workers = max(1, self.config.max_workers // 2)
            logger.warning(f"Memory usage high, reducing workers from {self.config.max_workers} to {adjusted_workers}")
            return adjusted_workers
        return self.config.max_workers
    
    def process_items(self, items: List[T]) -> TaskResult:
        """
        Process a list of items with robust error handling and monitoring.
        
        Args:
            items: List of items to process
            
        Returns:
            TaskResult with processing statistics
        """
        start_time = time.time()
        
        # Filter valid items
        valid_items = [item for item in items if self.validate_item(item)]
        invalid_count = len(items) - len(valid_items)
        
        if invalid_count > 0:
            logger.warning(f"Filtered out {invalid_count} invalid items")
        
        if not valid_items:
            logger.warning("No valid items to process")
            return TaskResult(
                success=True,
                processed_count=0,
                failed_count=invalid_count,
                total_time=time.time() - start_time
            )
        
        # Adjust workers based on memory
        actual_workers = self._adjust_workers_for_memory()
        
        logger.info(f"Starting {self.task_name}: {len(valid_items)} items with {actual_workers} workers")
        
        # Use monitoring context
        with ProcessingContext(self.task_name, self.config.heartbeat_interval) as monitor:
            return self._process_with_monitoring(valid_items, monitor, start_time)
    
    def _process_with_monitoring(self, items: List[T], monitor, start_time: float) -> TaskResult:
        """Process items with monitoring and error handling."""
        batches = self._create_batches(items)
        results = []
        processed_count = 0
        failed_count = 0
        consecutive_failures = 0
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._process_batch, batch, batch_index): batch_index
                for batch_index, batch in enumerate(batches)
            }
            
            try:
                for future in as_completed(futures, timeout=self.config.timeout_total):
                    batch_index = futures[future]
                    try:
                        batch_result = future.result(timeout=self.config.timeout_per_item)
                        results.extend(batch_result)
                        processed_count += len(batch_result)
                        consecutive_failures = 0  # Reset on success
                        
                        # Update monitoring
                        monitor.update_activity(processed=len(batch_result), failed=0)
                        
                        # Check memory periodically
                        if processed_count % (self.config.progress_log_interval * 2) == 0:
                            if not self._check_memory_usage():
                                logger.warning("Memory usage high during processing")
                        
                        # Log progress
                        if batch_index % 5 == 0:
                            logger.info(f"Completed batch {batch_index + 1}/{len(batches)}")
                            
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_index}: {str(e)}")
                        failed_count += self.config.batch_size
                        consecutive_failures += 1
                        monitor.update_activity(processed=0, failed=self.config.batch_size)
                        
                        # Circuit breaker
                        if consecutive_failures >= self.config.max_consecutive_failures:
                            logger.error(f"Circuit breaker triggered: {consecutive_failures} consecutive failures")
                            self._cancel_remaining_futures(futures)
                            break
                            
            except Exception as e:
                logger.error(f"Critical error in task processing: {str(e)}")
                self._cancel_remaining_futures(futures)
        
        total_time = time.time() - start_time
        success_rate = (processed_count / len(items)) * 100 if items else 0
        
        logger.info(f"Task {self.task_name} completed: {processed_count} processed, "
                   f"{failed_count} failed ({success_rate:.1f}% success) in {total_time:.2f}s")
        
        return TaskResult(
            success=consecutive_failures < self.config.max_consecutive_failures,
            processed_count=processed_count,
            failed_count=failed_count,
            total_time=total_time
        )
    
    def _create_batches(self, items: List[T]) -> List[List[T]]:
        """Create batches from items."""
        batches = []
        for i in range(0, len(items), self.config.batch_size):
            batches.append(items[i:i + self.config.batch_size])
        return batches
    
    def _process_batch(self, batch: List[T], batch_index: int) -> List[R]:
        """Process a single batch of items."""
        batch_results = []
        
        for item_index, item in enumerate(batch):
            try:
                result = self.process_single_item(item, item_index)
                batch_results.append(result)
            except Exception as e:
                logger.error(f"Error processing item {item_index} in batch {batch_index}: {str(e)}")
                # Continue processing other items in the batch
                continue
        
        return batch_results
    
    def _cancel_remaining_futures(self, futures: Dict) -> None:
        """Cancel remaining futures when circuit breaker is triggered."""
        for future in futures:
            if not future.done():
                future.cancel()
                try:
                    future.result(timeout=1)
                except Exception:
                    pass  # Expected for cancelled futures


class DocumentProcessingMixin(TaskProcessingMixin[T, R]):
    """
    Specialized mixin for document processing tasks.
    
    Provides additional document-specific functionality like:
    - Document validation
    - Metadata handling
    - Chunk processing
    """
    
    def validate_item(self, item: T) -> bool:
        """Validate a document item."""
        if hasattr(item, 'page_content'):
            return bool(item.page_content and isinstance(item.page_content, str))
        elif isinstance(item, str):
            return bool(item.strip())
        return False
    
    def process_documents_with_metadata(self, documents: List[T], metadatas: List[Dict]) -> TaskResult:
        """
        Process documents with their metadata.
        
        Args:
            documents: List of documents to process
            metadatas: List of metadata dictionaries
            
        Returns:
            TaskResult with processing statistics
        """
        if len(documents) != len(metadatas):
            raise ValueError("Documents and metadatas must have the same length")
        
        # Create document-metadata pairs
        items = list(zip(documents, metadatas))
        return self.process_items(items)
    
    def process_texts_with_metadata(self, texts: List[str], metadatas: List[Dict]) -> TaskResult:
        """
        Process text strings with their metadata.
        
        Args:
            texts: List of text strings to process
            metadatas: List of metadata dictionaries
            
        Returns:
            TaskResult with processing statistics
        """
        if len(texts) != len(metadatas):
            raise ValueError("Texts and metadatas must have the same length")
        
        # Create text-metadata pairs
        items = list(zip(texts, metadatas))
        return self.process_items(items)
