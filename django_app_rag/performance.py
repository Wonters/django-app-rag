"""
Configuration des paramètres de performance pour le RAG.

Ce module centralise tous les paramètres de performance configurables
pour optimiser l'utilisation des ressources selon l'infrastructure disponible.
"""

from pydantic_settings import BaseSettings
from typing import Literal
import multiprocessing


class PerformanceConfig(BaseSettings):
    """
    Configuration des paramètres de performance.

    Tous les paramètres sont configurables via variables d'environnement
    avec le préfixe RAG_PERF_
    """

    # === Workers Configuration ===

    # Number of workers for data collection (crawling, notion, file extraction)
    collection_workers: int = min(10, multiprocessing.cpu_count() * 2)

    # Number of processes for Dramatiq task processing
    dramatiq_processes: int = min(2, multiprocessing.cpu_count())

    # Number of threads per Dramatiq process
    dramatiq_threads: int = 4

    # Number of workers for embedding batch processing
    embedding_workers: int = min(2, multiprocessing.cpu_count())

    # === Batch Processing ===

    # Batch size for document processing
    document_batch_size: int = 100

    # Batch size for embedding generation
    embedding_batch_size: int = 32

    # Batch size for database bulk operations
    db_bulk_size: int = 500

    # === Pagination ===

    # Default page size for API endpoints
    api_page_size: int = 50

    # Maximum page size allowed for API endpoints
    api_max_page_size: int = 500

    # Page size for internal document iteration
    document_page_size: int = 1000

    # === Timeouts ===

    # Timeout for single document crawling (seconds)
    crawl_timeout: int = 30

    # Timeout for RAG task processing (seconds)
    rag_task_timeout: int = 600  # 10 minutes

    # Timeout for indexing task (seconds)
    indexing_timeout: int = 3600  # 1 hour

    # === Cache Configuration ===

    # Cache TTL for retriever results (seconds)
    retriever_cache_ttl: int = 3600  # 1 hour

    # Cache TTL for document text (seconds)
    document_cache_ttl: int = 7200  # 2 hours

    # Maximum cache size in MB
    max_cache_size_mb: int = 1024  # 1 GB

    # === Resource Limits ===

    # Maximum memory per worker (MB)
    max_worker_memory_mb: int = 2048  # 2 GB

    # Maximum concurrent tasks
    max_concurrent_tasks: int = 10

    # Maximum documents per collection
    max_documents_per_collection: int = 100000

    # === Device Configuration ===

    # Device for embedding models (cpu, cuda, mps)
    device: Literal["cpu", "cuda", "mps"] = "cpu"

    # Enable mixed precision for faster inference (requires CUDA)
    enable_fp16: bool = False

    # === Optimization Flags ===

    # Enable query result caching
    enable_query_cache: bool = True

    # Enable document deduplication
    enable_deduplication: bool = True

    # Enable incremental indexing (append mode)
    enable_incremental_indexing: bool = True

    # Enable parallel processing where possible
    enable_parallel_processing: bool = True

    class Config:
        env_prefix = "RAG_PERF_"
        case_sensitive = False


# Global instance
performance_config = PerformanceConfig()


def get_optimal_workers(task_type: str = "default") -> int:
    """
    Get optimal number of workers based on task type and available resources.

    Args:
        task_type: Type of task (collection, embedding, dramatiq)

    Returns:
        Optimal number of workers for the task
    """
    if task_type == "collection":
        return performance_config.collection_workers
    elif task_type == "embedding":
        return performance_config.embedding_workers
    elif task_type == "dramatiq":
        return performance_config.dramatiq_processes
    else:
        return min(4, multiprocessing.cpu_count())


def get_optimal_batch_size(task_type: str = "default") -> int:
    """
    Get optimal batch size based on task type.

    Args:
        task_type: Type of task (document, embedding, db)

    Returns:
        Optimal batch size for the task
    """
    if task_type == "document":
        return performance_config.document_batch_size
    elif task_type == "embedding":
        return performance_config.embedding_batch_size
    elif task_type == "db":
        return performance_config.db_bulk_size
    else:
        return 100


def should_use_gpu() -> bool:
    """Check if GPU should be used for processing."""
    return performance_config.device in ["cuda", "mps"]


def get_recommended_config():
    """
    Get recommended performance configuration based on system resources.

    Returns:
        dict: Recommended configuration parameters
    """
    cpu_count = multiprocessing.cpu_count()

    try:
        import psutil
        mem_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        mem_gb = 8  # Default assumption

    # Adjust based on available resources
    if mem_gb < 4:
        # Low memory system
        config = {
            "collection_workers": 2,
            "dramatiq_processes": 1,
            "embedding_batch_size": 16,
            "document_batch_size": 50,
        }
    elif mem_gb < 8:
        # Medium memory system
        config = {
            "collection_workers": min(5, cpu_count),
            "dramatiq_processes": min(2, cpu_count),
            "embedding_batch_size": 32,
            "document_batch_size": 100,
        }
    else:
        # High memory system
        config = {
            "collection_workers": min(10, cpu_count * 2),
            "dramatiq_processes": min(4, cpu_count),
            "embedding_batch_size": 64,
            "document_batch_size": 200,
        }

    return config
