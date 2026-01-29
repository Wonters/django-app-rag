"""
Unit tests for Dramatiq tasks.

Tests cover:
- launch_qa_process task
- Helper functions for QA processing
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from django.test import TestCase
from django_app_rag.models import Collection, Source, Question, Answer, Document
from django_app_rag.tasks.rag_tasks import (
    launch_qa_process,
    _validate_config_path,
    _get_source_with_questions,
    _initialize_rag_agents,
    _delete_old_answer,
    _retrieve_documents,
    _generate_answer,
    _create_answer_instance,
    _create_source_documents,
    _process_single_question,
    TaskStatus,
)


class ValidateConfigPathTest(TestCase):
    """Tests for _validate_config_path helper."""

    def test_validate_config_path_missing(self):
        """Test validation with missing config path."""
        with self.assertRaises(ValueError) as context:
            _validate_config_path("")

        self.assertIn("manquant", str(context.exception))

    def test_validate_config_path_not_exists(self):
        """Test validation with non-existent file."""
        with self.assertRaises(FileNotFoundError) as context:
            _validate_config_path("/nonexistent/path/config.yaml")

        self.assertIn("introuvable", str(context.exception))

    def test_validate_config_path_valid(self, tmp_path=None):
        """Test validation with valid config file."""
        # Create temporary config file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: value\n")
            temp_path = f.name

        try:
            result = _validate_config_path(temp_path)
            self.assertIsInstance(result, Path)
            self.assertTrue(result.exists())
        finally:
            Path(temp_path).unlink()


class GetSourceWithQuestionsTest(TestCase):
    """Tests for _get_source_with_questions helper."""

    def setUp(self):
        """Set up test data."""
        self.collection = Collection.objects.create(title="Test")
        self.source = Source.objects.create(
            title="Test Source",
            type=Source.URL,
            collection=self.collection
        )

    def test_get_source_with_questions_success(self):
        """Test retrieving source with questions."""
        Question.objects.create(
            title="Q1",
            field="What?",
            source=self.source
        )
        Question.objects.create(
            title="Q2",
            field="Why?",
            source=self.source
        )

        source, questions = _get_source_with_questions(self.source.id)

        self.assertEqual(source, self.source)
        self.assertEqual(questions.count(), 2)

    def test_get_source_not_found(self):
        """Test with non-existent source ID."""
        with self.assertRaises(Source.DoesNotExist):
            _get_source_with_questions(99999)


class DeleteOldAnswerTest(TestCase):
    """Tests for _delete_old_answer helper."""

    def setUp(self):
        """Set up test data."""
        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=collection
        )
        self.question = Question.objects.create(
            title="Q",
            field="Test",
            source=source
        )

    def test_delete_old_answer_exists(self):
        """Test deleting existing old answer."""
        old_answer = Answer.objects.create(
            title="Old",
            field="Old text",
            question=self.question
        )
        doc = Document.objects.create(title="Doc", uid="doc1")
        old_answer.documents.add(doc)

        # Delete old answer
        _delete_old_answer(self.question)

        # Check answer is deleted
        with self.assertRaises(Answer.DoesNotExist):
            Answer.objects.get(id=old_answer.id)

        # Check document still exists (not cascaded)
        self.assertTrue(Document.objects.filter(id=doc.id).exists())

    def test_delete_old_answer_none(self):
        """Test when no old answer exists."""
        # Should not raise error
        _delete_old_answer(self.question)


class GenerateAnswerTest(TestCase):
    """Tests for _generate_answer helper."""

    @patch('django_app_rag.tasks.rag_tasks.QuestionAnswerTool')
    def test_generate_answer_success(self, mock_qa_tool):
        """Test successful answer generation."""
        mock_agent = Mock()
        mock_agent.forward.return_value = '{"answer": "Test answer", "sources": []}'
        mock_qa_tool.return_value = mock_agent

        result = _generate_answer(mock_agent, "What is RAG?", "{}")

        self.assertIsNotNone(result)
        self.assertEqual(result['answer'], "Test answer")

    @patch('django_app_rag.tasks.rag_tasks.QuestionAnswerTool')
    def test_generate_answer_empty_response(self, mock_qa_tool):
        """Test with empty response."""
        mock_agent = Mock()
        mock_agent.forward.return_value = ""

        result = _generate_answer(mock_agent, "Question", "{}")

        self.assertIsNone(result)

    @patch('django_app_rag.tasks.rag_tasks.QuestionAnswerTool')
    def test_generate_answer_invalid_json(self, mock_qa_tool):
        """Test with invalid JSON response."""
        mock_agent = Mock()
        mock_agent.forward.return_value = "not valid json"

        result = _generate_answer(mock_agent, "Question", "{}")

        self.assertIsNone(result)

    @patch('django_app_rag.tasks.rag_tasks.QuestionAnswerTool')
    def test_generate_answer_list_response(self, mock_qa_tool):
        """Test with list response (extracts first item)."""
        mock_agent = Mock()
        mock_agent.forward.return_value = '[{"answer": "Test"}]'

        result = _generate_answer(mock_agent, "Question", "{}")

        self.assertIsNotNone(result)
        self.assertEqual(result['answer'], "Test")


class CreateAnswerInstanceTest(TestCase):
    """Tests for _create_answer_instance helper."""

    def setUp(self):
        """Set up test data."""
        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=collection
        )
        self.question = Question.objects.create(
            title="Q",
            field="Test",
            source=source
        )

    def test_create_answer_instance_success(self):
        """Test creating answer instance."""
        answer_json = {"answer": "Test answer", "sources": []}

        answer = _create_answer_instance(self.question, answer_json, 0)

        self.assertIsNotNone(answer)
        self.assertEqual(answer.field, "Test answer")
        self.assertEqual(answer.question, self.question)

    def test_create_answer_instance_default_text(self):
        """Test creating answer with missing answer field."""
        answer_json = {"sources": []}

        answer = _create_answer_instance(self.question, answer_json, 0)

        self.assertIsNotNone(answer)
        self.assertEqual(answer.field, "Aucune réponse générée")


class CreateSourceDocumentsTest(TestCase):
    """Tests for _create_source_documents helper."""

    def setUp(self):
        """Set up test data."""
        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=collection
        )
        question = Question.objects.create(
            title="Q",
            field="Test",
            source=source
        )
        self.answer = Answer.objects.create(
            title="A",
            field="Answer",
            question=question
        )

    def test_create_source_documents_success(self):
        """Test creating and associating source documents."""
        answer_json = {
            "answer": "Test",
            "sources": [
                {
                    "title": "Doc 1",
                    "id": "doc1",
                    "similarity_score": 0.9,
                    "url": "https://example.com/1"
                },
                {
                    "title": "Doc 2",
                    "id": "doc2",
                    "similarity_score": 0.8,
                    "url": "https://example.com/2"
                }
            ]
        }

        _create_source_documents(answer_json, self.answer, 0)

        self.assertEqual(self.answer.documents.count(), 2)
        doc1 = Document.objects.get(uid="doc1")
        self.assertEqual(doc1.title, "Doc 1")
        self.assertEqual(doc1.similarity_score, 0.9)

    def test_create_source_documents_no_sources(self):
        """Test with no sources in answer."""
        answer_json = {"answer": "Test"}

        _create_source_documents(answer_json, self.answer, 0)

        self.assertEqual(self.answer.documents.count(), 0)

    def test_create_source_documents_invalid_source(self):
        """Test with invalid source format."""
        answer_json = {
            "sources": [
                "invalid",  # Not a dict
                {"title": "Valid", "id": "valid"}
            ]
        }

        _create_source_documents(answer_json, self.answer, 0)

        # Only valid doc should be created
        self.assertEqual(self.answer.documents.count(), 1)


@pytest.mark.django_db
class TestLaunchQAProcessIntegration:
    """Integration tests for launch_qa_process task."""

    def test_launch_qa_process_no_questions(self):
        """Test with source that has no questions."""
        import tempfile

        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=collection
        )

        # Create temporary config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: value\n")
            config_path = f.name

        try:
            result = launch_qa_process(source.id, config_path)

            assert result['status'] == TaskStatus.COMPLETED
            assert result['processed'] == 0
            assert result['total'] == 0
            assert "Aucune question" in result['message']
        finally:
            Path(config_path).unlink()

    def test_launch_qa_process_invalid_config(self):
        """Test with invalid config path."""
        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=collection
        )

        result = launch_qa_process(source.id, "/nonexistent/config.yaml")

        assert result['status'] == TaskStatus.FAILED
        assert 'error' in result
        assert result['error'] is not None

    def test_launch_qa_process_source_not_found(self):
        """Test with non-existent source."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: value\n")
            config_path = f.name

        try:
            result = launch_qa_process(99999, config_path)

            assert result['status'] == TaskStatus.FAILED
            assert "introuvable" in result['message'].lower()
        finally:
            Path(config_path).unlink()

    @patch('django_app_rag.tasks.rag_tasks._initialize_rag_agents')
    @patch('django_app_rag.tasks.rag_tasks._process_single_question')
    def test_launch_qa_process_success(self, mock_process_q, mock_init_agents):
        """Test successful QA process."""
        import tempfile

        # Setup
        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=collection
        )
        Question.objects.create(
            title="Q1",
            field="What?",
            source=source
        )
        Question.objects.create(
            title="Q2",
            field="Why?",
            source=source
        )

        # Mock agents
        mock_init_agents.return_value = (Mock(), Mock())
        mock_process_q.return_value = True  # Success

        # Create config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: value\n")
            config_path = f.name

        try:
            result = launch_qa_process(source.id, config_path)

            assert result['status'] == TaskStatus.COMPLETED
            assert result['processed'] == 2
            assert result['total'] == 2
            assert mock_process_q.call_count == 2
        finally:
            Path(config_path).unlink()


class TaskStatusTest(TestCase):
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        self.assertEqual(TaskStatus.PENDING, "pending")
        self.assertEqual(TaskStatus.RUNNING, "running")
        self.assertEqual(TaskStatus.COMPLETED, "completed")
        self.assertEqual(TaskStatus.FAILED, "failed")
        self.assertEqual(TaskStatus.CANCELLED, "cancelled")
