
import logging
from pathlib import Path
from loguru import logger
import re

# Cache pour éviter de reconfigurer le logger plusieurs fois
_logger_cache = {}


def get_logger(name):
    """Legacy function for backward compatibility"""
    return logging.getLogger("django_app_rag." + name)


def get_logger_loguru(name: str = None, name_file: str = None):
    """
    Get a loguru logger with automatic file logging based on module name.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        loguru logger instance
    """
    if name is None:
        name = "django_app_rag"
    
    # Vérifier le cache pour éviter de reconfigurer
    if name in _logger_cache:
        return _logger_cache[name]
    
    # Create logs directory if it doesn't exist
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log file name based on module name

    log_file = log_dir / (name_file if name_file else "rag.log")

    
    # Remove existing handlers to avoid duplicates
    logger.remove()
    
    # Check if this is a task logger
    is_task_logger = "task" in name.lower()
    
    if is_task_logger:
        # Special formatting for task logs with SUB distinction only
        def task_formatter(record):
            message = record["message"]
            
            # Escape any HTML-like tags in the message to prevent Loguru color parsing errors
            import re
            escaped_message = re.sub(r'<([^>]+)>', r'\\<\1\\>', message)
            
            # Check if message contains SUB prefix
            if "[SUB-" in message:
                # Subprocess logs - yellow color
                formatted_msg = f"<yellow>{escaped_message}</yellow>"
            else:
                # Regular logs (main process)
                formatted_msg = escaped_message
                
            return f"<green>{record['time']:YYYY-MM-DD HH:mm:ss}</green> | <level>{record['level'].name: <8}</level> | <cyan>{record['name']}</cyan>:<cyan>{record['function']}</cyan>:<cyan>{record['line']}</cyan> - {formatted_msg}\n"
        
        # Add console handler with task-specific formatting
        logger.add(
            sink=lambda msg: print(msg, end=""),
            format=task_formatter,
            level="INFO"
        )
        
        # Add file handler with clean formatting (no colors in file)
        logger.add(
            sink=str(log_file),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip"
        )
    else:
        # Standard formatting for non-task loggers
        # Add console handler
        logger.add(
            sink=lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
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
    
    # Mettre en cache le logger configuré
    _logger_cache[name] = logger
    return logger


def clean_ansi_codes(text: str) -> str:
    """
    Supprime les codes de couleur ANSI d'une chaîne de caractères.
    
    Args:
        text: Texte contenant potentiellement des codes ANSI
        
    Returns:
        Texte nettoyé sans codes ANSI
    """
    # Pattern pour supprimer les codes ANSI (CSI sequences)
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*[mGKHF]')
    return ansi_pattern.sub('', text)

def get_subprocess_logger(process_name: str):
    """
    Get a loguru logger specifically for a subprocess with its own log file.
    Automatically cleans ANSI codes from messages.
    
    Args:
        process_name: Name of the subprocess (e.g., 'retrieve', 'etl', 'index')
        
    Returns:
        tuple: (loguru logger instance, log file path)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("log/subprocesses")
    log_dir.mkdir(exist_ok=True)
    
    # Create subprocess-specific log file
    log_file = log_dir / f"{process_name.lower()}.log"
    
    # Create a new logger instance for this subprocess
    from loguru import logger as loguru_logger
    subprocess_logger = loguru_logger.bind(subprocess=process_name)
    
    # Remove existing handlers to avoid duplicates
    subprocess_logger.remove()
    
    # Custom sink function that automatically cleans ANSI codes
    def clean_ansi_sink(message):
        # Extract the message part and clean ANSI codes
        clean_message = clean_ansi_codes(message)
        print(clean_message, end="")
    
    # Add console handler with subprocess formatting and ANSI cleaning
    subprocess_logger.add(
        sink=clean_ansi_sink,
        format=f"<green>{{time:YYYY-MM-DD HH:mm:ss}}</green> | <level>{{level: <8}}</level> | <yellow>[SUB-{process_name.upper():<10}]</yellow> | <level>{{message}}</level>",
        level="INFO"
    )
    
    # Custom file sink with rotation support and ANSI cleaning
    from loguru._file_sink import FileSink
    
    class CleanAnsiFileSink(FileSink):
        def write(self, message):
            # Clean ANSI codes before writing
            clean_message = clean_ansi_codes(message)
            super().write(clean_message)
    
    # Add file handler for subprocess-specific log file with ANSI cleaning
    subprocess_logger.add(
        sink=CleanAnsiFileSink(str(log_file), rotation="10 MB", retention="7 days", compression="zip"),
        format=f"{{time:YYYY-MM-DD HH:mm:ss}} | {{level: <8}} | [SUB-{process_name.upper():<10}] | {{message}}",
        level="DEBUG"
    )
    
    return subprocess_logger, str(log_file)