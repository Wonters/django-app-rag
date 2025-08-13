from django.conf import settings
from pathlib import Path

class AppRAGConfig:
    """
    Configuration centrale pour l'application django_app_rag.
    Modifiez ici les paramètres globaux de l'app.
    """
    def __init__(self, prefix):
        self.prefix = prefix

    def _setting(self, name, dflt):
        """
        Get a setting from django.conf.settings, falling back to the default.
        If the default is not given, uses the setting from django.conf.global_settings.
        """
        from django.conf import settings
        return getattr(settings, self.prefix + name, dflt)

    @property
    def rag_data_dir(self):
        return self._setting('RAG_DATA_DIR', settings.MEDIA_ROOT / "rag_data")
    
    @property
    def frontend_dev_server(self):
        return self._setting('FRONTEND_DEV_SERVER', 'http://localhost:5173')
    
    @property
    def frontend_prod_path(self):
        return self._setting('FRONTEND_PROD_PATH', '/static/dist/main.js')
    
    @property
    def enable_rag_features(self):
        return self._setting('ENABLE_RAG_FEATURES', True)
    
    @property
    def templates_dir(self):
        """Base templates directory for django-app-rag"""
        return self._setting('APP_RAG_TEMPLATES_DIR', 
                           Path(settings.BASE_DIR) / "django-app-rag/django_app_rag/templates")
    
    
    @property
    def template_dirs(self):
        """List of all template directories for django-app-rag"""
        return [
            self.templates_dir,
        ]
    @property
    def templates(self):
        return self._setting('TEMPLATES', {
            'main_rag': 'django_app_rag/main_rag.html',
        })


# Instance globale (pattern classique)
app_rag_config = AppRAGConfig('APP_RAG_') 