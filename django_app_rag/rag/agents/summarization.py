import asyncio
import os
import psutil
from litellm import acompletion
from django_app_rag.logging import get_logger_loguru
from tqdm.asyncio import tqdm
from django_app_rag.rag.models import Document
from ..mixins.task_mixin_async import TaskMixinAsync

logger = get_logger_loguru(__name__)

class SummarizationAgent(TaskMixinAsync[Document]):
    """Generates summaries for documents using LiteLLM with async support.

    This class handles the interaction with language models through LiteLLM to
    generate concise summaries while preserving key information from the original
    documents. It supports both single and batch document processing.

    Attributes:
        max_characters: Maximum number of characters for the summary.
        model_id: The ID of the language model to use for summarization.
        mock: If True, returns mock summaries instead of using the model.
        max_concurrent_requests: Maximum number of concurrent API requests.
    """

    SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant specialized in summarizing documents.
Your task is to create a clear, concise TL;DR summary in markdown format.
Things to keep in mind while summarizing:
- titles of sections and sub-sections
- tags such as Generative AI, LLMs, etc.
- entities such as persons, organizations, processes, people, etc.
- the style such as the type, sentiment and writing style of the document
- the main findings and insights while preserving key information and main ideas
- ignore any irrelevant information such as cookie policies, privacy policies, HTTP errors,etc.

Document content:
{content}

Generate a concise TL;DR summary having a maximum of {characters} characters of the key findings from the provided documents, highlighting the most significant insights and implications.
Return the document in markdown format regardless of the original format.
"""

    def __init__(
        self,
        max_characters: int,
        model_id: str = "gpt-4o-mini",
        mock: bool = False,
        max_concurrent_requests: int = 10,
    ) -> None:
        super().__init__()
        self.max_characters = max_characters
        self.model_id = model_id
        self.mock = mock
        self.max_concurrent_requests = max_concurrent_requests

    def __call__(
        self, documents: Document | list[Document], temperature: float = 0.0
    ) -> Document | list[Document]:
        """Process single document or batch of documents for summarization.

        Args:
            documents: Single Document or list of Documents to summarize.
            temperature: Temperature for the summarization model.
        Returns:
            Document | list[Document]: Processed document(s) with summaries.
        """

        is_single_document = isinstance(documents, Document)
        docs_list = [documents] if is_single_document else documents

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            results = asyncio.run(self.__summarize_batch(docs_list, temperature))
        else:
            results = loop.run_until_complete(
                self.__summarize_batch(docs_list, temperature)
            )

        return results[0] if is_single_document else results

    async def __summarize_batch(
        self, documents: list[Document], temperature: float = 0.0
    ) -> list[Document]:
        """Asynchronously summarize multiple documents.

        Args:
            documents: List of documents to summarize.
            temperature: Temperature for the summarization model.
        Returns:
            list[Document]: Documents with generated summaries.
        """
        start_mem = self.get_memory_usage()
        total_docs = len(documents)
        logger.debug(
            f"Starting summarization batch with {self.max_concurrent_requests} concurrent requests. "
            f"Current process memory usage: {start_mem['rss']} MB"
        )

        # Use the mixin's process_with_retry method
        summarized_documents = await self.process_with_retry(
            items=documents,
            process_item_func=lambda doc, semaphore, await_time: self.__summarize(
                doc, semaphore, temperature, await_time
            ),
            success_condition=lambda doc: doc.summary is not None,
            initial_await_time=7,
            retry_await_time=20,
            batch_name="Summarization"
        )

        end_mem = self.get_memory_usage()
        memory_diff = end_mem['rss'] - start_mem['rss']
        logger.debug(
            f"Summarization batch completed. "
            f"Final process memory usage: {end_mem['rss']} MB, "
            f"Memory diff: {memory_diff} MB"
        )

        success_count = len(summarized_documents)
        failed_count = total_docs - success_count
        logger.info(
            f"Summarization completed: "
            f"{success_count}/{total_docs} succeeded ✓ | "
            f"{failed_count}/{total_docs} failed ✗"
        )

        return summarized_documents


    async def __summarize(
        self,
        document: Document,
        semaphore: asyncio.Semaphore | None = None,
        temperature: float = 0.0,
        await_time_seconds: int = 2,
    ) -> Document:
        """Generate a summary for a single document.

        Args:
            document: The Document object to summarize.
            semaphore: Optional semaphore for controlling concurrent requests.
            temperature: Temperature for the summarization model.
        Returns:
            Document | None: Document with generated summary or None if failed.
        """
        if self.mock:
            return document.add_summary("This is a mock summary")

        async def process_document():
            try:
                response = await acompletion(
                    model=self.model_id,
                    messages=[
                        {
                            "role": "system",
                            "content": self.SYSTEM_PROMPT_TEMPLATE.format(
                                characters=self.max_characters, content=document.content
                            ),
                        },
                    ],
                    stream=False,
                    temperature=temperature,
                )
                await asyncio.sleep(await_time_seconds)  # Rate limiting

                if not response.choices:
                    logger.warning(f"No summary generated for document {document.id}")
                    return document

                summary: str = response.choices[0].message.content
                return document.add_summary(summary)
            except Exception as e:
                logger.warning(f"Failed to summarize document {document.id}: {str(e)}")
                return document

        if semaphore:
            async with semaphore:
                return await process_document()

        return await process_document()
