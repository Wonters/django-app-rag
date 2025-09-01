import json
import uuid
from pathlib import Path
from typing import Any
from django_app_rag.rag.logging_setup import get_logger

logger = get_logger(__name__)
from smolagents import Tool
from django_app_rag.rag.monitoring.mlflow import mlflow_track
from django_app_rag.rag.settings import settings
from openai import OpenAI
import mlflow




class QuestionAnswerTool(Tool):
    name = "question_answer_tool"
    description = """Use this tool to answer questions by processing retrieved documents and providing a concise answer with source citations.
    This tool takes retrieved documents and generates a concise answer with proper source citations using an LLM.
    Best used when you need to:
    - Answer specific questions about topics in the knowledge base
    - Get concise answers with supporting evidence
    - Research complex topics with multiple sources
    - Provide answers that include proper citations and references
    The tool will return a JSON response with a short answer, question_id, and list of sources."""

    inputs = {
        "question": {
            "type": "string",
            "description": """The question to answer. Should be a clear, specific question about information in the knowledge base.
            Examples:
            - "What is the FTI architecture?"
            - "How do vector databases work?"
            - "What are the best practices for RAG implementation?""",
        },
        "retrieved_documents": {
            "type": "string",
            "description": """The documents retrieved by the diskstorage_vector_search_retriever tool.
            This should be the output from the retriever tool containing the relevant documents.""",
        }
    }
    output_type = "string"
    not_found_answer = "Aucun documents"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize OpenAI client for answer generation
        self.client = OpenAI(
            base_url="https://api.openai.com/v1",
            api_key=settings.OPENAI_API_KEY,
        )

    @mlflow_track(name="QuestionAnswerTool.forward")
    def forward(self, question: str, retrieved_documents: str) -> str:
        # Configure MLflow tracking URI if not already set
        if not mlflow.get_tracking_uri() or mlflow.get_tracking_uri().startswith('file://'):
            mlflow.set_tracking_uri("file:///tmp/mlruns")
        
        mlflow.set_tags({"agent": True})
        mlflow.log_dict(
            {
                "question": question,
                "retrieved_documents": retrieved_documents,
            },
            "trace.json",
        )

        try:
            question = self.__parse_question(question)
            
            print(f"🔍 QuestionAnswerTool - Question: {question}")
            print(f"🔍 QuestionAnswerTool - Retrieved documents length: {len(retrieved_documents)}")
            
            # Parse the retrieved documents from the retriever tool output
            documents = self.__parse_retrieved_documents(retrieved_documents)
            
            print(f"🔍 QuestionAnswerTool - Parsed {len(documents)} documents")
            
            if not documents:
                print("❌ QuestionAnswerTool - No documents found")
                return json.dumps([{
                    "answer": "Aucun document pertinent trouvé pour répondre à cette question.",
                    "question_id": str(uuid.uuid4()),
                    "sources": []
                }])

            # Log the number of documents found
            logger.info(f"Processing {len(documents)} retrieved documents")
            print(f"✅ QuestionAnswerTool - Processing {len(documents)} documents")

            # Check if documents have actual content
            documents_with_content = [doc for doc in documents if doc.get("content", "").strip()]
            if not documents_with_content:
                print("❌ QuestionAnswerTool - No documents with content found")
                return json.dumps([{
                    "answer": "Aucun document pertinent trouvé pour répondre à cette question.",
                    "question_id": str(uuid.uuid4()),
                    "sources": []
                }])

            # Extract sources from documents
            sources = []
            context_parts = []
            
            for i, doc in enumerate(documents_with_content, 1):
                # Extraire les informations de groupement des chunks
                chunk_info = doc.get("chunk_info", {})
                
                source_info = {
                    "id": doc.get("id", f"Document {i}"),
                    "title": doc.get("title", f"Document {i}"),
                    "url": doc.get("url", "No URL available"),
                    "similarity_score": doc.get("score")
                }
                
                # Ajouter les informations de groupement si disponibles
                if chunk_info:
                    source_info.update({
                        "is_unique_chunk": chunk_info.get("is_unique_chunk"),
                        "chunk_length": chunk_info.get("chunk_length"),
                        "chunk_preview": chunk_info.get("chunk_preview")
                    })
                    
                    print(f"🔍 QuestionAnswerTool - Document {i}: {doc.get('title', '')[:50]}...")
                    print(f"   📊 Score: {doc.get('score')}")
                    print(f"   📏 Longueur du chunk: {chunk_info.get('chunk_length')} caractères")
                    print(f"   📝 Aperçu: {chunk_info.get('chunk_preview', '')[:80]}...")
                    
                    if not chunk_info.get("is_unique_chunk"):
                        print(f"   ⚠️  Doublon détecté: {chunk_info.get('duplicate_of')}")
                
                sources.append(source_info)
                context_parts.append(doc.get("content", ""))

            # Create context for answer generation
            context = "\n\n".join(context_parts)
            
            print(f"🔍 QuestionAnswerTool - Context length: {len(context)} characters")
            
            # Generate concise answer using LLM
            answer = self.__generate_concise_answer_with_llm(question, context)
            
            logger.info(f"Generated answer: {answer[:100]}...")
            print(f"✅ QuestionAnswerTool - Generated answer: {answer[:100]}...")
            
            # Return JSON response
            response = {
                "answer": answer,
                "question_id": str(uuid.uuid4()),
                "sources": sources
            }
            
            print(f"✅ QuestionAnswerTool - Returning response with {len(sources)} sources")
            
            return json.dumps(response, ensure_ascii=False)
            
        except Exception as e:
            logger.opt(exception=True).error(f"Error answering question: {e}")
            print(f"❌ QuestionAnswerTool - Error: {e}")
            return json.dumps([{
                "answer": f"Error answering question: {str(e)}",
                "question_id": str(uuid.uuid4()),
                "sources": []
            }])

    @mlflow_track(name="QuestionAnswerTool.parse_question")
    def __parse_question(self, question: str) -> str:
        # Handle both JSON and plain string inputs
        try:
            question_dict = json.loads(question)
            return question_dict["question"]
        except (json.JSONDecodeError, KeyError, TypeError):
            # If it's not valid JSON or doesn't have a "question" key, treat it as a plain string
            return question

    def __parse_retrieved_documents(self, retrieved_documents: str) -> list:
        """
        Parse the JSON output from the DiskStorageRetrieverTool to extract document information.
        """
        documents = []
        
        print(f"🔍 QuestionAnswerTool - Parsing documents from: {retrieved_documents[:200]}...")
        
        try:
            # Parse the JSON response from the retriever tool
            data = json.loads(retrieved_documents)
            
            if "documents" in data:
                documents = data["documents"]
                print(f"🔍 QuestionAnswerTool - Found {len(documents)} documents in JSON")
                
                for doc in documents:
                    print(f"🔍 QuestionAnswerTool - Parsed document {doc.get('id')} (score {doc.get('score')}): {doc.get('title', '')[:50]}...")
            else:
                print("❌ QuestionAnswerTool - No 'documents' key found in JSON response")
                
        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing JSON from retrieved documents: {e}")
            print(f"❌ QuestionAnswerTool - Error parsing JSON: {e}")
            
            # Try to handle Python dict representation (single quotes instead of double quotes)
            try:
                # Replace single quotes with double quotes and handle None values
                cleaned_str = retrieved_documents.replace("'", '"').replace('None', 'null')
                data = json.loads(cleaned_str)
                
                if "documents" in data:
                    documents = data["documents"]
                    print(f"🔍 QuestionAnswerTool - Found {len(documents)} documents after cleaning Python dict")
                    
                    for doc in documents:
                        print(f"🔍 QuestionAnswerTool - Parsed documents {doc.get('id')} (score {doc.get('score')}): {doc.get('title', '')[:50]}...")
                else:
                    print("❌ QuestionAnswerTool - No 'documents' key found in cleaned data")
                    # Fallback: try to extract any text content
                    documents.append({
                        "id": None,
                        "title": "Retrieved Document",
                        "url": "No URL available",
                        "score": None,
                        "content": retrieved_documents
                    })
                    
            except Exception as cleanup_error:
                logger.warning(f"Error parsing cleaned retrieved documents: {cleanup_error}")
                print(f"❌ QuestionAnswerTool - Error parsing cleaned documents: {cleanup_error}")
                # Fallback: try to extract any text content
                documents.append({
                    "id": None,
                    "title": "Retrieved Document",
                    "url": "No URL available",
                    "score": None,
                    "content": retrieved_documents
                })
        except Exception as e:
            logger.warning(f"Error parsing retrieved documents: {e}")
            print(f"❌ QuestionAnswerTool - Error parsing documents: {e}")
            # Fallback: try to extract any text content
            documents.append({
                "id": None,
                "title": "Retrieved Document",
                "url": "No URL available",
                "score": None,
                "content": retrieved_documents
            })
        
        print(f"✅ QuestionAnswerTool - Successfully parsed {len(documents)} documents")
        return documents

    def __generate_concise_answer_with_llm(self, question: str, context: str) -> str:
        """
        Generate a concise answer using LLM based on the retrieved documents.
        """
        if not context.strip():
            print("❌ QuestionAnswerTool - Empty context, returning 'Aucun documents'")
            return "Aucun documents"
        
        print(f"🔍 QuestionAnswerTool - Generating answer for question: {question}")
        print(f"🔍 QuestionAnswerTool - Context preview: {context[:200]}...")
        
        # Prompt for concise answer generation
        answer_prompt = f"""
        Question: {question}
        
        Context from retrieved documents:
        {context}
        
        Based on the context above, provide a concise, short and accurate answer to the question. 
        The answer should be clear, factual, and directly address the question.
        Keep the answer brief but informative. The answer should be less than 100 words.
        
        If the documents do not contain relevant information to answer the question, respond with "Aucun documents".
        
        Answer:
        """
        
        try:
            print("🔍 QuestionAnswerTool - Calling LLM...")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": answer_prompt}]
            )
            answer = response.choices[0].message.content.strip()
            
            print(f"🔍 QuestionAnswerTool - LLM response: {answer[:200]}...")
            
            # Check if the answer indicates no relevant information
            if "aucun document" in answer.lower() or "no relevant" in answer.lower() or "cannot answer" in answer.lower():
                print("❌ QuestionAnswerTool - LLM indicated no relevant information")
                return self.not_found_answer
            
            print(f"✅ QuestionAnswerTool - Generated answer successfully")
            return answer
        except Exception as e:
            logger.error(f"Error generating answer with LLM: {e}")
            print(f"❌ QuestionAnswerTool - Error generating answer with LLM: {e}")
            return "Error generating answer" 