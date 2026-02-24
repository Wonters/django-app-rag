import os.path
from contextlib import contextmanager
from pathlib import Path
from django_app_rag.logging import get_logger_loguru
import faiss
from typing import Any, Dict, List, Optional
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain_core.stores import InMemoryStore
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain.retrievers.parent_document_retriever import ParentDocumentRetriever
from langchain_text_splitters import TextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain.retrievers.multi_vector import SearchType
from django_app_rag.rag.infrastructur.faiss.persistent_store import SQLiteDocStore
from django_app_rag.path_utils import ensure_path, ensure_str, safe_join

logger = get_logger_loguru(__name__)


class FaissParentDocumentRetriever(ParentDocumentRetriever):
    """Un ParentDocumentRetriever qui utilise FAISS en back-end.

    Améliorations par rapport à la version de base :
    - context manager batch_indexing() pour bufferiser les writes FAISS
    - Reranking optionnel via CrossEncoder (sentence-transformers)
    - Retrieval hybride optionnel : dense (FAISS) + sparse (BM25) avec fusion RRF
    - Logging réduit au niveau DEBUG pour les diagnostics verbeux
    """

    def __init__(
        self,
        embedding_model: Embeddings,
        child_splitter: TextSplitter,
        parent_splitter: Optional[TextSplitter] = None,
        index_factory_str: str = "Flat",
        normalize_L2: bool = True,
        search_kwargs: Optional[Dict[str, Any]] = None,
        persistent_path: str = "data/",
        similarity_score_threshold: float = 0.5,
        reranker_model_id: Optional[str] = None,
        use_hybrid_retrieval: bool = False,
    ):
        persistent_path = safe_join(ensure_path(persistent_path), "faiss_store")
        # VectorStore FAISS instanciation
        if os.path.exists(persistent_path):
            vectorstore = FAISS.load_local(
                ensure_str(persistent_path),
                embeddings=embedding_model,
                index_name="index",
                allow_dangerous_deserialization=True,
            )
            logger.info(f"Vectorstore loaded from {persistent_path}")
        else:
            # Find dimension by encoding a dummy vector
            dummy_vec = embedding_model.embed_query(" ")
            dim = len(dummy_vec)

            index = faiss.index_factory(dim, index_factory_str, faiss.METRIC_INNER_PRODUCT)
            vectorstore = FAISS(
                embedding_function=embedding_model,
                index=index,
                index_to_docstore_id={},
                docstore=InMemoryDocstore(),
                relevance_score_fn=None,
                normalize_L2=normalize_L2,
            )

        # Initialize persistent docstore using SQLite
        docstore_path = safe_join(persistent_path, "parent_docstore.db")
        docstore = SQLiteDocStore(ensure_str(docstore_path))
        logger.info(f"Using persistent SQLiteDocStore at {docstore_path}")

        super().__init__(
            vectorstore=vectorstore,
            docstore=docstore,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
            search_kwargs=search_kwargs or {},
        )
        self._persistent_path = persistent_path
        self._similarity_score_threshold = similarity_score_threshold
        self._reranker_model_id = reranker_model_id
        self._use_hybrid = use_hybrid_retrieval
        # Mutable runtime state (not Pydantic fields)
        self._batch_mode = False
        self._reranker_instance = None
        self._bm25_instance = None

        if self._similarity_score_threshold is not None:
            self.search_type = SearchType.similarity_score_threshold

    @contextmanager
    def batch_indexing(self):
        """Context manager pour bufferiser les writes FAISS.

        Permet d'ajouter des milliers de documents sans écrire sur disque
        à chaque batch, puis de sauvegarder une seule fois à la fin.

        Usage:
            with retriever.batch_indexing():
                for batch in document_batches:
                    retriever.add_documents(batch)
            # save_local() est appelé ici, une seule fois
        """
        self._batch_mode = True
        try:
            yield self
        finally:
            self._batch_mode = False
            logger.info(f"Batch indexing complete, saving vectorstore to {self._persistent_path}")
            self.vectorstore.save_local(self._persistent_path)

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
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError(
                f"Le nombre de metadatas ({len(metadatas)}) ne correspond "
                f"pas au nombre de textes ({len(texts)})"
            )
        docs: List[Document] = []
        for i, txt in enumerate(texts):
            meta = metadatas[i] if metadatas else {}
            docs.append(Document(page_content=txt, metadata=meta))
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
        logger.info(f"Adding {len(documents)} documents to vectorstore")

        self._validate_document_ids(documents)
        self._validate_batch_not_already_indexed(documents)

        super().add_documents(documents, ids, add_to_docstore, **kwargs)

        # Invalidate BM25 index so it's rebuilt on next hybrid search
        self._bm25_instance = None

        # T2: Only write to disk when not in batch mode.
        # Use batch_indexing() context manager to defer the save during bulk indexing.
        if not self._batch_mode:
            logger.info(f"Saving vectorstore to {self._persistent_path}")
            self.vectorstore.save_local(self._persistent_path)
        else:
            logger.debug("Batch mode active: deferring vectorstore save")

    def _validate_document_ids(self, documents: list[Document]) -> None:
        """Valide que tous les documents ont des IDs uniques (logs en DEBUG)."""
        from collections import Counter

        all_ids = [doc.metadata.get("id", "unknown") for doc in documents]
        id_counts = Counter(all_ids)
        duplicates = {id_: count for id_, count in id_counts.items() if count > 1}

        if duplicates:
            logger.warning(f"Duplicate IDs detected in batch: {list(duplicates.keys())}")

        docs_without_id = [doc for doc in documents if not doc.metadata.get("id")]
        if docs_without_id:
            logger.warning(f"{len(docs_without_id)} documents have no ID")

        logger.debug(
            f"ID validation: {len(documents)} docs, "
            f"{len(duplicates)} duplicate IDs, {len(docs_without_id)} missing IDs"
        )

    def _validate_batch_not_already_indexed(self, documents: list[Document]) -> None:
        """Avertit si des documents du batch sont déjà dans l'index."""
        batch_ids = {doc.metadata.get("id") for doc in documents if doc.metadata.get("id")}
        if not batch_ids:
            return

        if hasattr(self.vectorstore, "index_to_docstore_id"):
            existing_ids = set(self.vectorstore.index_to_docstore_id.values())
            already_indexed = batch_ids.intersection(existing_ids)
            if already_indexed:
                pct = (len(already_indexed) / len(batch_ids)) * 100
                logger.warning(
                    f"{len(already_indexed)}/{len(batch_ids)} documents ({pct:.0f}%) "
                    f"already indexed - possible duplicate indexing"
                )
            else:
                logger.debug(f"Batch of {len(batch_ids)} documents: no duplicates found")

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Get documents relevant to a query.

        T3: diagnose_index() n'est plus appelé automatiquement à chaque requête.
        Pour diagnostiquer l'index, appelez manuellement retriever.diagnose_index().
        """
        if self._use_hybrid:
            return self._hybrid_search(query)
        return self._dense_search(query)

    def _dense_search(self, query: str) -> list[Document]:
        """Recherche dense FAISS avec filtrage par score et reranking optionnel."""
        if self.search_type == SearchType.mmr:
            sub_docs = self.vectorstore.max_marginal_relevance_search(
                query, **self.search_kwargs
            )
        elif self.search_type == SearchType.similarity_score_threshold:
            sub_docs_and_similarities = self.vectorstore.similarity_search_with_relevance_scores(
                query, **self.search_kwargs
            )
            logger.debug(f"FAISS returned {len(sub_docs_and_similarities)} candidates")

            sub_docs = []
            for doc, score in sub_docs_and_similarities:
                if score > self._similarity_score_threshold:
                    doc.metadata["similarity_score"] = score
                    sub_docs.append(doc)
        else:
            sub_docs = self.vectorstore.similarity_search(query, **self.search_kwargs)

        unique_docs = self._group_similar_chunks(sub_docs)

        # T5: Reranking optionnel via CrossEncoder
        if self._reranker_model_id and unique_docs:
            unique_docs = self._rerank(query, unique_docs)

        logger.info(f"Dense search: {len(unique_docs)} unique docs for query '{query[:60]}'")
        return unique_docs

    def _hybrid_search(self, query: str) -> list[Document]:
        """T6: Retrieval hybride FAISS + BM25 avec fusion RRF.

        Combine la recherche dense (embeddings) et la recherche sparse (BM25)
        pour améliorer le recall sur les termes techniques exacts.
        """
        dense_docs = self._dense_search(query)
        sparse_docs = self._bm25_search(query)

        logger.debug(
            f"Hybrid search: {len(dense_docs)} dense + {len(sparse_docs)} sparse docs"
        )

        merged = self._rrf_merge(dense_docs, sparse_docs)

        k = self.search_kwargs.get("k", 5)
        result = merged[:k]

        logger.info(f"Hybrid search: {len(result)} docs returned after RRF fusion")
        return result

    def _bm25_search(self, query: str) -> list[Document]:
        """Recherche BM25 sur les child documents du docstore FAISS (InMemoryDocstore)."""
        from langchain_community.retrievers import BM25Retriever

        if self._bm25_instance is None:
            child_docs = list(self.vectorstore.docstore._dict.values())
            if not child_docs:
                logger.debug("BM25: no child documents available in FAISS docstore")
                return []
            k = self.search_kwargs.get("k", 5)
            self._bm25_instance = BM25Retriever.from_documents(child_docs, k=k)
            logger.debug(f"BM25 index built from {len(child_docs)} child documents")

        try:
            return self._bm25_instance.invoke(query)
        except Exception as e:
            logger.warning(f"BM25 search failed, falling back to dense only: {e}")
            return []

    def _rrf_merge(
        self,
        dense_docs: list[Document],
        sparse_docs: list[Document],
        rrf_k: int = 60,
    ) -> list[Document]:
        """Reciprocal Rank Fusion : fusionne les résultats dense et sparse.

        Score RRF = sum(1 / (k + rank)) pour chaque retriever.
        Un document dans les deux listes obtient un score plus élevé.
        """
        scores: dict[int, float] = {}
        doc_map: dict[int, Document] = {}

        for rank, doc in enumerate(dense_docs):
            key = hash(doc.page_content.strip())
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            doc_map[key] = doc

        for rank, doc in enumerate(sparse_docs):
            key = hash(doc.page_content.strip())
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            if key not in doc_map:
                doc_map[key] = doc

        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [doc_map[k] for k in sorted_keys]

    def _rerank(self, query: str, docs: list[Document]) -> list[Document]:
        """T5: Reranking des documents via CrossEncoder (sentence-transformers).

        Améliore la précision en reclassant les candidats récupérés
        avant de les envoyer au LLM.
        """
        if not docs or not self._reranker_model_id:
            return docs

        try:
            if self._reranker_instance is None:
                from sentence_transformers import CrossEncoder

                self._reranker_instance = CrossEncoder(self._reranker_model_id)
                logger.info(f"CrossEncoder reranker loaded: {self._reranker_model_id}")

            pairs = [(query, doc.page_content) for doc in docs]
            scores = self._reranker_instance.predict(pairs)

            ranked = sorted(zip(scores, docs), key=lambda x: float(x[0]), reverse=True)
            for score, doc in ranked:
                doc.metadata["rerank_score"] = float(score)

            logger.debug(f"Reranked {len(docs)} documents")
            return [doc for _, doc in ranked]

        except Exception as e:
            logger.warning(f"Reranking failed, returning original order: {e}")
            return docs

    def _group_similar_chunks(self, chunks: list[Document]) -> list[Document]:
        """Déduplique les chunks par hash de contenu et par ID."""
        if not chunks:
            return []

        chunks.sort(key=lambda x: x.metadata.get("similarity_score", 0), reverse=True)

        unique: list[Document] = []
        seen_ids: set = set()
        seen_hashes: set = set()

        for chunk in chunks:
            chunk_id = chunk.metadata.get("id", "unknown")
            content_hash = hash(chunk.page_content.strip())

            if chunk_id in seen_ids or content_hash in seen_hashes:
                logger.debug(f"Duplicate chunk skipped: ID={chunk_id}")
                continue

            seen_ids.add(chunk_id)
            seen_hashes.add(content_hash)
            chunk.metadata["is_unique_chunk"] = True
            unique.append(chunk)

        logger.debug(f"Dedup: {len(chunks)} -> {len(unique)} unique chunks")
        return unique

    def diagnose_index(self) -> None:
        """Diagnostic de l'index FAISS.

        Méthode utilitaire pour le debugging manuel.
        N'est plus appelée automatiquement à chaque requête (T3).

        Usage: retriever.diagnose_index()
        """
        try:
            faiss_index = self.vectorstore.index
            index_to_docstore_id = self.vectorstore.index_to_docstore_id
            docstore_ids = list(index_to_docstore_id.values())
            duplicate_count = len(docstore_ids) - len(set(docstore_ids))

            logger.info(
                f"FAISS index diagnostic: ntotal={faiss_index.ntotal}, "
                f"dim={faiss_index.d}, mapping_entries={len(index_to_docstore_id)}, "
                f"duplicates={duplicate_count}"
            )

            if hasattr(self.vectorstore, "docstore") and hasattr(
                self.vectorstore.docstore, "_dict"
            ):
                logger.info(
                    f"FAISS child docstore: {len(self.vectorstore.docstore._dict)} documents"
                )

            if duplicate_count > 0:
                from collections import Counter

                id_counts = Counter(docstore_ids)
                dupes = {id_: c for id_, c in id_counts.items() if c > 1}
                logger.warning(f"Duplicate IDs in FAISS mapping: {dupes}")

        except Exception as e:
            logger.error(f"Index diagnosis failed: {e}")
