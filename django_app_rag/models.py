from django.db import models
from django.core.files.base import ContentFile
from pathlib import Path
import os
import yaml
from pathlib import Path
from django_app_rag.logging import get_logger
from django.conf import settings
logger = get_logger(__name__)

def rag_config_upload_path(instance, filename):
    """
    Callback pour organiser les fichiers de configuration RAG dans des dossiers
    basés sur le titre et l'ID de la collection
    """
    collection = instance.collection
    folder_name = f"{collection.title.replace(' ', '_')}_{collection.id}"
    return f"rag_configs/{folder_name}/{filename}"


class Source(models.Model):
    NOTION = 'notion'
    URL = 'url'
    FILE = 'file'
    SOURCE_TYPE_CHOICES = [
        (NOTION, 'Notion'),
        (URL, 'URL'),
        (FILE, 'File'),
    ]
    type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    link = models.URLField(blank=True, null=True)
    notion_db_ids = models.TextField(blank=True, null=True, help_text="Liste des IDs de bases Notion, séparés par des virgules")
    file = models.FileField(upload_to='rag_sources/', blank=True, null=True)
    collection = models.ForeignKey("Collection", on_delete=models.CASCADE, related_name='sources')

    def __str__(self):
        if self.type == Source.NOTION:
            return f"{self.title} ({self.type}: {self.notion_db_ids})"
        elif self.type == Source.URL:
            return f"{self.title} ({self.type}: {self.link})"
        elif self.type == Source.FILE:
            return f"{self.title} ({self.type}: {self.file.name})"
        else:
            return f"{self.title} ({self.type})"


class Question(models.Model):
    title = models.CharField(max_length=255)
    field = models.TextField(blank=True, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='questions')

    def __str__(self):
        return self.title

class Answer(models.Model):
    title = models.CharField(max_length=255)
    field = models.TextField(blank=True, null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', null=True, blank=True)

    def __str__(self):
        return self.title

class Collection(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.title} - sources: {self.sources.count()}"
    
    def create_rag_config(self, title: str, config_path: Path, **kwargs):
        config = yaml.safe_load(config_path.read_text())
        config["collection_name"] = f"{self.title.replace(' ', '_')}_{self.id}"
        rag_data_dir = settings.MEDIA_ROOT / "rag_data" / f"{self.id}"
        rag_data_dir.mkdir(parents=True, exist_ok=True)
        config["data_dir"] = rag_data_dir.as_posix()
        config.update(kwargs)
        config_content = yaml.dump(config, default_flow_style=False)
        config_file = RagConfig(title=title, collection=self, config_file=ContentFile(config_content.encode('utf-8'), name=f"{title}.yaml"))
        config_file.save()
        logger.info(f"Configuration RAG été créée pour la collection {self.title}")
        return config_file.config_file.path
    
    def rag_retrieve_config(self):
        # Récupérer les valeurs actuelles des sources
        current_file_paths = list(self.sources.filter(type=Source.FILE).values_list('file', flat=True))
        current_urls = list(self.sources.filter(type=Source.URL).values_list('link', flat=True))
        current_notion_db_ids = list(self.sources.filter(type=Source.NOTION).values_list('notion_db_ids', flat=True))
        config_template = Path(__file__).parent / "rag" / "config" / "collect_data.yaml"

        if self.rag_configs.filter(title="retrieve").exists():
            rag_config = self.rag_configs.get(title="retrieve")
            config_file = rag_config.config_file
            with open(config_file.path, 'r') as f:
                config = yaml.safe_load(f)
            # Vérifier si la config est à jour
            config_file_paths = config.get('file_paths', [])
            config_urls = config.get('urls', [])
            config_notion_db_ids = config.get('notion_database_ids', [])
            # Comparer les listes (en ignorant l'ordre)
            if (set(current_file_paths) != set(config_file_paths) or
                set(current_urls) != set(config_urls) or
                set(current_notion_db_ids) != set(config_notion_db_ids)):
                # Si la config n'est pas à jour, la recréer
                rag_config.delete()
                return self.create_rag_config(
                    title="retrieve",
                    config_path=config_template,
                    file_paths=current_file_paths,
                    urls=current_urls,
                    notion_database_ids=current_notion_db_ids
                )
            else:
                # Config à jour
                return config_file.path
        else:
            # Charger le fichier de configuration de base
            return self.create_rag_config(
                title="retrieve",
                config_path=config_template,
                file_paths=current_file_paths,
                urls=current_urls,
                notion_database_ids=current_notion_db_ids
            )

    def rag_etl_config(self):
        if self.rag_configs.filter(title="etl").exists():
            logger.info(f"Configuration RAG été trouvée pour la collection {self.title}")
            return self.rag_configs.get(title="etl").config_file.path
        else:
            # Charger le fichier de configuration de base
            config_path = Path(__file__).parent / "rag" / "config" / "etl.yaml"
            return self.create_rag_config(title="etl", config_path=config_path)
    
    def rag_index_config(self):
        if self.rag_configs.filter(title="index").exists():
            logger.info(f"Configuration RAG été trouvée pour la collection {self.title}")
            return self.rag_configs.get(title="index").config_file.path
        else:
            # Charger le fichier de configuration de base
            config_path = Path(__file__).parent / "rag" / "config" / "index.yaml"
            return self.create_rag_config(title="index", config_path=config_path)
        
class RagConfig(models.Model):
    title = models.CharField(max_length=255, help_text="Nom de la configuration RAG")
    config_file = models.FileField(
        upload_to=rag_config_upload_path,
        help_text="Fichier de configuration YAML pour le pipeline RAG"
    )
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='rag_configs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Configuration active pour cette collection")

    class Meta:
        verbose_name = "Configuration RAG"
        verbose_name_plural = "Configurations RAG"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.collection.title}"

    def get_config_path(self):
        """
        Retourne le chemin absolu du fichier de configuration
        """
        if self.config_file:
            return self.config_file.path
        return None
        
