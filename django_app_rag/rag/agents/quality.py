import asyncio
import json
import os
import psutil
from litellm import acompletion
from django_app_rag.logging import get_logger_loguru
from pydantic import BaseModel
from tqdm.asyncio import tqdm
from django_app_rag.rag import utils 
from django_app_rag.rag.models import Document
from ..mixins.task_mixin_async import TaskMixinAsync

logger = get_logger_loguru(__name__)
class QualityScoreResponseFormat(BaseModel):
    """Format for quality score responses from the language model.

    Attributes:
        score: A float between 0.0 and 1.0 representing the quality score.
    """

    score: float


class QualityScoreAgent(TaskMixinAsync[Document]):
    """Evaluates the quality of documents using LiteLLM with async support.

    This class handles the interaction with language models through LiteLLM to
    evaluate document quality based on relevance, factual accuracy, and information
    coherence. It supports both single and batch document processing.

    Attributes:
        model_id: The ID of the language model to use for quality evaluation.
        mock: If True, returns mock quality scores instead of using the model.
        max_concurrent_requests: Maximum number of concurrent API requests.
    """

    SYSTEM_PROMPT_TEMPLATE = """You are an expert judge tasked with evaluating the quality of a given DOCUMENT.

Guidelines:
1. Evaluate the DOCUMENT based on generally accepted facts and reliable information.
2. Evaluate that the DOCUMENT contains relevant information and not only links or error messages.
3. Check that the DOCUMENT doesn't oversimplify or generalize information in a way that changes its meaning or accuracy.

Analyze the text thoroughly and assign a quality score between 0 and 1, where:
- **0.0**: The DOCUMENT is completely irrelevant containing only noise such as links or error messages
- **0.1 - 0.7**: The DOCUMENT is partially relevant containing some relevant information checking partially guidelines
- **0.8 - 1.0**: The DOCUMENT is entirely relevant containing all relevant information following the guidelines

CRITICAL: You MUST return ONLY a valid JSON object with this exact format:
{{
    "score": <your score between 0.0 and 1.0>
}}

Examples of valid responses:
{{
    "score": 0.8
}}

{{
    "score": 0.3
}}

{{
    "score": 1.0
}}

Do NOT include any other text, explanations, or formatting. ONLY the JSON object.

DOCUMENT:
{document}"""

    def __init__(
        self,
        model_id: str = "gpt-4o-mini",
        mock: bool = False,
        max_concurrent_requests: int = 10,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.mock = mock
        self.max_concurrent_requests = max_concurrent_requests

    def __call__(
        self, documents: Document | list[Document]
    ) -> Document | list[Document]:
        """Process single document or batch of documents for summarization.

        Args:
            documents: Single Document or list of Documents to summarize.

        Returns:
            Document | list[Document]: Processed document(s) with summaries.
        """

        is_single_document = isinstance(documents, Document)
        docs_list = [documents] if is_single_document else documents

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            results = asyncio.run(self.__get_quality_score_batch(docs_list))
        else:
            results = loop.run_until_complete(self.__get_quality_score_batch(docs_list))

        return results[0] if is_single_document else results

    async def __get_quality_score_batch(
        self, documents: list[Document]
    ) -> list[Document]:
        """Asynchronously score multiple documents with retry mechanism.

        Args:
            documents: List of documents to score.

        Returns:
            list[Document]: Documents with quality scores.
        """
        start_mem = self.get_memory_usage()
        total_docs = len(documents)
        logger.debug(
            f"Starting quality scoring batch with {self.max_concurrent_requests} concurrent requests. "
            f"Current process memory usage: {start_mem['rss']} MB"
        )

        # Use the mixin's process_with_retry method
        scored_documents = await self.process_with_retry(
            items=documents,
            process_item_func=self.__get_quality_score,
            success_condition=lambda doc: doc.content_quality_score is not None,
            initial_await_time=7,
            retry_await_time=20,
            batch_name="Quality scoring"
        )

        end_mem = self.get_memory_usage()
        memory_diff = end_mem['rss'] - start_mem['rss']
        logger.debug(
            f"Quality scoring batch completed. "
            f"Final process memory usage: {end_mem['rss']} MB, "
            f"Memory diff: {memory_diff} MB"
        )

        success_count = len(scored_documents)
        failed_count = total_docs - success_count
        
        # Log detailed failure information
        if failed_count > 0:
            failed_docs = [doc for doc in documents if doc not in scored_documents]
            logger.warning(f"Failed documents details: {len(failed_docs)} documents failed")
            for i, doc in enumerate(failed_docs[:5]):  # Show first 5 failed docs
                logger.warning(f"Failed doc {i+1}: ID={doc.id}")
        
        logger.info(
            f"Quality scoring completed: "
            f"{success_count}/{total_docs} succeeded ✓ | "
            f"{failed_count}/{total_docs} failed ✗"
        )

        return scored_documents


    async def __get_quality_score(
        self,
        document: Document,
        semaphore: asyncio.Semaphore | None = None,
        await_time_seconds: int = 2,
    ) -> Document | None:
        """Generate a quality score for a single document.

        Args:
            document: The Document object to score.
            semaphore: Optional semaphore for controlling concurrent requests.
            await_time_seconds: Time to wait for the model to respond.
        Returns:
            Document | None: Document with generated quality score or None if failed.
        """
        logger.debug(f"Starting quality score processing for document {document.id}")
        
        if self.mock:
            logger.debug(f"Mock mode: returning quality score 0.5 for document {document.id}")
            return document.add_quality_score(score=0.5)

        async def process_document() -> Document:
            logger.debug(f"Processing document {document.id} for quality scoring")
            
            try:
                # Prepare the input prompt
                input_user_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
                    document=document.content
                )
                
                # Clip tokens if needed
                try:
                    input_user_prompt = utils.clip_tokens(
                        input_user_prompt, max_tokens=8192, model_id=self.model_id
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to clip tokens for document {document.id}: {str(e)}"
                    )

                # Call the API with proper error handling
                logger.debug(f"Calling API for document {document.id} with model {self.model_id}")
                
                response = await asyncio.wait_for(
                    acompletion(
                        model=self.model_id,
                        messages=[
                            {"role": "user", "content": input_user_prompt},
                        ],
                        stream=False,
                    ),
                    timeout=30.0  # 30 second timeout per request
                )
                
                # Rate limiting
                await asyncio.sleep(await_time_seconds)
                
                logger.debug(f"API response received for document {document.id}")

                # Validate response
                if not response or not response.choices:
                    logger.warning(
                        f"No quality score generated for document {document.id} - no choices in response"
                    )
                    return document

                # Parse the response
                raw_answer = response.choices[0].message.content
                logger.debug(f"Received response for document {document.id}: {raw_answer[:100]}...")
                
                quality_score = self._parse_model_output(raw_answer)
                if not quality_score:
                    logger.warning(
                        f"Failed to parse model output for document {document.id}. Raw answer: {raw_answer[:200]}"
                    )
                    return document

                # Add the quality score to the document
                result_doc = document.add_quality_score(score=quality_score.score)
                logger.debug(f"Successfully added quality score {quality_score.score} to document {document.id}")
                return result_doc
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout while scoring document {document.id}")
                return document
            except Exception as e:
                logger.warning(f"Failed to score document {document.id}: {str(e)}")
                return document

        # Execute with semaphore if provided
        try:
            if semaphore:
                async with semaphore:
                    return await process_document()
            else:
                return await process_document()
        except Exception as e:
            logger.error(f"Critical error processing document {document.id}: {str(e)}")
            return document

    def _parse_model_output(
        self, answer: str | None
    ) -> QualityScoreResponseFormat | None:
        if not answer:
            return None

        # Log the raw answer for debugging
        logger.debug(f"Raw model answer: {answer[:200]}...")

        try:
            # First try direct JSON parsing
            dict_content = json.loads(answer)
            return QualityScoreResponseFormat(
                score=dict_content["score"],
            )
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parsing failed: {e}")
            
            # Try to extract JSON from the response if it's wrapped in text
            try:
                # Look for JSON-like content between curly braces
                import re
                json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', answer)
                if json_match:
                    json_str = json_match.group(0)
                    logger.debug(f"Extracted JSON string: {json_str}")
                    dict_content = json.loads(json_str)
                    return QualityScoreResponseFormat(
                        score=dict_content["score"],
                    )
            except Exception as extract_error:
                logger.debug(f"JSON extraction failed: {extract_error}")
            
            # Try to find a number that could be a score
            try:
                import re
                # Look for numbers between 0 and 1 (scores)
                score_match = re.search(r'\b(0\.\d+|[01]\.0)\b', answer)
                if score_match:
                    score_value = float(score_match.group(0))
                    logger.info(f"Extracted score from text: {score_value}")
                    return QualityScoreResponseFormat(score=score_value)
            except Exception as score_error:
                logger.debug(f"Score extraction failed: {score_error}")
            
            # If all else fails, return None
            logger.warning(f"Could not parse quality score from answer: {answer[:100]}...")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error parsing model output: {e}")
            return None


