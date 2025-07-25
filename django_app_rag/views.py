from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.generic import TemplateView
from django.conf import settings
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet
from .models import Document
from .serializer import DocumentsSerializer, SourceSerializer
from django.views.generic.edit import FormView
from .models import Source
from .forms import SourceForm


class MainRAGTemplateView(TemplateView):
    template_name = "django_app_rag/main_rag.html" 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['debug'] = settings.DEBUG
        return context

class DocumentsModelViewSet(ModelViewSet):
    queryset = Document.objects.all().order_by('-uploaded_at')
    serializer_class = DocumentsSerializer

class SourceModelViewSet(ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer


class SourceFormView(FormView):
    template_name = 'django_app_rag/source_form.html'
    form_class = SourceForm
    success_url = '/rag_app'  # ou autre URL de redirection

    def get_object(self):
        pk = self.kwargs.get('pk')
        if pk is not None:
            try:
                return Source.objects.get(pk=pk)
            except Source.DoesNotExist:
                return None
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        obj = self.get_object()
        if obj:
            kwargs['instance'] = obj
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
