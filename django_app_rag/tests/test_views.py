"""
Unit tests for Django views.

Tests cover:
- SourceFormView (creation and editing)
- CollectionFormTemplateView
- QuestionFormView
- API ViewSets
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django_app_rag.models import Collection, Source, Question, Answer, Document


class SourceFormViewTest(TestCase):
    """Tests for SourceFormView."""

    def setUp(self):
        """Set up test client and data."""
        self.client = Client()
        self.collection = Collection.objects.create(
            title="Test Collection"
        )

    def test_source_form_get_empty(self):
        """Test GET request to source form."""
        url = reverse('source-add')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_source_form_get_with_type(self):
        """Test GET request with type parameter."""
        url = reverse('source-add')
        response = self.client.get(url, {'type': 'url'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_source_form_post_step_one(self):
        """Test POST request - step 1 (select type)."""
        url = reverse('source-add')
        response = self.client.post(url, {
            'type': 'url',
            'collection': self.collection.id,
            'title': 'Test Source'
        })

        # Should re-render form for step 2
        self.assertEqual(response.status_code, 200)

    def test_source_form_post_step_two_url(self):
        """Test POST request - step 2 (submit URL source)."""
        url = reverse('source-add')
        response = self.client.post(url, {
            'type': 'url',
            'collection': self.collection.id,
            'title': 'URL Source',
            'link': 'https://example.com'
        })

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Check source was created
        source = Source.objects.filter(title='URL Source').first()
        self.assertIsNotNone(source)
        self.assertEqual(source.type, Source.URL)
        self.assertEqual(source.link, 'https://example.com')

    def test_source_edit_get(self):
        """Test GET request to edit existing source."""
        source = Source.objects.create(
            title="Edit Test",
            type=Source.URL,
            link="https://old.com",
            collection=self.collection
        )

        url = reverse('source-edit', kwargs={'pk': source.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_source_edit_post(self):
        """Test POST request to edit existing source."""
        source = Source.objects.create(
            title="Old Title",
            type=Source.URL,
            link="https://old.com",
            collection=self.collection
        )

        url = reverse('source-edit', kwargs={'pk': source.id})
        response = self.client.post(url, {
            'type': 'url',
            'collection': self.collection.id,
            'title': 'New Title',
            'link': 'https://new.com'
        })

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Check source was updated
        source.refresh_from_db()
        self.assertEqual(source.title, 'New Title')
        self.assertEqual(source.link, 'https://new.com')


class QuestionFormViewTest(TestCase):
    """Tests for QuestionFormView."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.collection = Collection.objects.create(title="Test")
        self.source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=self.collection
        )

    def test_question_form_get(self):
        """Test GET request to question form."""
        url = reverse('question-add')
        response = self.client.get(url, {'source': self.source.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_question_form_post(self):
        """Test POST request to create question."""
        url = reverse('question-add')
        response = self.client.post(url, {
            'source': self.source.id,
            'title': 'Test Question',
            'field': 'What is RAG?'
        })

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Check question was created
        question = Question.objects.filter(title='Test Question').first()
        self.assertIsNotNone(question)
        self.assertEqual(question.field, 'What is RAG?')
        self.assertEqual(question.source, self.source)


class CollectionAPITest(APITestCase):
    """Tests for Collection API endpoints."""

    def setUp(self):
        """Set up API client."""
        self.client = APIClient()

    def test_list_collections(self):
        """Test GET /api/collections/."""
        Collection.objects.create(title="Collection 1")
        Collection.objects.create(title="Collection 2")

        url = reverse('collection-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_collection(self):
        """Test POST /api/collections/."""
        url = reverse('collection-list')
        data = {
            'title': 'New Collection',
            'description': 'Test description'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Collection.objects.count(), 1)
        self.assertEqual(Collection.objects.first().title, 'New Collection')

    def test_get_collection_detail(self):
        """Test GET /api/collections/{id}/."""
        collection = Collection.objects.create(title="Detail Test")

        url = reverse('collection-detail', kwargs={'pk': collection.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Detail Test')

    def test_update_collection(self):
        """Test PUT /api/collections/{id}/."""
        collection = Collection.objects.create(title="Old")

        url = reverse('collection-detail', kwargs={'pk': collection.id})
        data = {'title': 'Updated', 'description': 'New desc'}

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        collection.refresh_from_db()
        self.assertEqual(collection.title, 'Updated')

    def test_delete_collection(self):
        """Test DELETE /api/collections/{id}/."""
        collection = Collection.objects.create(title="Delete Me")

        url = reverse('collection-detail', kwargs={'pk': collection.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Collection.objects.count(), 0)


class SourceAPITest(APITestCase):
    """Tests for Source API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.collection = Collection.objects.create(title="Test")

    def test_list_sources(self):
        """Test GET /api/sources/."""
        Source.objects.create(
            title="Source 1",
            type=Source.URL,
            collection=self.collection
        )

        url = reverse('source-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_sources_by_collection(self):
        """Test filtering sources by collection."""
        collection2 = Collection.objects.create(title="Collection 2")

        Source.objects.create(
            title="S1", type=Source.URL, collection=self.collection
        )
        Source.objects.create(
            title="S2", type=Source.URL, collection=collection2
        )

        url = reverse('source-list')
        response = self.client.get(url, {'collection': self.collection.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'S1')

    def test_create_source(self):
        """Test POST /api/sources/."""
        url = reverse('source-list')
        data = {
            'title': 'New Source',
            'type': 'url',
            'link': 'https://example.com',
            'collection': self.collection.id
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Source.objects.count(), 1)


class QuestionAPITest(APITestCase):
    """Tests for Question API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.collection = Collection.objects.create(title="Test")
        self.source = Source.objects.create(
            title="Source",
            type=Source.URL,
            collection=self.collection
        )

    def test_list_questions(self):
        """Test GET /api/questions/."""
        Question.objects.create(
            title="Q1",
            field="Test",
            source=self.source
        )

        url = reverse('question-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_question(self):
        """Test POST /api/questions/."""
        url = reverse('question-list')
        data = {
            'title': 'New Question',
            'field': 'What is this?',
            'source': self.source.id
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Question.objects.count(), 1)

    def test_question_with_answer(self):
        """Test question detail includes answer."""
        question = Question.objects.create(
            title="Q",
            field="Test",
            source=self.source
        )
        Answer.objects.create(
            title="A",
            field="Answer text",
            question=question
        )

        url = reverse('question-detail', kwargs={'pk': question.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('answer', response.data)
        self.assertEqual(response.data['answer']['field'], 'Answer text')


@pytest.mark.django_db
class TestViewHelperMethods:
    """Pytest-style tests for view helper methods."""

    def test_source_form_view_is_editing(self, client):
        """Test _is_editing helper method."""
        from django_app_rag.views import SourceFormView

        # Create test instance
        collection = Collection.objects.create(title="Test")
        source = Source.objects.create(
            title="Test",
            type=Source.URL,
            collection=collection
        )

        # Test edit URL detection
        view = SourceFormView()
        view.request = client.get(f'/source/{source.id}/edit/')

        assert view._is_editing() is True

        # Test add URL
        view.request = client.get('/source/add/')
        assert view._is_editing() is False

    def test_source_form_view_is_step_one(self, client):
        """Test _is_step_one helper method."""
        from django_app_rag.views import SourceFormView

        view = SourceFormView()

        # Step 1: type selected but no specific field
        view.request = client.post('/source/add/', {
            'type': 'url',
            'title': 'Test'
        })

        assert view._is_step_one('url') is True

        # Step 2: type and link provided
        view.request = client.post('/source/add/', {
            'type': 'url',
            'title': 'Test',
            'link': 'https://example.com'
        })

        assert view._is_step_one('url') is False
