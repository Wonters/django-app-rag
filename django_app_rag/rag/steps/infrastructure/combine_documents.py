from typing_extensions import Annotated
from zenml import get_step_context, step
from loguru import logger

from django_app_rag.rag.models import Document


@step
def combine_documents(
    notion_documents: list | None = None,
    files_documents: list | None = None,
    urls_documents: list | None = None,
) -> Annotated[list, "combined_documents"]:
    """Combine documents from multiple sources into a single list.
    
    Args:
        notion_documents: Documents from Notion source
        files_documents: Documents from files source
        urls_documents: Documents from URLs source
        
    Returns:
        list[Document]: Combined list of all documents
    """
    combined_documents = []
    
    # Handle None values by converting to empty lists
    notion_docs = notion_documents or []
    files_docs = files_documents or []
    urls_docs = urls_documents or []
    
    if notion_docs:
        combined_documents.extend(notion_docs)
        logger.info(f"Added {len(notion_docs)} notion documents")
    
    if files_docs:
        combined_documents.extend(files_docs)
        logger.info(f"Added {len(files_docs)} file documents")
    
    if urls_docs:
        combined_documents.extend(urls_docs)
        logger.info(f"Added {len(urls_docs)} URL documents")
    
    logger.info(f"Total combined documents: {len(combined_documents)}")
    
    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="combined_documents",
        metadata={
            "total_count": len(combined_documents),
            "notion_count": len(notion_docs),
            "files_count": len(files_docs),
            "urls_count": len(urls_docs),
        },
    )
    
    return combined_documents 