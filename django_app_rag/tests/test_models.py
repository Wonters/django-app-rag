"""
Unit tests for Django models.

Tests cover:
- Source model creation and methods
- Collection model creation and methods
- Question and Answer models
- Document model
- RagConfig model
"""

import pytest
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from pathlib import Path
import tempfile
import shutil
from django_app_rag.models import Collection, Source, Question, Answer, Document, RagConfig


class CollectionModelTest(TestCase):
    """Tests for Collection model."""

    def setUp(self):
        """Set up test data."""
        self.collection = Collection.objects.create(
            title="Test Collection",
            description="Test description"
        )

    def test_collection_creation(self):
        """Test that collection is created correctly."""
        self.assertEqual(self.collection.title, "Test Collection")
        self.assertEqual(self.collection.description, "Test description")
        self.assertIsNotNone(self.collection.id)

    def test_collection_str(self):
        """Test collection string representation."""
        self.assertEqual(str(self.collection), "Test Collection")

    def test_get_rag_data_dir(self):
        """Test get_rag_data_dir method."""
        data_dir = self.collection.get_rag_data_dir()
        self.assertIsInstance(data_dir, Path)
        self.assertTrue(str(data_dir).endswith(f"test_collection_{self.collection.id}"))

    def test_collection_sources_relationship(self):
        """Test that collection can have multiple sources."""
        source1 = Source.objects.create(
            title="Source 1",
            type=Source.URL,
            link="https://example.com",
            collection=self.collection
        )
        source2 = Source.objects.create(
            title="Source 2",
            type=Source.FILE,
            collection=self.collection
        )

        self.assertEqual(self.collection.sources.count(), 2)
        self.assertIn(source1, self.collection.sources.all())
        self.assertIn(source2, self.collection.sources.all())


class SourceModelTest(TestCase):
    """Tests for Source model."""

    def setUp(self):
        """Set up test data."""
        self.collection = Collection.objects.create(
            title="Test Collection"
        )

    def test_url_source_creation(self):
        """Test URL source creation."""
        source = Source.objects.create(
            title="URL Source",
            type=Source.URL,
            link="https://example.com",
            collection=self.collection
        )

        self.assertEqual(source.title, "URL Source")
        self.assertEqual(source.type, Source.URL)
        self.assertEqual(source.link, "https://example.com")
        self.assertEqual(source.collection, self.collection)

    def test_notion_source_creation(self):
        """Test Notion source creation."""
        source = Source.objects.create(
            title="Notion Source",
            type=Source.NOTION,
            notion_db_ids="db123,db456",
            collection=self.collection
        )

        self.assertEqual(source.type, Source.NOTION)
        self.assertEqual(source.notion_db_ids, "db123,db456")

    def test_file_source_creation(self):
        """Test file source creation."""
        source = Source.objects.create(
            title="File Source",
            type=Source.FILE,
            collection=self.collection
        )

        self.assertEqual(source.type, Source.FILE)

    def test_get_rag_id(self):
        """Test get_rag_id method."""
        source = Source.objects.create(
            title="Test Source",
            type=Source.URL,
            link="https://example.com/test",
            collection=self.collection
        )

        rag_id = source.get_rag_id()
        self.assertIsInstance(rag_id, str)
        self.assertTrue(len(rag_id) > 0)

    def test_source_str(self):
        """Test source string representation."""
        source = Source.objects.create(
            title="My Source",
            type=Source.URL,
            collection=self.collection
        )

        self.assertEqual(str(source), "My Source")

    def test_quality_score_default(self):
        """Test that quality_score defaults to None."""
        source = Source.objects.create(
            title="Test",
            type=Source.URL,
            collection=self.collection
        )

        self.assertIsNone(source.quality_score)

    def test_is_indexed_at_default(self):
        """Test that is_indexed_at defaults to None."""
        source = Source.objects.create(
            title="Test",
            type=Source.URL,
            collection=self.collection
        )

        self.assertIsNone(source.is_indexed_at)


