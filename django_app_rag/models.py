from django.db import models
from django.core.files.base import ContentFile
from pathlib import Path
import yaml
import numpy as np
from functools import lru_cache
from django.db import transaction
from django.core.cache import cache
import hashlib
from django_app_rag.logging import get_logger
from django_app_rag.app_settings import app_rag_config
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage
from django_app_rag.rag.utils import generate_consistent_id
from django_app_rag.path_utils import ensure_path, ensure_str, safe_join
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
    quality_score = models.FloatField(blank=True, null=True)

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
    
    def get_rag_id(self):
        if self.type == Source.NOTION:
            identifier = self.notion_db_ids
        elif self.type == Source.URL:
            identifier = self.link
        elif self.type == Source.FILE:
            identifier = ensure_path(self.file.name).name
        return generate_consistent_id(self.type, identifier)

    def compute_quality_score(self, reset: bool = False):
        if self.quality_score is None or reset:
            disk_storage = DiskStorage(
                collection_name=self.collection.get_rag_config_collection_name(),
                data_dir=ensure_str(self.collection.get_rag_data_dir()),
            )
            documents = disk_storage.read_raw()
            quality_score: np.ndarray = np.array([])
            for document in documents:
                if document["metadata"]["id"] == self.get_rag_id():
                    quality_score = np.append(quality_score, float(document["content_quality_score"]))
            
            # Éviter NaN si aucun score n'est trouvé
            if len(quality_score) > 0:
                self.quality_score = quality_score.mean()
            else:
                self.quality_score = 0.0  # ou 0.0 selon votre logique métier
            self.save()


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
        config_path_obj = ensure_path(config_path)
        config = yaml.safe_load(config_path_obj.read_text())
        config["collection_name"] = self.get_rag_config_collection_name()
        config["data_dir"] = ensure_str(self.get_rag_data_dir())
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
        Récupère la configuration RAG pour la collecte de données avec protection contre les race conditions.

        Args:
            source: Source optionnel pour la configuration RAG
            **kwargs: Paramètres supplémentaires pour la configuration

        Returns:
            str: Chemin vers le fichier de configuration

        Note:
            Utilise un lock distribué pour éviter les race conditions lors de la création/modification
            des configurations. Thread-safe et process-safe.
        """
        lock_key = f"rag_config_lock_{self.id}"
        lock_timeout = 30  # 30 seconds timeout

        # Tenter d'acquérir le lock
        if not cache.add(lock_key, "locked", timeout=lock_timeout):
            # Si le lock ne peut pas être acquis, attendre et réessayer
            import time
            for _ in range(10):  # Max 10 retries = 5 seconds
                time.sleep(0.5)
                if cache.add(lock_key, "locked", timeout=lock_timeout):
                    break
            else:
                logger.warning(f"Could not acquire lock for collection {self.id} config")
                # Fallback: utiliser la config existante ou template
                if config := self.rag_configs.filter(is_active=True).first():
                    return ensure_str(config.config_file.path)
                return ensure_str(safe_join(Path(__file__).parent, "rag", "config", "rag.yaml"))

        try:
            # Récupérer les valeurs actuelles des sources
            current_urls, current_notion_db_ids, current_file_paths = self._get_current_sources(source)

            # Calculer un hash pour détecter les changements
            config_hash = self._compute_config_hash(current_urls, current_notion_db_ids, current_file_paths)

            # Utiliser une transaction pour garantir la cohérence
            with transaction.atomic():
                # Récupérer la config active avec un lock de ligne
                config = self.rag_configs.select_for_update().filter(is_active=True).first()

                if config:
                    # Vérifier si la config est toujours valide
                    if self._is_config_valid(config, current_urls, current_notion_db_ids, current_file_paths, config_hash):
                        return ensure_str(config.config_file.path)

                    # Config obsolète : la marquer comme inactive et en créer une nouvelle
                    config.is_active = False
                    config.save()

                # Créer une nouvelle configuration
                config_template = safe_join(Path(__file__).parent, "rag", "config", "rag.yaml")
                new_config_path = self.create_rag_config(
                    title=f"rag_v{self.rag_configs.count() + 1}",
                    config_path=config_template,
                    urls=current_urls,
                    notion_database_ids=current_notion_db_ids,
                    file_paths=current_file_paths,
                    storage_mode="append" if source else "overwrite",
                )

                # Stocker le hash dans la config pour validation future
                new_config = self.rag_configs.get(config_file__icontains=ensure_path(new_config_path).name)
                new_config.config_hash = config_hash
                new_config.save()

                return new_config_path

        finally:
            # Toujours libérer le lock
            cache.delete(lock_key)

    def _get_current_sources(self, source: Source = None):
        """Extract current URLs, Notion IDs, and file paths from sources."""
        if source:
            current_urls = [source.link] if source.type == Source.URL else []
            current_notion_db_ids = [source.notion_db_ids] if source.type == Source.NOTION else []
            current_file_paths = [str(source.file.path)] if source.type == Source.FILE and source.file else []
        else:
            current_urls = list(
                self.sources.filter(type=Source.URL).values_list("link", flat=True)
            )
            current_notion_db_ids = list(
                self.sources.filter(type=Source.NOTION).values_list("notion_db_ids", flat=True)
            )
            current_file_paths = [
                str(s.file.path) for s in self.sources.filter(type=Source.FILE)
                if s.file
            ]

        return current_urls, current_notion_db_ids, current_file_paths

    def _compute_config_hash(self, urls, notion_ids, file_paths):
        """Compute a hash of the configuration for change detection."""
        # Normalize and sort for consistent hashing
        content = {
            'urls': sorted(urls),
            'notion_ids': sorted(notion_ids),
            'file_paths': sorted(file_paths)
        }
        content_str = yaml.dump(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _is_config_valid(self, config, current_urls, current_notion_db_ids, current_file_paths, expected_hash):
        """Check if config is still valid by comparing content."""
        try:
            config_path = ensure_path(config.config_file.path)

            # Check if file exists
            if not config_path.exists():
                logger.warning(f"Config file {config_path} does not exist")
                return False

            # Check hash if available
            if hasattr(config, 'config_hash') and config.config_hash:
                return config.config_hash == expected_hash

            # Fallback: compare actual content
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)

            config_urls = set(data.get("urls", []))
            config_file_paths = set(data.get("file_paths", []))
            config_notion_db_ids = set(data.get("notion_database_ids", []))

            return (
                set(current_urls) == config_urls and
                set(current_notion_db_ids) == config_notion_db_ids and
                set(current_file_paths) == config_file_paths
            )
        except Exception as e:
            logger.error(f"Error validating config: {e}")
            return False


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
    config_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA256 hash de la configuration pour détecter les changements"
    )
    version = models.IntegerField(
        default=1,
        help_text="Numéro de version de la configuration"
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
    

