import json
from pathlib import Path
import yaml
from loguru import logger
from smolagents import Tool
from django_app_rag.rag.monitoring.mlflow import mlflow_track
from django_app_rag.rag.retrievers import get_retriever
import mlflow


class DiskStorageRetrieverTool(Tool):
    name = "diskstorage_vector_search_retriever"
    description = """Use this tool to search and retrieve relevant documents from a knowledge base using semantic search.
    This tool performs similarity-based search to find the most relevant documents matching the query.
    Best used when you need to:
    - Find specific information from stored documents
    - Get context about a topic
    - Research historical data or documentation
    The tool will return multiple relevant document snippets."""

    inputs = {
        "query": {
            "type": "string",
            "description": """The search query to find relevant documents for using semantic search.
            Should be a clear, specific question or statement about the information you're looking for.""",
        }
    }
    output_type = "string"

    def __init__(self, config_path: Path, **kwargs):
        super().__init__(**kwargs)

        self.config_path = config_path
        self.retriever = self.__load_retriever(config_path)

    def __load_retriever(self, config_path: Path):
        config = yaml.safe_load(config_path.read_text())

        return get_retriever(
            embedding_model_id=config["embedding_model_id"],
            embedding_model_type=config["embedding_model_type"],
            retriever_type=config["retriever_type"],
            k=5,
            device=config["device"],
            persistent_path=config["data_dir"],
            similarity_score_threshold=config.get("similarity_score_threshold", 0.5),
        )

    @mlflow_track(name="DiskStorageRetrieverTool.forward")
    def forward(self, query: str) -> str:
        # Configure MLflow tracking URI if not already set
        if not mlflow.get_tracking_uri() or mlflow.get_tracking_uri().startswith('file://'):
            # Set to local file system if no tracking server is configured
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
            },
            "trace.json",
        )

        try:
            query = self.__parse_query(query)
            print(f"🔍 DiskStorageRetrieverTool - Searching for query: {query}")
            
            relevant_docs = self.retriever.invoke(query)

            # Log the number of documents found after filtering
            logger.info(f"Found {len(relevant_docs)} documents with similarity score > {self.retriever._similarity_score_threshold * 100:.0f}%")
            print(f"✅ DiskStorageRetrieverTool - Found {len(relevant_docs)} documents")

            formatted_docs = []
            for i, doc in enumerate(relevant_docs, 1):
                # Get the similarity score if available
                formatted_docs.append({
                    "id": doc.metadata.get("id", f"Document {i}"),
                    "title": doc.metadata.get("title", f"Document {i}"),
                    "url": doc.metadata.get("url", "No URL available"),
                    "score": doc.metadata.get("similarity_score", None),
                    "content": doc.page_content.strip()
                })

            result = {
                "documents": formatted_docs,
                "total_count": len(formatted_docs),
                "message": f"Found {len(formatted_docs)} relevant documents. When using context from any document, also include the document URL as reference."
            }
            
            json_result = json.dumps(result, ensure_ascii=False)
            print(f"✅ DiskStorageRetrieverTool - Returning JSON with {len(formatted_docs)} documents")
            return json_result
        except Exception as e:
            logger.opt(exception=True).error(f"Error retrieving documents: {e}")
            
            # Return structured JSON even in case of error for compatibility with question_answer_tool
            error_result = {
                "documents": [],
                "total_count": 0,
                "message": f"Error retrieving documents: {str(e)}"
            }
            
            return json.dumps(error_result, ensure_ascii=False)

    @mlflow_track(name="DiskStorageRetrieverTool.parse_query")
    def __parse_query(self, query: str) -> str:
        # Handle both JSON and plain string inputs
        try:
            query_dict = json.loads(query)
            return query_dict["query"]
        except (json.JSONDecodeError, KeyError, TypeError):
            # If it's not valid JSON or doesn't have a "query" key, treat it as a plain string
            return query
