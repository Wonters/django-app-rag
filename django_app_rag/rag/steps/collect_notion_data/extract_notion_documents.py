from typing_extensions import Annotated
from zenml import get_step_context, step

from django_app_rag.rag.models import Document, DocumentMetadata
from django_app_rag.rag.infrastructur.notion import NotionDocumentClient


@step
def extract_notion_documents(
    documents_metadata: list[dict],
) -> Annotated[list[Document], "notion_documents"]:
    """Extract content from multiple Notion documents.

    Args:
        documents_metadata: List of document metadata dictionaries to extract content from.

    Returns:
        list[Document]: List of Document objects with their extracted content.
    """

    client = NotionDocumentClient()
    documents = []
    
    # Convertir les dictionnaires en objets DocumentMetadata
    for metadata_dict in documents_metadata:
        document_metadata = DocumentMetadata.model_validate(metadata_dict)
        document = client.extract_document(document_metadata)
        # Retourner directement l'objet Document
        documents.append(document)

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="notion_documents",
        metadata={
            "len_documents": len(documents),
        },
    )

    return documents
