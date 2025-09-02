import logging
import os
import threading
from pathlib import Path
from django.conf import settings

# Variable globale pour tracker si le logging a déjà été configuré
_rag_logging_configured = False
_logging_lock = threading.Lock()


class ThreadSafeFileHandler(logging.FileHandler):
    """
    Thread-safe file handler that uses a lock to prevent concurrent access issues.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
    
    def emit(self, record):
        """
        Emit a record with thread safety.
        """
        try:
            with self._lock:
                super().emit(record)
        except Exception:
            self.handleError(record)

def setup_rag_logging(log_level: str = "INFO", log_dir: str = None):
    """
    Configure le logging Django pour le module RAG avec des options personnalisables
    
    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Répertoire de logs personnalisé (optionnel)
    """
    global _rag_logging_configured
    
    # Utiliser un lock pour éviter les problèmes de concurrence
    with _logging_lock:
        # Vérifier si le logging a déjà été configuré
        if _rag_logging_configured:
            logger = logging.getLogger('django_app_rag.rag')
            logger.debug("RAG logging already configured, skipping setup")
            return logger
    
    # Détermine le répertoire de logs
    if log_dir is None:
        # Utilise le répertoire de travail actuel ou le répertoire parent si on est dans django-app-rag
        current_dir = Path.cwd()
        if current_dir.name == "django-app-rag":
            # Si on est dans django-app-rag, remonte d'un niveau
            log_dir = current_dir.parent / "log" / "zenml"
        else:
            # Sinon utilise le répertoire de travail actuel
            log_dir = current_dir / "log" / "zenml"
    else:
        log_dir = Path(log_dir)
    
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        # Si on ne peut pas créer le répertoire, utiliser un répertoire temporaire
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / "rag_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        print(f"Warning: Could not create log directory, using temporary directory: {log_dir}")
    
    # Configuration du logger RAG principal
    logger = logging.getLogger('django_app_rag.rag')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Configuration pour tous les loggers RAG (propagation vers le parent)
    rag_logger = logging.getLogger('django_app_rag.rag')
    rag_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Éviter la duplication des handlers
    if not rag_logger.handlers:
        # Handler pour la console - thread-safe
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Format pour la console
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        rag_logger.addHandler(console_handler)
        
        # Handler pour le fichier principal - thread-safe
        log_file = log_dir / "rag_pipeline.log"
        file_handler = ThreadSafeFileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Format pour le fichier
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        rag_logger.addHandler(file_handler)
        
        # Handler pour les erreurs - thread-safe
        error_log_file = log_dir / "rag_errors.log"
        error_handler = ThreadSafeFileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        rag_logger.addHandler(error_handler)
    
    # Garder la propagation activée pour que tous les loggers RAG enfants utilisent cette configuration
    rag_logger.propagate = True
    
    # Marquer le logging comme configuré
    _rag_logging_configured = True
    
    logger.info(f"RAG logging setup completed. Log level: {log_level}, Log directory: {log_dir}")
    return logger

# Configuration initiale - ne s'exécutera qu'une seule fois
setup_rag_logging()

def get_logger(name: str = None):
    """
    Retourne un logger configuré pour le module RAG
    
    Args:
        name: Nom du module (optionnel)
    
    Returns:
        Logger configuré
    """
    if name:
        logger = logging.getLogger(name)
        # Si c'est un logger RAG, s'assurer qu'il hérite de la configuration
        if name.startswith('django_app_rag.rag'):
            # Le logger parent est déjà configuré, donc les enfants héritent automatiquement
            pass
        return logger
    return logging.getLogger('django_app_rag.rag')


def get_thread_safe_logger(name: str = None):
    """
    Retourne un logger thread-safe configuré pour le module RAG
    
    Args:
        name: Nom du module (optionnel)
    
    Returns:
        ThreadSafeLogger configuré
    """
    from .thread_safe_logger import ThreadSafeLogger
    
    if name:
        logger = logging.getLogger(name)
        # Si c'est un logger RAG, s'assurer qu'il hérite de la configuration
        if name.startswith('django_app_rag.rag'):
            # Le logger parent est déjà configuré, donc les enfants héritent automatiquement
            pass
        return ThreadSafeLogger(logger)
    return ThreadSafeLogger(logging.getLogger('django_app_rag.rag'))

def is_rag_logging_configured():
    """
    Vérifie si le logging RAG a déjà été configuré
    
    Returns:
        bool: True si le logging est configuré, False sinon
    """
    return _rag_logging_configured
