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
            ),
        )
        config_file.save()
        logger.info(f"Configuration RAG été créée pour la collection {self.title}")
        return config_file.config_file.path

    def rag_retrieve_config(self):
        """
        Récupère la configuration RAG pour la collecte de données
        """
        # Récupérer les valeurs actuelles des sources
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
        config_template = Path(__file__).parent / "rag" / "config" / "collect_data.yaml"

        if self.rag_configs.filter(title="retrieve").exists():
            rag_config = self.rag_configs.get(title="retrieve")
            config_file = rag_config.config_file
            with open(config_file.path, "r") as f:
                config = yaml.safe_load(f)
            # Vérifier si la config est à jour
            config_urls = config.get("urls", [])
            config_file_paths = config.get("file_paths", [])
            config_notion_db_ids = config.get("notion_database_ids", [])
            # Comparer les listes (en ignorant l'ordre)
            if set(current_urls) != set(config_urls) or set(
                current_notion_db_ids
            ) != set(config_notion_db_ids) or set(current_file_paths) != set(config_file_paths):
                # Si la config n'est pas à jour, la recréer
                rag_config.delete()
                return self.create_rag_config(
                    title="retrieve",
                    config_path=config_template,
                    urls=current_urls,
                    notion_database_ids=current_notion_db_ids,
                    file_paths=current_file_paths,
                )
            else:
                # Config à jour
                return config_file.path
        else:
            # Charger le fichier de configuration de base
            return self.create_rag_config(
                title="retrieve",
                config_path=config_template,
                urls=current_urls,
                notion_database_ids=current_notion_db_ids,
                file_paths=current_file_paths,
            )

    def rag_etl_config(self):
        """
        Récupère la configuration RAG pour l'ETL
        """
        if self.rag_configs.filter(title="etl").exists():
            logger.info(
                f"Configuration RAG été trouvée pour la collection {self.title}"
            )
            return self.rag_configs.get(title="etl").config_file.path
        else:
            # Charger le fichier de configuration de base
            config_path = Path(__file__).parent / "rag" / "config" / "etl.yaml"
            return self.create_rag_config(title="etl", config_path=config_path)

    def rag_index_config(self):
        """
        Récupère la configuration RAG pour l'indexation
        """
        if self.rag_configs.filter(title="index").exists():
            logger.info(
                f"Configuration RAG été trouvée pour la collection {self.title}"
            )
            return self.rag_configs.get(title="index").config_file.path
        else:
            # Charger le fichier de configuration de base
            config_path = Path(__file__).parent / "rag" / "config" / "index.yaml"
            return self.create_rag_config(title="index", config_path=config_path)

    def rag_etl_source_config(self, source_type: str, source_identifier: str, storage_mode: str = "append"):
        """
        Récupère la configuration RAG pour l'ETL d'une source unique
        """
        if self.rag_configs.filter(title="etl_source").exists():
            logger.info(
                f"Configuration RAG etl_source trouvée pour la collection {self.title}"
            )
            return self.rag_configs.get(title="etl_source").config_file.path
        else:
            # Charger le fichier de configuration de base
            config_path = Path(__file__).parent / "rag" / "config" / "etl_source.yaml"
            return self.create_rag_config(
                title="etl_source",
                config_path=config_path,
                source_type=source_type,
                source_identifier=source_identifier,
                storage_mode=storage_mode
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