class HeuristicQualityAgent:
    """A rule-based agent for evaluating document quality based on simple heuristics.

    This agent evaluates document quality primarily by analyzing the ratio of URL content
    to total content length, assigning low scores to documents that are primarily
    composed of URLs.
    """

    def __call__(
        self, documents: Document | list[Document]
    ) -> Document | list[Document]:
        """Process single document or batch of documents for quality scoring.

        Args:
            documents: Single Document or list of Documents to evaluate.

        Returns:
            Document | list[Document]: Processed document(s) with quality scores.
        """
        is_single_document = isinstance(documents, Document)
        docs_list = [documents] if is_single_document else documents

        scored_documents = [self.__score_document(document) for document in docs_list]

        return scored_documents[0] if is_single_document else scored_documents

    def __score_document(self, document: Document) -> Document:
        """Score a single document based on URL content ratio.

        Calculates the ratio of URL content length to total content length.
        Documents with > 70% URL content receive a score of 0.0.

        Args:
            document: The Document object to score.

        Returns:
            Document: The input document with an added quality score.
        """

        if len(document.content) == 0:
            return document.add_quality_score(score=0.0)

        url_based_content = sum(len(url) for url in document.child_urls)
        url_content_ratio = url_based_content / len(document.content)

        if url_content_ratio >= 0.7:
            return document.add_quality_score(score=0.0)
        elif url_content_ratio >= 0.5:
            return document.add_quality_score(score=0.2)

        return document
