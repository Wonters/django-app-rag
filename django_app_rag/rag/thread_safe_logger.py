"""
Thread-safe logger wrapper to prevent logging lock issues in multi-threaded environments.
"""

import logging
import threading
from typing import Any, Optional


class ThreadSafeLogger:
    """
    A thread-safe wrapper around Python's logging.Logger that prevents
    lock acquisition issues in multi-threaded environments.
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._lock = threading.Lock()
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Thread-safe debug logging."""
        try:
            with self._lock:
                self._logger.debug(msg, *args, **kwargs)
        except Exception:
            # Fallback to print if logging fails
            print(f"DEBUG: {msg % args if args else msg}")
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """Thread-safe info logging."""
        try:
            with self._lock:
                self._logger.info(msg, *args, **kwargs)
        except Exception:
            # Fallback to print if logging fails
            print(f"INFO: {msg % args if args else msg}")
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Thread-safe warning logging."""
        try:
            with self._lock:
                self._logger.warning(msg, *args, **kwargs)
        except Exception:
            # Fallback to print if logging fails
            print(f"WARNING: {msg % args if args else msg}")
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """Thread-safe error logging."""
        try:
            with self._lock:
                self._logger.error(msg, *args, **kwargs)
        except Exception:
            # Fallback to print if logging fails
            print(f"ERROR: {msg % args if args else msg}")
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """Thread-safe critical logging."""
        try:
            with self._lock:
                self._logger.critical(msg, *args, **kwargs)
        except Exception:
            # Fallback to print if logging fails
            print(f"CRITICAL: {msg % args if args else msg}")
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """Thread-safe exception logging."""
        try:
            with self._lock:
                self._logger.exception(msg, *args, **kwargs)
        except Exception:
            # Fallback to print if logging fails
            print(f"EXCEPTION: {msg % args if args else msg}")


def get_thread_safe_logger(name: str) -> ThreadSafeLogger:
    """
    Get a thread-safe logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        ThreadSafeLogger instance
    """
    logger = logging.getLogger(name)
    return ThreadSafeLogger(logger)
