from typing_extensions import Annotated
from zenml import get_step_context
from zenml.steps import step
from loguru import logger
from django_app_rag.rag.models import Document


@step
def filter_by_quality(
    documents: list,
    content_quality_score_threshold: float,
) -> Annotated[list[Document], "filtered_documents"]:
    """Process documents by chunking, embedding, and loading into MongoDB.

    Args:
        documents: List of documents to process.
        content_quality_score_threshold: Minimum quality score threshold for filtering.
    """

    assert 0 <= content_quality_score_threshold <= 1, (
        "Content quality score threshold must be between 0 and 1"
    )

    # Diagnostic logs
    docs_with_score = [doc for doc in documents if doc.content_quality_score is not None]
    docs_without_score = [doc for doc in documents if doc.content_quality_score is None]
    
    logger.info(f"Total documents: {len(documents)}")
    logger.info(f"Documents with quality score: {len(docs_with_score)}")
    logger.info(f"Documents without quality score: {len(docs_without_score)}")
    
    if docs_with_score:
        scores = [doc.content_quality_score for doc in docs_with_score]
        logger.info(f"Quality scores range: {min(scores):.3f} - {max(scores):.3f}")
        logger.info(f"Threshold: {content_quality_score_threshold}")

    valid_docs = [
        doc
        for doc in documents
        if doc.content_quality_score is not None
        and doc.content_quality_score > content_quality_score_threshold
    ]
    logger.info(f"Filtered {len(documents) - len(valid_docs)} documents")

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="filtered_documents",
        metadata={
            "len_documents_before_filtering": len(documents),
            "len_documents_after_filtering": len(valid_docs),
        },
    )

    return valid_docs
