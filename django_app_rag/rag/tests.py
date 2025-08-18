import pytest
from django_app_rag.rag.infrastructur.disk_storage import DiskStorage
from django_app_rag.rag.models import Document
from django_app_rag.rag.retrievers import get_retriever
from typing import List, Dict, Any, Optional
from loguru import logger
from django_app_rag.rag.agents.tools import get_agent
from pathlib import Path
import json
import time
from concurrent.futures import ThreadPoolExecutor
from django_app_rag.models import (
    Source,
    Question,
    Collection,
    Document as DocumentModel,
    Answer,
)
from django.core.files.base import ContentFile
from django.core.files import File
from django_app_rag.rag.agents.tools import QuestionAnswerTool, DiskStorageRetrieverTool


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
            persistent_path="media/rag_data/1",
        )

    def teardown_method(self):
        self.retriever = None

    def test_disk_storage(self):
        storage = DiskStorage(
            model_class=Document,
            collection_name="Low_Tech_1",
            data_dir="media/rag_data/1",
        )
        documents = storage.read()
        print(f"Documents: {documents}")
        assert len(documents) > 0

    def test_retriever(self):
        documents = self.retriever.invoke(
            "Comment brancher les APSDS3 quelles puissances ? "
        )
        assert len(documents) > 0

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
        assert (
            len(results) > 0
        ), "Il devrait y avoir au moins un résultat pour 'panneaux solaire'"
        assert isinstance(
            results_with_scores, list
        ), "Les résultats avec scores devraient être une liste"
        assert (
            len(results_with_scores) > 0
        ), "Il devrait y avoir au moins un résultat avec scores"

    def test_score_filtering(self):
        """Test du filtrage des documents par score de similarité"""
        print("=== Test du filtrage par score ===")

        query = "panneaux solaire"
        threshold = self.retriever.similarity_score_threshold

        # Test avec le retriever qui applique le filtrage
        filtered_results = self.retriever.invoke(query)
        print(
            f"Documents après filtrage (>{threshold*100:.0f}%): {len(filtered_results)}"
        )

        # Test direct avec le vectorstore pour voir tous les scores
        vectorstore = self.retriever.vectorstore
        all_results_with_scores = vectorstore.similarity_search_with_relevance_scores(
            query, k=10
        )

        print("Tous les scores avant filtrage:")
        for i, (doc, score) in enumerate(all_results_with_scores):
            status = "✓" if score > threshold else "✗"
            print(f"  {status} Document {i+1}: score = {score:.4f}")

        print(
            f"\nDocuments avec score > {threshold*100:.0f}%: {len([(doc, score) for doc, score in all_results_with_scores if score > threshold])}"
        )
        print(
            f"Documents avec score ≤ {threshold*100:.0f}%: {len([(doc, score) for doc, score in all_results_with_scores if score <= threshold])}"
        )

        # Vérification que le filtrage fonctionne
        assert len(filtered_results) <= len(
            all_results_with_scores
        ), "Le nombre de documents filtrés ne peut pas être supérieur au nombre total"

        # Vérification que tous les documents filtrés ont un score > threshold
        # (Cette vérification nécessiterait d'accéder aux scores dans le retriever,
        # ce qui n'est pas directement possible avec l'interface actuelle)

    def test_document_chunks(self):
        """Test pour vérifier la structure et le contenu des chunks de documents"""
        print("=== Test des chunks de documents ===")

        # Accéder directement aux documents stockés dans le vectorstore
        vectorstore = self.retriever.vectorstore
        docstore = vectorstore.docstore

        print(f"Nombre total de chunks dans le docstore: {len(docstore._dict)}")

        # Vérifier que des documents sont stockés
        assert len(docstore._dict) > 0, "Le docstore devrait contenir au moins un chunk"

        # Lister et analyser tous les chunks
        chunks = list(docstore._dict.values())
        print(f"Chunks disponibles: {len(chunks)}")

        # Vérifier la structure de chaque chunk
        for i, chunk in enumerate(chunks):
            # Vérifications de base sur la structure
            assert hasattr(
                chunk, "page_content"
            ), f"Le chunk {i+1} doit avoir un attribut page_content"
            assert hasattr(
                chunk, "metadata"
            ), f"Le chunk {i+1} doit avoir un attribut metadata"
            assert isinstance(
                chunk.page_content, str
            ), f"Le contenu du chunk {i+1} doit être une chaîne de caractères"
            assert isinstance(
                chunk.metadata, dict
            ), f"Les métadonnées du chunk {i+1} doivent être un dictionnaire"

            # Vérifier que le contenu n'est pas vide
            assert (
                len(chunk.page_content.strip()) > 0
            ), f"Le contenu du chunk {i+1} ne doit pas être vide"

        # Analyser les chunks par document original
        print(f"\n=== Analyse des chunks par document original ===")

        # Créer deux dictionnaires pour regrouper les chunks
        chunks_by_id = {}  # Regroupement par ID de chunk individuel
        chunks_by_doc_id = {}  # Regroupement par ID de document original

        for chunk in chunks:
            # Regroupement par ID de chunk (chaque chunk est unique)
            chunk_id = chunk.metadata["id"]
            if chunk_id not in chunks_by_id:
                chunks_by_id[chunk_id] = []
            chunks_by_id[chunk_id].append(chunk)

            # Regroupement par ID de document original
            doc_id = chunk.metadata["doc_id"]
            if doc_id not in chunks_by_doc_id:
                chunks_by_doc_id[doc_id] = []
            chunks_by_doc_id[doc_id].append(chunk)

        print(f"Nombre de chunks uniques (par ID): {len(chunks_by_id)}")
        print(f"Nombre de documents originaux (par doc_id): {len(chunks_by_doc_id)}")

        # === ANALYSE PAR ID DE CHUNK ===
        print(f"\n🔍 ANALYSE PAR ID DE CHUNK (chunks individuels)")
        print(f"=" * 60)

        # Statistiques par chunk individuel
        chunk_sizes_by_id = []
        for chunk_id, chunk_list in chunks_by_id.items():
            chunk = chunk_list[0]  # Normalement un seul chunk par ID
            if len(chunk_list) > 1:
                print(f"Il y a {len(chunk_list)} chunks pour l'ID {chunk_id}")
            chunk_sizes_by_id.append(len(chunk.page_content))

        # Statistiques globales des chunks
        if chunk_sizes_by_id:
            avg_chunk_size = sum(chunk_sizes_by_id) / len(chunk_sizes_by_id)
            min_chunk_size = min(chunk_sizes_by_id)
            max_chunk_size = max(chunk_sizes_by_id)

            print(f"\n📊 Statistiques des chunks individuels:")
            print(f"  Taille moyenne: {avg_chunk_size:.0f} caractères")
            print(f"  Taille minimale: {min_chunk_size} caractères")
            print(f"  Taille maximale: {max_chunk_size} caractères")
            print(
                f"  Écart-type: {sum((x - avg_chunk_size) ** 2 for x in chunk_sizes_by_id) ** 0.5 / len(chunk_sizes_by_id):.0f} caractères"
            )

        # === ANALYSE PAR DOC_ID (DOCUMENTS ORIGINAUX) ===
        print(f"\n📄 ANALYSE PAR DOC_ID (documents originaux)")
        print(f"=" * 60)

        # Statistiques par document original
        doc_stats = []
        for doc_id, doc_chunks in chunks_by_doc_id.items():
            chunk_sizes = [len(chunk.page_content) for chunk in doc_chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            min_size = min(chunk_sizes)
            max_size = max(chunk_sizes)

            # Stocker les statistiques pour l'analyse globale
            doc_stats.append(
                {
                    "doc_id": doc_id,
                    "chunk_count": len(doc_chunks),
                    "avg_chunk_size": avg_size,
                    "min_chunk_size": min_size,
                    "max_chunk_size": max_size,
                    "total_content_size": sum(chunk_sizes),
                }
            )

        # === STATISTIQUES GLOBALES ===
        print(f"\n🌐 STATISTIQUES GLOBALES")
        print(f"=" * 60)

        # Statistiques des documents
        if doc_stats:
            chunk_counts = [stat["chunk_count"] for stat in doc_stats]
            avg_chunks_per_doc = sum(chunk_counts) / len(chunk_counts)
            min_chunks_per_doc = min(chunk_counts)
            max_chunks_per_doc = max(chunk_counts)

            print(f"📊 Répartition des chunks par document:")
            print(f"  Nombre moyen de chunks par document: {avg_chunks_per_doc:.1f}")
            print(f"  Nombre minimum de chunks par document: {min_chunks_per_doc}")
            print(f"  Nombre maximum de chunks par document: {max_chunks_per_doc}")

            # Distribution des tailles de contenu total par document
            total_sizes = [stat["total_content_size"] for stat in doc_stats]
            avg_total_size = sum(total_sizes) / len(total_sizes)
            min_total_size = min(total_sizes)
            max_total_size = max(total_sizes)

            print(f"\n📊 Taille totale des documents:")
            print(f"  Taille moyenne totale: {avg_total_size:.0f} caractères")
            print(f"  Taille minimale totale: {min_total_size} caractères")
            print(f"  Taille maximale totale: {max_total_size} caractères")

        # Vérifications finales
        total_chunks_by_id = sum(
            len(chunk_list) for chunk_list in chunks_by_id.values()
        )
        total_chunks_by_doc_id = sum(
            len(chunk_list) for chunk_list in chunks_by_doc_id.values()
        )

        assert total_chunks_by_id == len(
            chunks
        ), "Le nombre total de chunks par ID doit correspondre"
        assert total_chunks_by_doc_id == len(
            chunks
        ), "Le nombre total de chunks par doc_id doit correspondre"

        print(f"\n✅ Vérifications:")
        print(f"  Total chunks par ID: {total_chunks_by_id}")
        print(f"  Total chunks par doc_id: {total_chunks_by_doc_id}")
        print(f"  Total chunks réel: {len(chunks)}")

        print("✅ Test des chunks de documents réussi!")


class TestQuestionAnswerTool:

    def test_question_answer(self):
        import json

        # Utiliser un format JSON pour forcer l'utilisation du QuestionAnswerTool
        question = '{"question": "Comment elever des Mouches ?"}'
        agent = get_agent(
            retriever_config_path=Path("media/rag_configs/Low_Tech_1/index.yaml")
        )
        answer = agent.run(question)
        answer = json.loads(answer)
        print(f"Type de réponse: {type(answer)}")
        print(f"Réponse: {answer}")

        # Vérifier si c'est une sortie JSON du QuestionAnswerTool
        if isinstance(answer, list) and len(answer) > 0:
            first_item = answer[0]
            if (
                isinstance(first_item, dict)
                and "answer" in first_item
                and "question_id" in first_item
                and "sources" in first_item
            ):
                print("✅ Sortie JSON du QuestionAnswerTool détectée!")
                print(f"Réponse: {first_item['answer']}")
                print(f"Question ID: {first_item['question_id']}")
                print(f"Sources: {len(first_item['sources'])} sources trouvées")
                for i, source in enumerate(first_item["sources"]):
                    print(
                        f"  Source {i+1}: {source.get('title', 'Sans titre')} (score: {source.get('similarity_score', 'N/A')})"
                    )
            else:
                print("❌ Format JSON inattendu")
        else:
            print("❌ Pas de sortie JSON du QuestionAnswerTool")

        assert len(str(answer)) > 0


class TestTaskQA:

    question_number = 2

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup the test environment"""
        print("Setup the test environment")
        self.collection = Collection.objects.create(title="Test")
        self.source = Source.objects.create(
            collection=self.collection,
            title="Test",
            type=Source.FILE,
            file=ContentFile("Test"),
        )
        questions = []
        for i in range(self.question_number):
            question = Question.objects.create(
                title=f"Test {i}",
                field=f"Quelle est la puissance d'un panneau solaire ? {i}",
                source=self.source,
            )
            questions.append(question)
        self.source.questions.add(*questions)
        self.source.save()

    @pytest.mark.django_db(transaction=True)
    def test_task_qa(self):

        source = Source.objects.prefetch_related("questions__answer").first()
        start = time.time()
        agent_qa = QuestionAnswerTool()
        agent_retriever = DiskStorageRetrieverTool(
            config_path=Path("media/rag_configs/Low_Tech_1/index.yaml")
        )
        # Possible optimization: using ProcessPoolExecutor, attention of serialization (Pytorch)
        for i, question in enumerate(source.questions.all()):
            documents = agent_retriever.forward(question.field)
            answer = agent_qa.forward(question.field, documents)
            answer = json.loads(answer)
            print(f"🔍 Réponse: {answer}")
            documents = [
                DocumentModel.objects.create(
                    title=doc["title"],
                    uid=doc["id"],
                    similarity_score=doc["similarity_score"],
                    url=doc["url"],
                )
                for doc in answer.get("sources", [])
            ]
            answer_instance = Answer.objects.create(
                title=f"Answer {i}", field=answer["answer"], question=question
            )
            answer_instance.documents.set(documents)
            answer_instance.save()
            print(f"🔍 Answer {i}: {answer_instance.field}")
            print(
                f"🔍 Documents: {answer_instance.documents.values_list('uid', flat=True)}"
            )
        print(Answer.objects.all())
        print(f"Results in {time.time() - start}")
        source.refresh_from_db()
        for question in source.questions.all():
            print(question.field)
            if hasattr(question, "answer") and question.answer:
                answer = question.answer
                print(answer.documents.values_list("uid", flat=True))
                print(answer.field)


class TestDocling:

    def test_docling(self):
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(
            "media/rag_sources/APsystems-Microinverter-DS3-series-for-Philippines-Datasheet_-Rev1.2_2023-02-08.pdf"
        )
        print(result)

    def test_1(self):
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        opts = PdfPipelineOptions()
        opts.do_ocr = False  # avoid EasyOCR/PyTorch entirely

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )
        result = converter.convert(
            "media/rag_sources/APsystems-Microinverter-DS3-series-for-Philippines-Datasheet_-Rev1.2_2023-02-08.pdf"
        )
        print(result)

    def test_2(self):
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            TesseractCliOcrOptions,
            PdfBackend,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption

        opts = PdfPipelineOptions(
            pdf_backend=PdfBackend.PYPDFIUM2,  # parseur non-ML
            do_ocr=True,
            ocr_options=TesseractCliOcrOptions(lang=["eng"]),
            do_table_structure=False,  # coupe TableFormer (PyTorch)
        )

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )
        result = converter.convert(
            "media/rag_sources/APsystems-Microinverter-DS3-series-for-Philippines-Datasheet_-Rev1.2_2023-02-08.pdf"
        )
