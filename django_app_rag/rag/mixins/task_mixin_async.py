import asyncio
import os
import psutil
from typing import Any, Callable, Generic, TypeVar
from django_app_rag.logging import get_logger_loguru

logger = get_logger_loguru(__name__)

T = TypeVar('T')


class TaskMixinAsync(Generic[T]):
    """Mixin pour la gestion robuste des tâches asynchrones.
    
    Ce mixin fournit une interface standardisée pour le traitement par lots
    de documents avec gestion des timeouts, cancellation, monitoring et retry.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_tasks = set()  # Track active tasks for monitoring

    def _cleanup_completed_tasks(self) -> None:
        """Remove completed tasks from the active tasks set."""
        completed_tasks = {task for task in self._active_tasks if task.done()}
        self._active_tasks -= completed_tasks
        if completed_tasks:
            logger.debug(f"Cleaned up {len(completed_tasks)} completed tasks")

    def _get_active_task_count(self) -> int:
        """Get the number of currently active tasks."""
        self._cleanup_completed_tasks()
        return len(self._active_tasks)

    async def process_batch_async(
        self,
        items: list[T],
        process_item_func: Callable[[T, asyncio.Semaphore, int], Any],
        await_time_seconds: int = 2,
        batch_name: str = "Processing",
        success_condition: Callable[[T], bool] = None,
    ) -> list[Any]:
        """Process a batch of items asynchronously with robust error handling.

        Args:
            items: List of items to process
            process_item_func: Function to process each item (item, semaphore, await_time_seconds) -> result
            await_time_seconds: Time to wait between requests
            batch_name: Name for logging purposes
            success_condition: Function to check if an item was successfully processed

        Returns:
            list[Any]: Results of processing each item
        """
        logger.info(f"Starting {batch_name} of {len(items)} items with {self.max_concurrent_requests} concurrent requests")
        logger.info(f"Await time between requests: {await_time_seconds} seconds")
        
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Create tasks using asyncio.create_task for better control
        tasks = []
        for item in items:
            task = asyncio.create_task(
                process_item_func(item, semaphore, await_time_seconds)
            )
            tasks.append(task)
            self._active_tasks.add(task)
        
        logger.debug(f"Created {len(tasks)} tasks for {batch_name}")
        
        # Set up timeout for the entire batch (30 seconds per item max)
        batch_timeout = len(items) * 30  # 30 seconds per item max
        if batch_timeout > 1800:  # Cap at 30 minutes
            batch_timeout = 1800
        
        results = []
        completed_count = 0
        failed_count = 0
        
        try:
            # Use asyncio.wait with timeout for better control
            done, pending = await asyncio.wait(
                tasks,
                timeout=batch_timeout,
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Log active task count periodically
            active_count = self._get_active_task_count()
            if active_count > 0:
                logger.debug(f"Active tasks remaining: {active_count}")
            
            # Process completed tasks
            for task in done:
                try:
                    result = await task
                    results.append(result)
                    completed_count += 1
                    
                    # Log progress every 50 items
                    if completed_count % 50 == 0:
                        logger.info(f"Processed {completed_count}/{len(items)} items")
                        
                except Exception as e:
                    logger.error(f"Error processing item in batch: {str(e)}")
                    failed_count += 1
                    results.append(None)
            
            # Handle pending tasks (timeout reached)
            if pending:
                logger.warning(f"Batch timeout reached, cancelling {len(pending)} pending tasks")
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.debug("Task cancelled successfully")
                    except Exception as e:
                        logger.error(f"Error cancelling task: {str(e)}")
                    failed_count += 1
                    results.append(None)
                    
        except Exception as e:
            logger.error(f"Critical error in batch processing: {str(e)}")
            # Cancel all remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            failed_count = len(items) - completed_count
            # Fill remaining results with None
            while len(results) < len(items):
                results.append(None)

        # Clean up completed tasks
        self._cleanup_completed_tasks()
        
        logger.info(f"{batch_name} completed: {completed_count} succeeded, {failed_count} failed")
        return results

    async def process_with_retry(
        self,
        items: list[T],
        process_item_func: Callable[[T, asyncio.Semaphore, int], Any],
        success_condition: Callable[[T], bool],
        initial_await_time: int = 7,
        retry_await_time: int = 20,
        batch_name: str = "Processing",
    ) -> list[Any]:
        """Process items with intelligent retry mechanism.

        Args:
            items: List of items to process
            process_item_func: Function to process each item
            success_condition: Function to check if an item was successfully processed
            initial_await_time: Initial await time between requests
            retry_await_time: Await time for retry attempts
            batch_name: Name for logging purposes

        Returns:
            list[Any]: Results of processing each item
        """
        # First attempt
        results = await self.process_batch_async(
            items=items,
            process_item_func=process_item_func,
            await_time_seconds=initial_await_time,
            batch_name=f"{batch_name} (initial)",
            success_condition=success_condition,
        )

        # Separate successful and failed items
        successful_items = [
            result for result in results 
            if result is not None and success_condition(result)
        ]
        failed_items = [
            item for item, result in zip(items, results)
            if result is None or not success_condition(result)
        ]

        # Retry failed items with increased await time
        if failed_items:
            logger.info(
                f"Retrying {len(failed_items)} failed items with increased await time..."
            )
            retry_results = await self.process_batch_async(
                items=failed_items,
                process_item_func=process_item_func,
                await_time_seconds=retry_await_time,
                batch_name=f"{batch_name} (retry)",
                success_condition=success_condition,
            )

            # Only add successfully processed items from retry
            successful_retry_results = [
                result for result in retry_results 
                if result is not None and success_condition(result)
            ]
            successful_items += successful_retry_results
            
            # Log retry results
            retry_success_count = len(successful_retry_results)
            retry_failed_count = len(failed_items) - retry_success_count
            logger.info(
                f"Retry completed: {retry_success_count} succeeded, {retry_failed_count} still failed"
            )

        return successful_items

    def get_memory_usage(self) -> dict[str, int]:
        """Get current memory usage information.
        
        Returns:
            dict: Memory usage information in MB
        """
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss // (1024 * 1024),  # Resident Set Size in MB
            "vms": memory_info.vms // (1024 * 1024),  # Virtual Memory Size in MB
        }
