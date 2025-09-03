import sqlitedict
import sqlite3
import json
from pathlib import Path
from typing import Optional, Iterator, List
from uuid import uuid4
from django_app_rag.logging import get_logger_loguru
from django_app_rag.rag.models import Document

logger = get_logger_loguru(__name__)


class DiskStorage:
    """
    Storage class for saving and loading data to disk using sqlitedict.
    """
    
    def __init__(self, collection_name: str, data_dir: str, autocommit: bool = True, wal: bool = True):
        logger.info(f"Initializing DiskStorage for collection {collection_name} in {data_dir}")
        self.storage_path = Path(data_dir) / "storage"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.path = str(self.storage_path / f"{collection_name}.db")
        self.table = collection_name
        self.db = sqlitedict.SqliteDict(
            filename=self.path,
            tablename=self.table,
            autocommit=autocommit,
            encode=json.dumps,
            decode=json.loads,
            journal_mode="WAL" if wal else None,
        )

    # -- context manager --
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is None and not self.db.autocommit:
            self.db.commit()
        self.db.close()

    # -- opérations de base --
    def put(self, doc_id: str, doc: dict) -> None:
        """Ajoute ou met à jour un document avec l'ID spécifié"""
        self.db[doc_id] = doc

    def bulk_put(self, docs: List[dict], commit_every: int = 10_000) -> None:
        """Ajoute plusieurs documents en lot"""
        for i, doc in enumerate(docs, 1):
            doc_id = doc.get('uid', str(uuid4()))
            self.db[doc_id] = doc
            if not self.db.autocommit and i % commit_every == 0:
                self.db.commit()
        if not self.db.autocommit:
            self.db.commit()

    def get(self, doc_id: str) -> Optional[dict]:
        """Récupère un document par son ID"""
        return self.db.get(doc_id)

    def delete(self, doc_id: str) -> None:
        """Supprime un document par son ID"""
        if doc_id in self.db:
            del self.db[doc_id]
            if not self.db.autocommit:
                self.db.commit()

    def __len__(self) -> int:
        """Retourne le nombre de documents dans la collection"""
        return len(self.db)

    # -- opérations de collection --
    def save(self, data: List[dict], mode: str = "overwrite"):
        """
        Sauvegarde les données dans le stockage.
        
        Args:
            data: Liste des documents à sauvegarder
            mode: Mode de sauvegarde - "overwrite" (écrase tout) ou "append" (ajoute)
        """
        if not data:
            logger.warning("Aucune donnée à sauvegarder")
            return

        if mode == "append":
            # Mode ajout : ajouter les nouveaux documents
            existing_count = len(self.db)
            added_count = 0
            
            for doc in data:
                doc_id = doc.get('uid', str(uuid4()))
                if doc_id not in self.db:
                    self.db[doc_id] = doc
                    added_count += 1
            
            logger.info(f"Ajout de {added_count} nouveaux documents à {existing_count} existants")
        else:
            # Mode écrasement (par défaut)
            self.db.clear()
            for doc in data:
                doc_id = doc.get('uid', str(uuid4()))
                self.db[doc_id] = doc
            logger.info(f"Mode {mode}: écrasement complet avec {len(data)} documents")

    def read_raw(self) -> List[dict]:
        """Lit tous les documents bruts de la collection"""
        try:
            return list(self.db.values())
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du stockage: {e}")
            return []

    def read(self, ids_documents: Optional[List[str]] = None) -> List[Document]:
        """
        Lit les documents de la base de données avec filtrage optionnel par IDs.
        Utilise des requêtes SQL directes pour une meilleure performance.
        
        Args:
            ids_documents: Liste des IDs de documents à récupérer. Si None, retourne tous les documents.
        
        Returns:
            Liste des objets Document correspondant aux IDs spécifiés, ou tous les documents si aucun filtre.
        """
        try:
            if ids_documents is None:
                # Si aucun filtre, retourner tous les documents
                documents = []
                for doc_data in self.db.values():
                    try:
                        doc = Document.model_validate(doc_data)
                        documents.append(doc)
                    except Exception as e:
                        logger.warning(f"Erreur lors de la création du Document: {e}")
                        continue
                return documents
            
            if not ids_documents:
                # Si liste vide, retourner liste vide
                logger.info("Liste d'IDs vide, retour d'une liste vide")
                return []
            
            # Utiliser une requête SQL directe pour le filtrage par IDs
            conn = sqlite3.connect(self.path)
            try:
                # Construire la clause IN avec le bon nombre de placeholders
                placeholders = ','.join(['?' for _ in ids_documents])
                sql = f"SELECT value FROM {self.table} WHERE key IN ({placeholders})"
                
                # Exécuter la requête
                cursor = conn.execute(sql, ids_documents)
                documents = []
                found_ids = []
                
                for (bval,) in cursor:
                    try:
                        doc_data = json.loads(bval)
                        # Créer un objet Document à partir des données
                        doc = Document.model_validate(doc_data)
                        documents.append(doc)
                        # Extraire l'ID du document pour le logging
                        found_ids.append(doc.id)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Erreur de décodage JSON pour un document: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Erreur lors de la création du Document: {e}")
                        continue
                
                # Identifier les IDs manquants
                missing_ids = [doc_id for doc_id in ids_documents if doc_id not in found_ids]
                
                logger.info(f"Récupération de {len(documents)} documents sur {len(ids_documents)} IDs demandés")
                if missing_ids:
                    logger.warning(f"IDs non trouvés: {missing_ids}")
                
                return documents
                
            finally:
                conn.close()
            
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des documents avec filtrage: {e}")
            return []

    def clear_collection(self):
        """Efface tous les documents de la collection"""
        try:
            self.db.clear()
            logger.info(f"Collection {self.table} effacée")
        except Exception as e:
            logger.error(f"Erreur lors de l'effacement de la collection: {e}")

    def get_document_count(self) -> int:
        """Retourne le nombre de documents dans la collection"""
        return len(self)

    def remove_documents_by_source(self, source_identifier: str):
        """
        Supprime les documents d'une source spécifique.
        
        Args:
            source_identifier: Identifiant de la source (URL, chemin de fichier, etc.)
        """
        try:
            keys_to_remove = []
            
            for key, doc in self.db.items():
                # Adapter selon la structure de vos documents
                if ('source' in doc and doc['source'] == source_identifier) or \
                   ('url' in doc and doc['url'] == source_identifier) or \
                   ('file_path' in doc and doc['file_path'] == source_identifier):
                    keys_to_remove.append(key)
            
            # Supprimer les documents identifiés
            for key in keys_to_remove:
                del self.db[key]
            
            logger.info(f"Supprimé {len(keys_to_remove)} documents de la source {source_identifier}")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des documents: {e}")

    # -- recherche par préfixe d'id (optionnelle) --
    def iter_prefix(self, prefix: str, limit: Optional[int] = None) -> Iterator[dict]:
        """Itère sur les documents dont l'ID commence par le préfixe donné"""
        conn = sqlite3.connect(self.path)
        try:
            # table = (key TEXT PRIMARY KEY, value BLOB)
            sql = f"SELECT value FROM {self.table} WHERE key LIKE ? ORDER BY key"
            if limit is not None:
                sql += f" LIMIT {int(limit)}"
            for (bval,) in conn.execute(sql, (prefix + "%",)):
                yield json.loads(bval)
        finally:
            conn.close()

    def close(self):
        """Ferme la connexion à la base de données"""
        if hasattr(self, 'db'):
            self.db.close()
