import time
import threading
import psutil
from typing import Dict, Any, Optional
from dataclasses import dataclass
from django_app_rag.logging import get_logger_loguru

logger = get_logger_loguru(__name__, "processing_monitor.log")


@dataclass
class ProcessingStats:
    """Statistics for processing monitoring."""
    start_time: float
    processed_items: int = 0
    failed_items: int = 0
    last_activity_time: float = 0
    memory_usage_mb: float = 0
    cpu_usage_percent: float = 0
    active_threads: int = 0


class ProcessingMonitor:
    """Monitor for processing tasks with heartbeat and resource monitoring."""
    
    def __init__(self, task_name: str, heartbeat_interval: int = 30):
        """
        Initialize the processing monitor.
        
        Args:
            task_name: Name of the task being monitored
            heartbeat_interval: Interval in seconds for heartbeat logging
        """
        self.task_name = task_name
        self.heartbeat_interval = heartbeat_interval
        self.stats = ProcessingStats(start_time=time.time())
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
    def start_monitoring(self) -> None:
        """Start the monitoring thread."""
        if self._monitoring:
            return
            
        self._monitoring = True
        self.stats.start_time = time.time()
        self.stats.last_activity_time = time.time()
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name=f"Monitor-{self.task_name}"
        )
        self._monitor_thread.start()
        
        logger.info(f"Started monitoring for task: {self.task_name}")
    
    def stop_monitoring(self) -> None:
        """Stop the monitoring thread."""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        total_time = time.time() - self.stats.start_time
        logger.info(f"Stopped monitoring for task: {self.task_name}. "
                   f"Total time: {total_time:.2f}s, "
                   f"Processed: {self.stats.processed_items}, "
                   f"Failed: {self.stats.failed_items}")
    
    def update_activity(self, processed: int = 0, failed: int = 0) -> None:
        """Update activity statistics."""
        with self._lock:
            self.stats.processed_items += processed
            self.stats.failed_items += failed
            self.stats.last_activity_time = time.time()
    
    def is_stuck(self, timeout_seconds: int = 300) -> bool:
        """
        Check if the task appears to be stuck.
        
        Args:
            timeout_seconds: Timeout in seconds to consider task stuck
            
        Returns:
            True if task appears to be stuck
        """
        with self._lock:
            time_since_activity = time.time() - self.stats.last_activity_time
            return time_since_activity > timeout_seconds
    
    def get_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        with self._lock:
            return ProcessingStats(
                start_time=self.stats.start_time,
                processed_items=self.stats.processed_items,
                failed_items=self.stats.failed_items,
                last_activity_time=self.stats.last_activity_time,
                memory_usage_mb=self.stats.memory_usage_mb,
                cpu_usage_percent=self.stats.cpu_usage_percent,
                active_threads=self.stats.active_threads
            )
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                # Update resource usage
                process = psutil.Process()
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                with self._lock:
                    self.stats.memory_usage_mb = memory_info.rss / 1024 / 1024
                    self.stats.cpu_usage_percent = cpu_percent
                    self.stats.active_threads = process.num_threads()
                
                # Check if stuck
                if self.is_stuck():
                    logger.warning(f"Task {self.task_name} appears to be stuck - "
                                 f"no activity for {time.time() - self.stats.last_activity_time:.0f}s")
                
                # Log heartbeat
                total_time = time.time() - self.stats.start_time
                logger.info(f"Heartbeat [{self.task_name}]: "
                           f"Time: {total_time:.0f}s, "
                           f"Processed: {self.stats.processed_items}, "
                           f"Failed: {self.stats.failed_items}, "
                           f"Memory: {self.stats.memory_usage_mb:.1f}MB, "
                           f"CPU: {self.stats.cpu_usage_percent:.1f}%, "
                           f"Threads: {self.stats.active_threads}")
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop for {self.task_name}: {str(e)}")
                time.sleep(self.heartbeat_interval)


class ProcessingContext:
    """Context manager for processing monitoring."""
    
    def __init__(self, task_name: str, heartbeat_interval: int = 30):
        self.monitor = ProcessingMonitor(task_name, heartbeat_interval)
    
    def __enter__(self) -> ProcessingMonitor:
        self.monitor.start_monitoring()
        return self.monitor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor.stop_monitoring()
