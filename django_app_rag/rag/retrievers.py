from typing import Literal, Union
from django_app_rag.logging import get_logger_loguru
from django_app_rag.rag.infrastructur.faiss.retriever import FaissParentDocumentRetriever
from .embeddings import EmbeddingModelType, EmbeddingsModel, get_embedding_model
from .splitters import get_splitter
from functools import lru_cache
from pathlib import Path
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage

logger = get_logger_loguru(__name__)

# Add these type definitions at the top of the file
RetrieverType = Literal["contextual", "parent"]
RetrieverModel = Union[FaissParentDocumentRetriever]


def get_retriever(
    embedding_model_id: str,
    embedding_model_type: EmbeddingModelType = "huggingface",
    retriever_type: RetrieverType = "parent",
    k: int = 3,
    device: str = "cpu",
    vectorstore: str = "faiss",
    persistent_path: str = None,
    similarity_score_threshold: float = 0.5
) -> RetrieverModel:
    logger.info(
        f"Getting '{retriever_type}' retriever for '{embedding_model_type}' - '{embedding_model_id}' on '{device}' "
        f"with {k} top results and similarity threshold {similarity_score_threshold}"
    )

    embedding_model = get_embedding_model(
        embedding_model_id, embedding_model_type, device
    )

    try:
        return RETRIEVER_TYPES[vectorstore][retriever_type](embedding_model, k, persistent_path, similarity_score_threshold)
    except KeyError:
        raise ValueError(f"Invalid retriever type: {retriever_type}")



def get_parent_document_retriever(
    embedding_model: EmbeddingsModel, k: int = 3, persistent_path: str = None, similarity_score_threshold: float = 0.5
) -> FaissParentDocumentRetriever:
    retriever = FaissParentDocumentRetriever(
        embedding_model=embedding_model,
        child_splitter=get_splitter(200),
        parent_splitter=get_splitter(800),
        search_kwargs={"k": k},
        persistent_path=persistent_path,
        similarity_score_threshold=similarity_score_threshold,
    )

    return retriever


RETRIEVER_TYPES = {"faiss": {"parent": get_parent_document_retriever}}


@lru_cache(maxsize=128)
def get_chunk_text_by_uid(data_dir: str, uid: str) -> str:
    """
    Récupère le texte d'un chunk par son UID depuis l'index FAISS
    
    Args:
        data_dir: Chemin vers le répertoire de données de la collection
        uid: L'UID du chunk à récupérer
        
    Returns:
        Le texte du chunk ou None si non trouvé
    """
    try:
        # Vérifier que le répertoire existe
        if not Path(data_dir).exists():
            logger.warning(f"Le répertoire de données n'existe pas: {data_dir}")
            return None
        
        # Initialiser le retriever pour accéder au docstore
        retriever = get_retriever(
            embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
            embedding_model_type="huggingface",
            retriever_type="parent",
            k=1,  # Pas besoin de beaucoup de résultats
            device="cpu",
            vectorstore="faiss",
            persistent_path=data_dir,
        )
        
        # Accéder au docstore
        vectorstore = retriever.vectorstore
        docstore = vectorstore.docstore
        
        # Chercher le chunk par UID dans le docstore
        for chunk_id, chunk in docstore._dict.items():
            if chunk.metadata.get('id') == uid:
                logger.info(f"Chunk trouvé pour l'UID {uid}")
                return chunk.page_content
        
        logger.warning(f"Aucun chunk trouvé pour l'UID: {uid}")
        return None
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du chunk {uid}: {str(e)}")
        return None


@lru_cache(maxsize=128)
def get_document_text_cached(document_id: str, data_dir: str, collection_name: str) -> dict:
    """
    Fonction cachée pour récupérer le texte d'un document depuis le DiskStorage
    
    Args:
        document_id: ID du document à récupérer
        data_dir: Chemin vers le répertoire de données
        collection_name: Nom de la collection
        
    Returns:
        Le dictionnaire du document ou None si non trouvé
    """
    try:
        disk_storage = DiskStorage(data_dir=data_dir, collection_name=collection_name)
        documents = disk_storage.read([document_id])
        
        if not documents or len(documents) == 0:
            return None
        
        # La méthode read retourne une liste d'objets Document
        # On prend le premier (et seul) document
        document = documents[0]
        return document.model_dump()
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du document {document_id}: {str(e)}")
        return None
