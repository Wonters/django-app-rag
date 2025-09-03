from typing_extensions import Annotated
from zenml import get_step_context, step
import traceback

from django_app_rag.rag.models import Document, DocumentMetadata
from django_app_rag.rag.crawler import Crawl4AICrawler
from django_app_rag.rag.utils import generate_content_hash
from django_app_rag.logging import get_logger_loguru

logger = get_logger_loguru(__name__)

@step
def extract_url_documents(
    urls: list[str],
    max_workers: int = 10,
) -> Annotated[list[Document], "url_documents"]:
    """Extract content from multiple URLs.

    Args:
        urls: List of URLs to extract content from.
        max_workers: Maximum number of concurrent requests. Defaults to 10.

    Returns:
        list[Document]: List of Document objects with their extracted content.
    """
    documents = []
    
    # Créer des documents temporaires avec les URLs pour utiliser le crawler
    temp_documents = []
    for url in urls:
        # Créer un ID temporaire basé sur l'URL pour les documents temporaires
        temp_id = generate_content_hash(url)
        document_metadata = DocumentMetadata(
            id=temp_id,  # ID temporaire pour les documents de référence
            url=url,
            title="",  # Sera rempli par le crawler
            source_type="url",
            properties={"url": url}
        )
        
        # Créer le document temporaire avec l'ID spécifié (pas de génération automatique)
        temp_document = Document(
            id=temp_id,  # ID explicite pour éviter la génération automatique
            metadata=document_metadata,
            parent_metadata=None,
            content="",  # Sera rempli par le crawler
            child_urls=[url],  # L'URL à crawler
        )
        temp_documents.append(temp_document)
    
    # Utiliser le crawler existant pour extraire le contenu
    try:
        crawler = Crawl4AICrawler(max_concurrent_requests=max_workers)
        crawled_documents = crawler(temp_documents)
    except Exception as e:
        logger.info(f"Error extracting URL documents: {e}")
        logger.error(traceback.format_exc())
        return []
    
    # Retourner directement les objets Document
    # Note: Les documents retournés par le crawler ont des IDs basés sur le contenu récupéré
    for document in crawled_documents:
        documents.append(document)
        logger.info(f"Successfully extracted document from {document.metadata.url} with content-based ID: {document.id}")

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="url_documents",
        metadata={
            "len_documents": len(documents),
            "processed_urls": len(urls),
            "successful_crawls": len(documents),
        },
    )

    return documents 