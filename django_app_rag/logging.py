
import logging
from pathlib import Path
from loguru import logger
import os


def get_logger(name):
    """Legacy function for backward compatibility"""
    return logging.getLogger("django_app_rag." + name)


def get_logger_loguru(name: str = None):
    """
    Get a loguru logger with automatic file logging based on module name.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        loguru logger instance
    """
    if name is None:
        name = "django_app_rag"
    
    # Create logs directory if it doesn't exist
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log file name based on module name
    if "step" in name.lower():
        log_file = log_dir / "steps.log"
    elif "pipeline" in name.lower():
        log_file = log_dir / "pipelines.log"
    elif "task" in name.lower():
        log_file = log_dir / "tasks.log"
    elif "rag" in name.lower():
        log_file = log_dir / "rag.log"
    else:
        log_file = log_dir / "general.log"
    
    # Remove existing handlers to avoid duplicates
    logger.remove()
    
    # Add console handler
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Add file handler
    logger.add(
        sink=str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    return logger