import json
from pathlib import Path
from typing import Any
from loguru import logger
from smolagents import Tool
from django_app_rag.rag.monitoring.mlflow import mlflow_track
from django_app_rag.rag.retrievers import get_retriever
import mlflow
import yaml


class QuestionAnswerTool(Tool):
    name = "question_answer_tool"
    description = """Use this tool to answer questions by searching through the knowledge base and providing comprehensive answers with source citations.
    This tool combines document retrieval with answer generation to provide accurate, well-sourced responses.
    Best used when you need to:
    - Answer specific questions about topics in the knowledge base
    - Get detailed explanations with supporting evidence
    - Research complex topics with multiple sources
    - Provide answers that include proper citations and references
    The tool will return a comprehensive answer along with the sources used."""

    inputs = {
        "question": {
            "type": "string",
            "description": """The question to answer. Should be a clear, specific question about information in the knowledge base.
            Examples:
            - "What is the FTI architecture?"
            - "How do vector databases work?"
            - "What are the best practices for RAG implementation?"""",
        }
    }
    output_type = "string"

    def __init__(self, config_path: Path, **kwargs):
        super().__init__(**kwargs)

        self.config_path = config_path
        self.retriever = self.__load_retriever(config_path)

    def __load_retriever(self, config_path: Path):
        config = yaml.safe_load(config_path.read_text())
        config = config["parameters"]

        return get_retriever(
            embedding_model_id=config["embedding_model_id"],
            embedding_model_type=config["embedding_model_type"],
            retriever_type=config["retriever_type"],
            k=5,
            device=config["device"],
            persistent_path=config["persistent_path"],
        )

    @mlflow_track(name="QuestionAnswerTool.forward")
    def forward(self, question: str) -> str:
        # Configure MLflow tracking URI if not already set
        if not mlflow.get_tracking_uri() or mlflow.get_tracking_uri().startswith('file://'):
            mlflow.set_tracking_uri("file:///tmp/mlruns")
        
        if hasattr(self.retriever, "search_kwargs"):
            search_kwargs = self.retriever.search_kwargs
        else:
            try:
                search_kwargs = {
                    "fulltext_penalty": self.retriever.fulltext_penalty,
                    "vector_score_penalty": self.retriever.vector_penalty,
                    "top_k": self.retriever.top_k,
                }
            except AttributeError:
                logger.warning("Could not extract search kwargs from retriever.")
                search_kwargs = {}

        mlflow.set_tags({"agent": True})
        mlflow.log_dict(
            {
                "search": search_kwargs,
                "embedding_model_id": self.retriever.vectorstore.embeddings.model_name,
                "question": question,
            },
            "trace.json",
        )

        try:
            question = self.__parse_question(question)
            relevant_docs = self.retriever.invoke(question)

            if not relevant_docs:
                return "I couldn't find any relevant documents to answer your question. Please try rephrasing your question or ask about a different topic."

            # Format the documents for context
            formatted_docs = []
            sources = []
            
            for i, doc in enumerate(relevant_docs, 1):
                title = doc.metadata.get("title", f"Document {i}")
                url = doc.metadata.get("url", "No URL available")
                content = doc.page_content.strip()
                
                formatted_docs.append(
                    f"""
<document id="{i}">
<title>{title}</title>
<url>{url}</url>
<content>{content}</content>
</document>
"""
                )
                
                sources.append({
                    "id": i,
                    "title": title,
                    "url": url
                })

            # Create the context for the answer
            context = "\n".join(formatted_docs)
            
            # Generate the answer with sources
            answer = self.__generate_answer(question, context, sources)
            
            return answer
            
        except Exception as e:
            logger.opt(exception=True).error(f"Error answering question: {e}")
            return f"Error answering question: {str(e)}"

    @mlflow_track(name="QuestionAnswerTool.parse_question")
    def __parse_question(self, question: str) -> str:
        # Handle both JSON and plain string inputs
        try:
            question_dict = json.loads(question)
            return question_dict["question"]
        except (json.JSONDecodeError, KeyError, TypeError):
            # If it's not valid JSON or doesn't have a "question" key, treat it as a plain string
            return question

    def __generate_answer(self, question: str, context: str, sources: list) -> str:
        """
        Generate a comprehensive answer based on the retrieved documents and sources.
        """
        # Create a comprehensive answer with proper citations
        answer_parts = []
        
        # Main answer section
        answer_parts.append(f"Based on the available documents, here's what I found regarding your question: '{question}'")
        answer_parts.append("")
        
        # Add the context documents
        answer_parts.append("Relevant information from the knowledge base:")
        answer_parts.append(context)
        answer_parts.append("")
        
        # Add sources section
        answer_parts.append("Sources:")
        for source in sources:
            answer_parts.append(f"- Document {source['id']}: {source['title']}")
            if source['url'] != "No URL available":
                answer_parts.append(f"  URL: {source['url']}")
        
        answer_parts.append("")
        answer_parts.append("Note: When using information from these documents, please cite the appropriate source using the document ID and URL provided above.")
        
        return "\n".join(answer_parts) 