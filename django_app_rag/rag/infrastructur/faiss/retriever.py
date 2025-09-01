import os.path
from pathlib import Path
from django_app_rag.rag.logging_setup import get_logger

logger = get_logger(__name__)
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
        persistent_path:str ="data/",
        similarity_score_threshold: float = 0.5,
    ):
        persistent_path = Path(persistent_path) / "faiss_store"
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
        self._similarity_score_threshold = similarity_score_threshold
        if self._similarity_score_threshold is not None:
            self.search_type = SearchType.similarity_score_threshold

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
        
        # Vérifier les IDs avant l'ajout
        self._validate_document_ids(documents)
        
        # Embed documents and add to vectorstore
        super().add_documents(documents, ids, add_to_docstore, **kwargs)
        # Save vectorstore on disk to persistency
        # Avoid compute embeddings every time
        logger.info(f"Saving vectorstore to {self._persistent_path}")
        self.vectorstore.save_local(self._persistent_path)

    def _validate_document_ids(self, documents: list[Document]):
        """
        Valide que tous les documents ont des IDs uniques.
        """
        logger.info(f"🔍 Validation des IDs pour {len(documents)} documents")
        
        # Collecter tous les IDs
        all_ids = []
        for doc in documents:
            doc_id = doc.metadata.get("id", "unknown")
            all_ids.append(doc_id)
        
        # Vérifier les doublons
        unique_ids = set(all_ids)
        duplicate_count = len(all_ids) - len(unique_ids)
        
        if duplicate_count > 0:
            logger.error(f"🚨 DOUBLONS DÉTECTÉS DANS LES DOCUMENTS À INDEXER: {duplicate_count} IDs dupliqués!")
            
            # Trouver les IDs dupliqués
            from collections import Counter
            id_counts = Counter(all_ids)
            duplicates = {id_: count for id_, count in id_counts.items() if count > 1}
            
            for id_, count in duplicates.items():
                logger.error(f"   - ID '{id_}' apparaît {count} fois")
                
                # Afficher les contenus des chunks dupliqués
                duplicate_docs = [doc for doc in documents if doc.metadata.get("id") == id_]
                for i, doc in enumerate(duplicate_docs):
                    content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                    logger.error(f"     Chunk {i+1}: '{content_preview}'")
        else:
            logger.info("✅ Tous les documents ont des IDs uniques")
        
        # Vérifier que tous les documents ont un ID
        docs_without_id = [doc for doc in documents if not doc.metadata.get("id")]
        if docs_without_id:
            logger.warning(f"⚠️  {len(docs_without_id)} documents sans ID détectés")
        else:
            logger.info("✅ Tous les documents ont un ID")

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Get documents relevant to a query.
        Args:
            query: String to find relevant documents for
            run_manager: The callbacks manager to use
        Returns:
            List of relevant documents
        """
        # Diagnostic de l'index au début de la recherche
        self.diagnose_index()
        
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
            
            # Logging pour diagnostiquer le problème de duplication
            logger.info(f"Recherche FAISS retourne {len(sub_docs_and_similarities)} résultats")
            
            # Analyser les résultats pour détecter les doublons
            chunk_ids_seen = set()
            duplicate_chunks = []
            
            for doc, score in sub_docs_and_similarities:
                chunk_id = doc.metadata.get("id", "unknown")
                if chunk_id in chunk_ids_seen:
                    duplicate_chunks.append((chunk_id, score))
                    logger.warning(f"⚠️  CHUNK DUPLIQUÉ DÉTECTÉ: ID {chunk_id} avec score {score}")
                else:
                    chunk_ids_seen.add(chunk_id)
                    logger.info(f"✅ Chunk unique: ID {chunk_id} avec score {score}")
            
            if duplicate_chunks:
                logger.error(f"🚨 {len(duplicate_chunks)} chunks dupliqués détectés dans les résultats FAISS!")
                for chunk_id, score in duplicate_chunks:
                    logger.error(f"   - ID: {chunk_id}, Score: {score}")
            
            # Filter documents with similarity score > threshold and add score to metadata
            filtered_docs = []
            for doc, score in sub_docs_and_similarities:
                if score > self._similarity_score_threshold:
                    # Create a copy of the document with score in metadata
                    doc.metadata["similarity_score"] = score
                    filtered_docs.append(doc)
            sub_docs = filtered_docs
        else:
            sub_docs = self.vectorstore.similarity_search(query, **self.search_kwargs)
        
        # Grouper les chunks par contenu similaire pour éviter la duplication
        grouped_docs = self._group_similar_chunks(sub_docs)
        
        return grouped_docs

    def _group_similar_chunks(self, chunks: list[Document]) -> list[Document]:
        """
        Groupe les chunks par contenu similaire pour éviter la duplication.
        Utilise une approche basée sur la similarité du contenu plutôt que sur les IDs.
        """
        if not chunks:
            return []
        
        logger.info(f"🔍 Début du groupement de {len(chunks)} chunks")
        
        # Trier par score décroissant
        chunks.sort(key=lambda x: x.metadata.get("similarity_score", 0), reverse=True)
        
        # Logging détaillé de chaque chunk avant groupement
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.metadata.get("id", "unknown")
            score = chunk.metadata.get("similarity_score", "unknown")
            content_preview = chunk.page_content[:50] + "..." if len(chunk.page_content) > 50 else chunk.page_content
            logger.info(f"   Chunk {i+1}: ID={chunk_id}, Score={score}, Contenu='{content_preview}'")
        
        grouped_chunks = []
        used_content_hashes = set()
        used_chunk_ids = set()
        
        for chunk in chunks:
            chunk_id = chunk.metadata.get("id", "unknown")
            content_hash = hash(chunk.page_content.strip())
            
            logger.info(f"🔍 Traitement du chunk ID={chunk_id}, Hash={content_hash}")
            
            # Vérifier si on a déjà vu ce chunk ID
            if chunk_id in used_chunk_ids:
                logger.warning(f"⚠️  Chunk ID déjà vu: {chunk_id}")
                chunk.metadata.update({
                    "is_unique_chunk": False,
                    "content_hash": content_hash,
                    "duplicate_of": f"Chunk ID {chunk_id} déjà présent",
                    "duplicate_type": "id_duplicate"
                })
                continue
            
            # Vérifier si on a déjà vu ce contenu
            if content_hash in used_content_hashes:
                logger.warning(f"⚠️  Contenu déjà vu pour le chunk ID: {chunk_id}")
                chunk.metadata.update({
                    "is_unique_chunk": False,
                    "content_hash": content_hash,
                    "duplicate_of": "Contenu identique déjà présent",
                    "duplicate_type": "content_duplicate"
                })
                continue
            
            # Chunk unique
            used_content_hashes.add(content_hash)
            used_chunk_ids.add(chunk_id)
            
            # Enrichir les métadonnées avec des informations utiles
            chunk.metadata.update({
                "is_unique_chunk": True,
                "content_hash": content_hash,
                "chunk_length": len(chunk.page_content),
                "chunk_preview": chunk.page_content[:100] + "..." if len(chunk.page_content) > 100 else chunk.page_content
            })
            
            grouped_chunks.append(chunk)
            logger.info(f"✅ Chunk {chunk_id} ajouté au groupe (unique)")
        
        logger.info(f"🎯 Groupement terminé: {len(chunks)} chunks → {len(grouped_chunks)} chunks uniques")
        return grouped_chunks

    def diagnose_index(self):
        """
        Méthode de diagnostic pour examiner l'index FAISS et détecter les problèmes.
        """
        logger.info("🔍 === DIAGNOSTIC DE L'INDEX FAISS ===")
        
        try:
            # Informations sur l'index FAISS
            faiss_index = self.vectorstore.index
            logger.info(f"📊 Type d'index FAISS: {type(faiss_index)}")
            logger.info(f"📊 Nombre total de vecteurs: {faiss_index.ntotal}")
            logger.info(f"📊 Dimension des vecteurs: {faiss_index.d}")
            
            # Informations sur le mapping
            index_to_docstore_id = self.vectorstore.index_to_docstore_id
            logger.info(f"📊 Nombre d'entrées dans le mapping: {len(index_to_docstore_id)}")
            
            # Vérifier les doublons dans le mapping
            docstore_ids = list(index_to_docstore_id.values())
            unique_ids = set(docstore_ids)
            duplicate_count = len(docstore_ids) - len(unique_ids)
            
            if duplicate_count > 0:
                logger.error(f"🚨 DOUBLONS DÉTECTÉS DANS LE MAPPING: {duplicate_count} entrées dupliquées!")
                
                # Trouver les IDs dupliqués
                from collections import Counter
                id_counts = Counter(docstore_ids)
                duplicates = {id_: count for id_, count in id_counts.items() if count > 1}
                
                for id_, count in duplicates.items():
                    logger.error(f"   - ID '{id_}' apparaît {count} fois")
            else:
                logger.info("✅ Aucun doublon détecté dans le mapping")
            
            # Informations sur le docstore
            if hasattr(self.vectorstore, 'docstore'):
                docstore = self.vectorstore.docstore
                if hasattr(docstore, '_dict'):
                    logger.info(f"📊 Nombre de documents dans le docstore: {len(docstore._dict)}")
                    
                    # Vérifier les doublons dans le docstore
                    docstore_ids = list(docstore._dict.keys())
                    unique_docstore_ids = set(docstore_ids)
                    docstore_duplicate_count = len(docstore_ids) - len(unique_docstore_ids)
                    
                    if docstore_duplicate_count > 0:
                        logger.error(f"🚨 DOUBLONS DÉTECTÉS DANS LE DOCSTORE: {docstore_duplicate_count} entrées dupliquées!")
                    else:
                        logger.info("✅ Aucun doublon détecté dans le docstore")
            
            logger.info("🔍 === FIN DU DIAGNOSTIC ===")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du diagnostic: {e}")
            logger.opt(exception=True).error("Détails de l'erreur:")