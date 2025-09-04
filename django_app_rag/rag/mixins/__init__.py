"""
Mixin classes for robust task processing.

This module provides mixins that encapsulate common patterns for:
- Parallel task processing with error handling
- Circuit breaker patterns
- Memory monitoring
- Progress tracking
- Timeout management
"""

from .task_processing_mixin import (
    TaskProcessingMixin,
    DocumentProcessingMixin,
    TaskConfig,
    TaskResult,
)
from .task_mixin_async import TaskMixinAsync

__all__ = [
    "TaskProcessingMixin",
    "DocumentProcessingMixin", 
    "TaskConfig",
    "TaskResult",
    "TaskMixinAsync",
]
