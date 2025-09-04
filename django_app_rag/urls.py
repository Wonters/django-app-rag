from django.urls import path, include
from .views import (MainRAGTemplateView, CollectionsModelViewSet, SourceFormView, SourceModelViewSet, 
 QuestionFormView, QuestionModelViewSet, CollectionFormTemplateView, ETLTaskView, LaunchQAView, ChunkTextView, DocumentTextView)
from rest_framework.routers import DefaultRouter

app_name = 'django_app_rag'

router = DefaultRouter()
router.register(r'collections', CollectionsModelViewSet, basename='collections')
router.register(r'sources', SourceModelViewSet, basename='sources')
router.register(r'questions', QuestionModelViewSet, basename='questions')

urlpatterns = [
    path('', MainRAGTemplateView.as_view(), name='main-rag-front'),
    path('source/add/', SourceFormView.as_view(), name='source-add'),
    path('source/<str:pk>/edit/', SourceFormView.as_view(), name='source-edit'),
    path('source/<str:pk>/delete/', SourceFormView.as_view(), name='source-delete'),
    path('collection/add/', CollectionFormTemplateView.as_view(), name='collection-add'),
    path('collection/<str:pk>/edit/', CollectionFormTemplateView.as_view(), name='collection-edit'),
    path('question/add/', QuestionFormView.as_view(), name='question-add'),
    path('question/<str:pk>/edit/', QuestionFormView.as_view(), name='question-edit'),
    path('api/', include(router.urls)),
    path('api/etl/', ETLTaskView.as_view(), name='etl-task'),
    path('api/qa/', LaunchQAView.as_view(), name='qa-task'),
    path('api/chunk-text/', ChunkTextView.as_view(), name='chunk-text'),
    path('api/document-text/', DocumentTextView.as_view(), name='document-text'),
] 