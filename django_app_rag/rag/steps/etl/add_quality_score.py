from django_app_rag.logging import get_logger_loguru
from typing_extensions import Annotated
from zenml import get_step_context, step
from django_app_rag.rag.agents.quality import (
    HeuristicQualityAgent,
    QualityScoreAgent,
)
from django_app_rag.rag.models import Document

logger = get_logger_loguru(__name__)

@step
def add_quality_score(
    documents: list,
    model_id: str = "gpt-4o-mini",
    mock: bool = False,
    max_workers: int = 10,
) -> Annotated[list[Document], "scored_documents"]:
    """Adds quality scores to documents using heuristic and model-based scoring agents.

    This function processes documents in two stages:
    1. Applies heuristic-based quality scoring
    2. Uses a model-based quality agent for documents that weren't scored by heuristics

    Args:
        documents: List of documents to evaluate for quality
        model_id: Identifier for the model to use in quality assessment.
            Defaults to "gpt-4o-mini"
        mock: If True, uses mock responses instead of real model calls.
            Defaults to False
        max_workers: Maximum number of concurrent quality check operations.
            Defaults to 10

    Returns:
        list[Document]: Documents enhanced with quality scores, annotated as
            "scored_documents" for pipeline metadata tracking

    Note:
        The function adds metadata to the step context including the total number
        of documents and how many received quality scores.
    """
    heuristic_quality_agent = HeuristicQualityAgent()
    scored_documents: list[Document] = heuristic_quality_agent(documents)

    scored_documents_with_heuristics = [
        d for d in scored_documents if d.content_quality_score is not None
    ]
    documents_without_scores = [
        d for d in scored_documents if d.content_quality_score is None
    ]

    quality_agent = QualityScoreAgent(
        model_id=model_id, mock=mock, max_concurrent_requests=max_workers
    )
    
    try:
        scored_documents_with_agents: list[Document] = quality_agent(
            documents_without_scores
        )
    except Exception as e:
        logger.error(f"Error during quality scoring with agent: {e}")
        # Fallback: assign default scores to documents that couldn't be scored
        scored_documents_with_agents = []
        for doc in documents_without_scores:
            try:
                # Assign a default score based on content length and URL ratio
                if len(doc.content) == 0:
                    scored_doc = doc.add_quality_score(score=0.0)
                elif len(doc.child_urls) > 0:
                    url_ratio = sum(len(url) for url in doc.child_urls) / len(doc.content)
                    if url_ratio >= 0.7:
                        scored_doc = doc.add_quality_score(score=0.1)
                    elif url_ratio >= 0.5:
                        scored_doc = doc.add_quality_score(score=0.3)
                    else:
                        scored_doc = doc.add_quality_score(score=0.6)
                else:
                    scored_doc = doc.add_quality_score(score=0.7)
                scored_documents_with_agents.append(scored_doc)
            except Exception as doc_error:
                logger.warning(f"Could not assign fallback score to document {doc.id}: {doc_error}")
                scored_documents_with_agents.append(doc)

    scored_documents: list[Document] = (
        scored_documents_with_heuristics + scored_documents_with_agents
    )

    len_documents = len(documents)
    len_documents_with_scores = len(
        [doc for doc in scored_documents if doc.content_quality_score is not None]
    )
    logger.info(f"Total documents: {len_documents}")
    logger.info(f"Total documents that were scored: {len_documents_with_scores}")

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="scored_documents",
        metadata={
            "len_documents": len_documents,
            "len_documents_with_scores": len_documents_with_scores,
            "len_documents_scored_with_heuristics": len(
                scored_documents_with_heuristics
            ),
            "len_documents_scored_with_agents": len(scored_documents_with_agents),
        },
    )

    return scored_documents
