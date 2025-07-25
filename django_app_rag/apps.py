from django.apps import AppConfig

    
class RAGAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_app_rag'

    def ready(self):
        pass
