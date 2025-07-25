import os.path
from loguru import logger
import faiss
from typing import Any, Dict, List, Optional
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain_core.stores import InMemoryStore
from langchain.docstore.in_memory import InMemoryDocstore
from langchain.retrievers.parent_document_retriever import ParentDocumentRetriever
from langchain_text_splitters import TextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain.retrievers.multi_vector import SearchType


class FaissParentDocumentRetriever(ParentDocumentRetriever):
    """Un ParentDocumentRetriever qui utilise FAISS en back-end."""
    # docstore: InMemoryStore

    def __init__(
        self,
        embedding_model: Embeddings,
        child_splitter: TextSplitter,
        parent_splitter: Optional[TextSplitter] = None,
        index_factory_str: str = "Flat",
        normalize_L2: bool = True,
        search_kwargs: Optional[Dict[str, Any]] = None,
        persistent_path:str ="faiss_store/"
    ):
        # VectorStore FAISS instanciation
        if os.path.exists(persistent_path):
            vectorstore = FAISS.load_local(persistent_path,
                             embeddings=embedding_model,
                             index_name="index",
                             allow_dangerous_deserialization=True)
            logger.info(f"Vectorstore loaded from {persistent_path}")
        else:
            # Find dimension encoding dummy
            dummy_vec = embedding_model.embed_query(" ")
            dim = len(dummy_vec)

            # Empty faiss index, no normalization L2 to apply
            index = faiss.index_factory(dim, index_factory_str, faiss.METRIC_INNER_PRODUCT)
            vectorstore = FAISS(
                embedding_function=embedding_model,
                index=index,
                index_to_docstore_id={},
                docstore=InMemoryDocstore(),
                relevance_score_fn=None,
                normalize_L2=normalize_L2,
            )


        super().__init__(
            vectorstore=vectorstore,
            docstore=InMemoryStore(),#todo: use MongoDBStore to save documents on Mongo
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
            search_kwargs=search_kwargs or {},
        )
        self._persistent_path = persistent_path

    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding: Embeddings,
        child_splitter: TextSplitter,
        parent_splitter: Optional[TextSplitter] = None,
        index_factory_str: str = "Flat",
        normalize_L2: bool = True,
        search_kwargs: Optional[Dict[str, Any]] = None,
    ) -> "FaissParentDocumentRetriever":
        """
        Retriever factory : create object, add all documents,
        et return a ready to use instance.
        """
        retriever = cls(
            embedding_model=embedding,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
            index_factory_str=index_factory_str,
            normalize_L2=normalize_L2,
            search_kwargs=search_kwargs,
        )
        # Cette méthode split automatiquement vos docs en parents/enfants,
        # index les enfants dans FAISS et stock les parents dans le docstore.
        retriever.add_documents(documents)
        return retriever

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        child_splitter: TextSplitter,
        parent_splitter: Optional[TextSplitter] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        index_factory_str: str = "Flat",
        normalize_L2: bool = True,
        search_kwargs: Optional[Dict[str, Any]] = None,
    ) -> "FaissParentDocumentRetriever":
        """
        Usine à retriever : construit des Documents à partir de `texts` et `metadatas`,
        puis délègue à from_documents.
        """
        # Validation des métadonnées
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError(
                f"Le nombre de metadatas ({len(metadatas)}) ne correspond "
                f"pas au nombre de textes ({len(texts)})"
            )
        # Création des Document
        docs: List[Document] = []
        for i, txt in enumerate(texts):
            meta = metadatas[i] if metadatas else {}
            docs.append(Document(page_content=txt, metadata=meta))
        # Délégation à from_documents
        return cls.from_documents(
            documents=docs,
            embedding=embedding,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
            index_factory_str=index_factory_str,
            normalize_L2=normalize_L2,
            search_kwargs=search_kwargs,
        )

    def add_documents(
            self,
            documents: list[Document],
            ids: Optional[list[str]] = None,
            add_to_docstore: bool = True,
            **kwargs: Any,
    ) -> None:
        logger.info(f"Adding documents to vectorstore")
        # Embed documents and add to vectorstore
        super().add_documents(documents, ids, add_to_docstore, **kwargs)
        # Save vectorstore on disk to persistency
        # Avoid compute embeddings every time
        logger.info(f"Saving vectorstore to {self._persistent_path}")
        self.vectorstore.save_local(self._persistent_path)


    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Get documents relevant to a query.
        Args:
            query: String to find relevant documents for
            run_manager: The callbacks handler to use
        Returns:
            List of relevant documents
        """
        if self.search_type == SearchType.mmr:
            sub_docs = self.vectorstore.max_marginal_relevance_search(
                query, **self.search_kwargs
            )
        elif self.search_type == SearchType.similarity_score_threshold:
            sub_docs_and_similarities = (
                self.vectorstore.similarity_search_with_relevance_scores(
                    query, **self.search_kwargs
                )
            )
            logger.info(f"Scores: {[score for _, score in sub_docs_and_similarities]}")
            sub_docs = [sub_doc for sub_doc, _ in sub_docs_and_similarities]
        else:
            sub_docs = self.vectorstore.similarity_search(query, **self.search_kwargs)
            logger.info(f"Sub_docs: {sub_docs}")
        # On retourne directement les documents trouvés par la recherche vectorielle
        return sub_docs