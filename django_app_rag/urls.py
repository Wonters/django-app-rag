from django.urls import path, include
from .views import MainRAGTemplateView, DocumentsModelViewSet, SourceFormView, SourceModelViewSet
from rest_framework.routers import DefaultRouter

app_name = 'django_app_rag'

router = DefaultRouter()
router.register(r'documents', DocumentsModelViewSet, basename='documents')
router.register(r'sources', SourceModelViewSet, basename='sources')
urlpatterns = [
    path('', MainRAGTemplateView.as_view(), name='main-rag-front'),
    path('source/add/', SourceFormView.as_view(), name='source-add'),
    path('source/<str:pk>/edit/', SourceFormView.as_view(), name='source-edit'),
    path('api/', include(router.urls)),
] 