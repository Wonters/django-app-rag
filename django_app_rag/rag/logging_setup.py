import logging
import os
from pathlib import Path
from django.conf import settings

# Variable globale pour tracker si le logging a déjà été configuré
_rag_logging_configured = False

def setup_rag_logging(log_level: str = "INFO", log_dir: str = None):
    """
    Configure le logging Django pour le module RAG avec des options personnalisables
    
    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Répertoire de logs personnalisé (optionnel)
    """
    global _rag_logging_configured
    
    # Vérifier si le logging a déjà été configuré
    if _rag_logging_configured:
        logger = logging.getLogger('django_app_rag.rag')
        logger.debug("RAG logging already configured, skipping setup")
        return logger
    
    # Détermine le répertoire de logs
    if log_dir is None:
        # Utilise le répertoire de travail actuel
        log_dir = Path.cwd() / "log" / "zenml"
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(exist_ok=True)
    
    # Configuration du logger RAG
    logger = logging.getLogger('django_app_rag.rag')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Éviter la duplication des handlers
    if not logger.handlers:
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Format pour la console
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Handler pour le fichier principal
        log_file = log_dir / "rag_pipeline.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Format pour le fichier
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Handler pour les erreurs
        error_log_file = log_dir / "rag_errors.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
    
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
        return logging.getLogger(name)
    return logging.getLogger('django_app_rag.rag')

def is_rag_logging_configured():
    """
    Vérifie si le logging RAG a déjà été configuré
    
    Returns:
        bool: True si le logging est configuré, False sinon
    """
    return _rag_logging_configured
