from zenml import step
from typing_extensions import Annotated
from django_app_rag.rag.models import Document
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage

@step
def save_to_diskstorage(
    documents: list,
    collection_name: str,
    data_dir: str = "data",
    mode: str = "overwrite"
) -> Annotated[bool, "success"]:
    """
    Sauvegarde les documents dans le stockage disque avec msgpack.
    
    Args:
        documents: Liste des documents à sauvegarder
        collection_name: Nom de la collection
        data_dir: Répertoire de données
        mode: Mode de sauvegarde - "overwrite" (écrase tout) ou "append" (ajoute)
    """
    storage = DiskStorage(
        model_class=Document, 
        collection_name=collection_name, 
        data_dir=data_dir
    )
    
    storage.save(documents, mode=mode)
    return True 