class QuestionAnswerModelTest(TestCase):
    """Tests for Question and Answer models."""

    def setUp(self):
        """Set up test data."""
        self.collection = Collection.objects.create(title="Test Collection")
        self.source = Source.objects.create(
            title="Test Source",
            type=Source.URL,
            collection=self.collection
        )

    def test_question_creation(self):
        """Test question creation."""
        question = Question.objects.create(
            title="What is RAG?",
            field="Explain RAG",
            source=self.source
        )

        self.assertEqual(question.title, "What is RAG?")
        self.assertEqual(question.field, "Explain RAG")
        self.assertEqual(question.source, self.source)

    def test_answer_creation(self):
        """Test answer creation."""
        question = Question.objects.create(
            title="Test Question",
            field="Test",
            source=self.source
        )

        answer = Answer.objects.create(
            title="Test Answer",
            field="RAG is Retrieval Augmented Generation",
            question=question
        )

        self.assertEqual(answer.title, "Test Answer")
        self.assertEqual(answer.question, question)
        self.assertEqual(question.answer, answer)

    def test_answer_documents_relationship(self):
        """Test answer can have multiple documents."""
        question = Question.objects.create(
            title="Test", field="Test", source=self.source
        )
        answer = Answer.objects.create(
            title="Answer", field="Text", question=question
        )

        doc1 = Document.objects.create(
            title="Doc 1",
            uid="doc1",
            similarity_score=0.9
        )
        doc2 = Document.objects.create(
            title="Doc 2",
            uid="doc2",
            similarity_score=0.8
        )

        answer.documents.add(doc1, doc2)

        self.assertEqual(answer.documents.count(), 2)
        self.assertIn(doc1, answer.documents.all())
        self.assertIn(doc2, answer.documents.all())


class DocumentModelTest(TestCase):
    """Tests for Document model."""

    def test_document_creation(self):
        """Test document creation."""
        doc = Document.objects.create(
            title="Test Document",
            uid="test-uid-123",
            similarity_score=0.95,
            url="https://example.com/doc"
        )

        self.assertEqual(doc.title, "Test Document")
        self.assertEqual(doc.uid, "test-uid-123")
        self.assertEqual(doc.similarity_score, 0.95)
        self.assertEqual(doc.url, "https://example.com/doc")

    def test_document_optional_fields(self):
        """Test document with optional fields."""
        doc = Document.objects.create(
            title="Minimal Doc",
            uid="min-123"
        )

        self.assertIsNone(doc.similarity_score)
        self.assertIsNone(doc.url)


class RagConfigModelTest(TestCase):
    """Tests for RagConfig model."""

    def setUp(self):
        """Set up test data."""
        self.collection = Collection.objects.create(title="Test Collection")

    def test_rag_config_creation(self):
        """Test RagConfig creation."""
        yaml_content = """
collection_name: test
embedding_model_id: all-MiniLM-L6-v2
chunk_size: 640
"""
        config_file = SimpleUploadedFile(
            "config.yaml",
            yaml_content.encode('utf-8'),
            content_type="application/x-yaml"
        )

        rag_config = RagConfig.objects.create(
            collection=self.collection,
            config_file=config_file
        )

        self.assertEqual(rag_config.collection, self.collection)
        self.assertIsNotNone(rag_config.config_file)

    def test_multiple_configs_per_collection(self):
        """Test that collection can have multiple configs."""
        config1 = RagConfig.objects.create(
            collection=self.collection,
            config_file=SimpleUploadedFile("c1.yaml", b"test: 1")
        )
        config2 = RagConfig.objects.create(
            collection=self.collection,
            config_file=SimpleUploadedFile("c2.yaml", b"test: 2")
        )

        self.assertEqual(self.collection.rag_configs.count(), 2)
        self.assertIn(config1, self.collection.rag_configs.all())
        self.assertIn(config2, self.collection.rag_configs.all())


@pytest.mark.django_db
class TestSourceMethods:
    """Pytest-style tests for Source methods."""

    def test_get_rag_id_consistency(self):
        """Test that get_rag_id returns consistent IDs."""
        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Test",
            type=Source.URL,
            link="https://example.com",
            collection=collection
        )

        # Get ID twice, should be the same
        id1 = source.get_rag_id()
        id2 = source.get_rag_id()

        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) > 0

    def test_different_source_types_have_different_ids(self):
        """Test that different source types generate different IDs."""
        collection = Collection.objects.create(title="Test")

        url_source = Source.objects.create(
            title="URL",
            type=Source.URL,
            link="https://example.com",
            collection=collection
        )

        notion_source = Source.objects.create(
            title="Notion",
            type=Source.NOTION,
            notion_db_ids="db123",
            collection=collection
        )

        # IDs should be different
        assert url_source.get_rag_id() != notion_source.get_rag_id()
