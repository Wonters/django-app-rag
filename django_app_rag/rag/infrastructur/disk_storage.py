import msgpack
from pathlib import Path
from pydantic import BaseModel
from typing import Union, Type, List
from uuid import uuid4
from loguru import logger


class DiskStorage:
    """
    Storage class for saving and loading data to disk using msgpack serialization.
    """
    storage_path: Path 
    model_class: Type[BaseModel]
    collection_name: str

    def __init__(self, model_class: Type[BaseModel], collection_name: str, data_dir: str):
        logger.info(f"Initializing DiskStorage for collection {collection_name} in {data_dir}")
        self.storage_path = Path(data_dir) / "storage"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.model_class = model_class
        self.collection_name = collection_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @property
    def location(self) -> Path:
        return self.storage_path / f"{self.collection_name}.msgpack"

    def save(self, data: List[BaseModel], mode: str = "overwrite"):
        """
        Sauvegarde les données dans le stockage msgpack.
        
        Args:
            data: Liste des documents à sauvegarder
            mode: Mode de sauvegarde - "overwrite" (écrase tout) ou "append" (ajoute)
        """
        if not data:
            logger.warning("Aucune donnée à sauvegarder")
            return
            
        # if not isinstance(data[0], self.model_class):
        #     logger.error(f"Data {type(data[0])} is not an instance of {self.model_class}")
        #     return

        # Convertir en dictionnaires pour la sérialisation
        new_data = [item.model_dump() for item in data]
        
        if mode == "append" and self.location.exists():
            # Mode ajout : lire les données existantes et ajouter les nouvelles
            try:
                existing_data = self.read_raw()
                # Éviter les doublons basés sur l'UID
                existing_uids = {doc.get('uid') for doc in existing_data if doc.get('uid')}
                unique_new_data = [doc for doc in new_data if doc.get('uid') not in existing_uids]
                
                if unique_new_data:
                    combined_data = existing_data + unique_new_data
                    logger.info(f"Ajout de {len(unique_new_data)} nouveaux documents à {len(existing_data)} existants")
                    final_data = combined_data
                else:
                    logger.info("Aucun nouveau document unique à ajouter")
                    return
            except Exception as e:
                logger.warning(f"Erreur lors de la lecture des données existantes, passage en mode écrasement: {e}")
                final_data = new_data
        else:
            # Mode écrasement (par défaut)
            final_data = new_data
            logger.info(f"Mode {mode}: écrasement complet avec {len(new_data)} documents")

        # Sauvegarder
        with open(self.location, "wb") as f:
            f.write(msgpack.packb(final_data))
            logger.info(f"Sauvegardé {len(final_data)} documents dans {self.location}")

    def read_raw(self) -> List[dict]:
        """
        Lit les données brutes (dict) du stockage msgpack.
        """
        if not self.location.exists():
            return []
            
        try:
            with open(self.location, "rb") as f:
                data = msgpack.unpackb(f.read())
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du stockage: {e}")
            return []

    def read(self) -> List[BaseModel]:
        """
        Read the data from the disk storage.
        """
        raw_data = self.read_raw()
        try:
            return [self.model_class.model_validate(item) for item in raw_data]
        except Exception as e:
            logger.error(f"Erreur lors de la validation des données: {e}")
            return []

    def clear_collection(self):
        if self.location.exists():
            self.location.unlink()
            logger.info(f"Collection {self.collection_name} effacée")

    def get_document_count(self) -> int:
        """Retourne le nombre de documents dans la collection"""
        raw_data = self.read_raw()
        return len(raw_data)

    def remove_documents_by_source(self, source_identifier: str):
        """
        Supprime les documents d'une source spécifique.
        
        Args:
            source_identifier: Identifiant de la source (URL, chemin de fichier, etc.)
        """
        if not self.location.exists():
            return
            
        raw_data = self.read_raw()
        filtered_data = []
        
        for doc in raw_data:
            # Adapter selon la structure de vos documents
            if 'source' in doc and doc['source'] != source_identifier:
                filtered_data.append(doc)
            elif 'url' in doc and doc['url'] != source_identifier:
                filtered_data.append(doc)
            elif 'file_path' in doc and doc['file_path'] != source_identifier:
                filtered_data.append(doc)
            else:
                # Garder le document si aucun critère de correspondance
                filtered_data.append(doc)
        
        # Sauvegarder les données filtrées
        with open(self.location, "wb") as f:
            f.write(msgpack.packb(filtered_data))
        
        logger.info(f"Supprimé les documents de la source {source_identifier}")
