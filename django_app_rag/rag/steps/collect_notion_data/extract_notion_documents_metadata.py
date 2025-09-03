from django_app_rag.logging import get_logger_loguru
from typing_extensions import Annotated
from zenml import get_step_context, step
from django_app_rag.rag.infrastructur.notion import NotionDatabaseClient


logger = get_logger_loguru(__name__)

@step
def extract_notion_documents_metadata(
    database_id: str,
) -> Annotated[list[dict], "notion_documents_metadata"]:
    """Extract metadata from Notion documents in a specified database.

    Args:
        database_id: The ID of the Notion database to query.

    Returns:
        A list of dictionaries containing the extracted information.
    """

    client = NotionDatabaseClient()
    documents_metadata = client.query_notion_database(database_id)

    # Convertir les objets DocumentMetadata en dictionnaires
    documents_metadata_dicts = [
        doc.model_dump() for doc in documents_metadata
    ]

    logger.info(
        f"Extracted {len(documents_metadata)} documents metadata from {database_id}"
    )

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="notion_documents_metadata",
        metadata={
            "database_id": database_id,
            "len_documents_metadata": len(documents_metadata),
        },
    )

    return documents_metadata_dicts
