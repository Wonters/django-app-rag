from django.db import models
from django.core.files.base import ContentFile
from pathlib import Path
import os
import yaml
from pathlib import Path
from django_app_rag.logging import get_logger
from django_app_rag.app_settings import app_rag_config


logger = get_logger(__name__)


def rag_config_upload_path(instance, filename):
    """
    Callback pour organiser les fichiers de configuration RAG dans des dossiers
    basés sur le titre et l'ID de la collection
    """
    collection = instance.collection
    folder_name = f"{collection.title.replace(' ', '_')}_{collection.id}"
    return f"rag_configs/{folder_name}/{filename}"


class Document(models.Model):
    """
    Instance to represent a document (source) in the vectorstore / InMemoryDocStore retrieved during RAG processing for an answer
    """

    similarity_score = models.FloatField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    title = models.CharField(max_length=255)
    uid = models.CharField(max_length=255)


class Source(models.Model):
    NOTION = "notion"
    URL = "url"
    FILE = "file"
    SOURCE_TYPE_CHOICES = [
        (NOTION, "Notion"),
        (URL, "URL"),
        (FILE, "File"),
    ]
    type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    link = models.URLField(blank=True, null=True)
    notion_db_ids = models.TextField(
        blank=True,
        null=True,
        help_text="Liste des IDs de bases Notion, séparés par des virgules",
    )
    file = models.FileField(upload_to="rag_sources/", blank=True, null=True)
    collection = models.ForeignKey(
        "Collection", on_delete=models.CASCADE, related_name="sources"
    )
    is_indexed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        if self.type == Source.NOTION:
            return f"{self.title} ({self.type}: {self.notion_db_ids})"
        elif self.type == Source.URL:
            return f"{self.title} ({self.type}: {self.link})"
        elif self.type == Source.FILE:
            return f"{self.title} ({self.type}: {self.file.name})"
        else:
            return f"{self.title} ({self.type})"

    def delete(self, *args, **kwargs):
        if self.type == Source.FILE:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)



class Question(models.Model):
    title = models.CharField(max_length=255)
    field = models.TextField(blank=True, null=True)
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, related_name="questions"
    )

    def __str__(self):
        return self.title


class Answer(models.Model):
    title = models.CharField(max_length=255)
    field = models.TextField(blank=True, null=True)
    documents = models.ManyToManyField(Document, related_name="answers")
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, related_name="answer", null=True, blank=True
    )

    def __str__(self):
        return self.title


class Collection(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - sources: {self.sources.count()}"

    def get_rag_data_dir(self):
        rag_data_dir = app_rag_config.rag_data_dir / f"{self.id}"
        rag_data_dir.mkdir(parents=True, exist_ok=True)
        return rag_data_dir

    def get_rag_config_collection_name(self):
        return f"{self.title.replace(' ', '_')}_{self.id}"

    def create_rag_config(self, title: str, config_path: Path, **kwargs):
        """
        Crée une configuration RAG pour la collection
        title: Nom de la configuration
        config_path: Chemin vers le fichier de configuration
        **kwargs: Paramètres supplémentaires pour la configuration
        Retourne le chemin vers le fichier de configuration
        """
        config = yaml.safe_load(config_path.read_text())
        config["collection_name"] = self.get_rag_config_collection_name()
        config["data_dir"] = self.get_rag_data_dir().as_posix()
        config.update(kwargs)
        config_content = yaml.dump(config, default_flow_style=False)
        config_file = RagConfig(
            title=title,
            collection=self,    
            config_file=ContentFile(
                config_content.encode("utf-8"), name=f"{title}.yaml"
            )
        )
        config_file.save()
        logger.info(f"Configuration RAG été créée pour la collection {self.title}")
        return config_file.config_file.path

    def get_rag_config(self, source: Source = None, **kwargs):
        """
        Récupère la configuration RAG pour la collecte de données
        source: Source optionnel pour la configuration RAG, modifie la configuration en fonction du type de source
        **kwargs: Paramètres supplémentaires pour la configuration
        Retourne le chemin vers le fichier de configuration
        """
        # Récupérer les valeurs actuelles des sources
        if source:
            current_urls = [source.link] if source.type == Source.URL else []
            current_notion_db_ids = [source.notion_db_ids] if source.type == Source.NOTION else []
            current_file_paths = [source.file.path] if source.type == Source.FILE else []
        else:
            current_urls = list(
                self.sources.filter(type=Source.URL).values_list("link", flat=True)
            )
            current_notion_db_ids = list(
                self.sources.filter(type=Source.NOTION).values_list(
                    "notion_db_ids", flat=True
                )
            )
            current_file_paths = []
            for source in self.sources.filter(type=Source.FILE):
                if source.file:
                    current_file_paths.append(source.file.path)
        config_template = Path(__file__).parent / "rag" / "config" / "rag.yaml"

        if config := self.rag_configs.first():
            config_file = config.config_file
            with open(config_file.path, "r") as f:
                data = yaml.safe_load(f)
            # Vérifier si la config est à jour
            config_urls = data.get("urls", [])
            config_file_paths = data.get("file_paths", [])
            config_notion_db_ids = data.get("notion_database_ids", [])
            # Comparer les listes (en ignorant l'ordre)
            if set(current_urls) != set(config_urls) or set(
                current_notion_db_ids
            ) != set(config_notion_db_ids) or set(current_file_paths) != set(config_file_paths):
                # Si la config n'est pas à jour, la recréer
                config.delete()
                return self.create_rag_config(
                    title="rag",
                    config_path=config_template,
                    urls=current_urls,
                    notion_database_ids=current_notion_db_ids,
                    file_paths=current_file_paths,
                    storage_mode="append" if source else "overwrite",
                )
            else:
                # Config à jour
                return config_file.path
        else:
            # Charger le fichier de configuration de base
            return self.create_rag_config(
                title="rag",
                config_path=config_template,
                urls=current_urls,
                notion_database_ids=current_notion_db_ids,
                file_paths=current_file_paths,
                storage_mode="append" if source else "overwrite",
            )


class RagConfig(models.Model):
    title = models.CharField(max_length=255, help_text="Nom de la configuration RAG")
    config_file = models.FileField(
        upload_to=rag_config_upload_path,
        help_text="Fichier de configuration YAML pour le pipeline RAG",
    )
    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="rag_configs"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True, help_text="Configuration active pour cette collection"
    )

    class Meta:
        verbose_name = "Configuration RAG"
        verbose_name_plural = "Configurations RAG"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.collection.title}"

    def delete(self, *args, **kwargs):
        self.config_file.delete(save=False)
        super().delete(*args, **kwargs)

    def get_config_path(self):
        """
        Retourne le chemin absolu du fichier de configuration
        """
        if self.config_file:
            return self.config_file.path
        return None
    

