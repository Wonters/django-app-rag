import pytest
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage
from django_app_rag.rag.models import Document
from django_app_rag.rag.retrievers import get_retriever
from typing import List, Dict, Any, Optional
from loguru import logger


class TestRetriever:
    """Classe pour tester les fonctionnalités du retriever FAISS"""
    
    def setup_method(self):
        self.retriever = get_retriever(
            embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
            embedding_model_type="huggingface",
            retriever_type="parent",
            k=3,
            device="cpu",
            vectorstore="faiss",
            persistent_path="media/rag_data/1"
        )
    
    def teardown_method(self):
        self.retriever = None

    def test_disk_storage(self):
        storage = DiskStorage(model_class=Document, collection_name="Low_Tech_1", data_dir="media/rag_data/1")
        documents = storage.read()
        print(f"Documents: {documents}")
        assert len(documents) > 0

    def test_retriever(self):
        documents = self.retriever.invoke("Comment brancher les APSDS3 quelles puissances ? ")
        assert len(documents) > 0

    def test_question_answer(self):
        question = "Comment brancher les APSDS3 quelles puissances ? "
        answer = self.retriever.question_answer(question)
        print(f"Réponse: {answer}")
        assert len(answer) > 0

    def test_index_faiss(self):
        print("=== Test avec invoke ===")
        try:
            documents_invoke = self.retriever.invoke("panneaux solaire")
            print(f"Nombre de documents trouvés avec invoke: {len(documents_invoke)}")
            for i, doc in enumerate(documents_invoke):
                print(f"Document {i+1}:")
                print(f"  Contenu: {doc.page_content[:200]}...")
                print(f"  Métadonnées: {doc.metadata}")
                print()
        except Exception as e:
            print(f"Erreur avec invoke: {e}")

    def test_show_index_info(self):
        """Affiche les informations sur l'index et les documents"""
        vectorstore = self.retriever.vectorstore
        faiss_index = vectorstore.index
        index_to_docstore_id = vectorstore.index_to_docstore_id
        docstore = vectorstore.docstore
        
        print("=== Informations sur l'index FAISS ===")
        print(f"Type d'index: {type(faiss_index)}")
        print(f"Nombre total de vecteurs: {faiss_index.ntotal}")
        print(f"Dimension des vecteurs: {faiss_index.d}")
        print(f"Index vide: {faiss_index.ntotal == 0}")
        
        print(f"\n=== Mapping index vers document ID ===")
        print(f"Nombre d'entrées dans le mapping: {len(index_to_docstore_id)}")
        
        # Afficher les premiers IDs de documents
        if index_to_docstore_id:
            print("Premiers IDs de documents:")
            for i, doc_id in list(index_to_docstore_id.items())[:10]:
                print(f"  Index {i} -> Document ID: {doc_id}")
        
        print(f"\n=== Documents dans le docstore ===")
        print(f"Nombre de documents: {len(docstore._dict)}")
        
        # Afficher les premiers documents
        if docstore._dict:
            print("Premiers documents:")
            for i, (doc_id, doc) in enumerate(list(docstore._dict.items())[:5]):
                print(f"\nDocument {i+1} (ID: {doc_id}):")
                print(f"  Contenu: {doc.page_content[:200]}...")
                print(f"  Métadonnées: {doc.metadata}")
        
        # Vérifications
        assert faiss_index.ntotal > 0, "L'index FAISS devrait contenir des vecteurs"
        assert len(docstore._dict) > 0, "Le docstore devrait contenir des documents"
        assert len(index_to_docstore_id) > 0, "Le mapping devrait contenir des entrées"


    def test_vectorstore_search(self):
        """Test de recherche directe dans le vector store FAISS"""
        # Accéder directement au vector store
        vectorstore = self.retriever.vectorstore
        
        print("=== Test de recherche directe dans le vector store ===")
        
        # Recherche par similarité
        query = "panneaux solaire"
        results = vectorstore.similarity_search(query, k=3)
        
        print(f"Recherche pour: '{query}'")
        print(f"Nombre de résultats: {len(results)}")
        
        for i, doc in enumerate(results):
            print(f"Résultat {i+1}:")
            print(f"  Contenu: {doc.page_content[:50]}...")
            print(f"  Métadonnées: {doc.metadata}")
            print()
        
        # Recherche avec scores
        print("=== Recherche avec scores ===")
        results_with_scores = vectorstore.similarity_search_with_score(query, k=3)
        
        for i, (doc, score) in enumerate(results_with_scores):
            print(f"Résultat {i+1} (score: {score:.4f}):")
            print(f"  Contenu: {doc.page_content[:200]}...")
            print(f"  Métadonnées: {doc.metadata}")
            print()
        
        # Vérifications
        assert isinstance(results, list), "Les résultats devraient être une liste"
        assert len(results) > 0, "Il devrait y avoir au moins un résultat pour 'panneaux solaire'"
        assert isinstance(results_with_scores, list), "Les résultats avec scores devraient être une liste"
        assert len(results_with_scores) > 0, "Il devrait y avoir au moins un résultat avec scores"

