from pathlib import Path
from typing_extensions import Annotated
from zenml import get_step_context, step
from loguru import logger

from django_app_rag.rag.models import Document, DocumentMetadata
from django_app_rag.rag import utils


@step
def extract_file_documents(
    file_paths: list[Path],
) -> Annotated[list[Document], "file_documents"]:
    """Extract content from multiple files.

    Args:
        file_paths: List of file paths to extract content from.

    Returns:
        list[Document]: List of Document objects with their extracted content.
    """
    documents = []
    
    for file_path in file_paths:
        try:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
                
            # Lire le contenu du fichier
            content = file_path.read_text(encoding='utf-8')
            
            # Créer les métadonnées du document
            document_id = utils.generate_random_hex(length=32)
            document_metadata = DocumentMetadata(
                id=document_id,
                url=str(file_path),
                title=file_path.name,
                properties={
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "file_extension": file_path.suffix,
                }
            )
            
            # Créer le document
            document = Document(
                id=document_id,
                metadata=document_metadata,
                parent_metadata=None,
                content=content,
                child_urls=[],
            )
            
            # Retourner directement l'objet Document
            documents.append(document)
            
            logger.info(f"Successfully extracted document from {file_path}")
            
        except Exception as e:
            logger.error(f"Error extracting document from {file_path}: {e}")
            continue

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="file_documents",
        metadata={
            "len_documents": len(documents),
            "processed_files": len(file_paths),
            "successful_extractions": len(documents),
        },
    )

    return documents 