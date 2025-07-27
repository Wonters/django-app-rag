from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.generic import TemplateView
from django.conf import settings
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet
from .models import Question, Collection
from .serializer import SourceSerializer, QuestionSerializer, CollectionSerializer
from django.views.generic.edit import FormView, CreateView, UpdateView
from .models import Source
from .forms import SourceForm, QuestionForm, CollectionForm
from django_app_rag.logging import get_logger
from django.urls import reverse
import json
from django.http import JsonResponse
from .tasks.mixins import TaskViewMixin
from .tasks.etl_tasks import initialize_collection_task

logger = get_logger(__name__)

class MainRAGTemplateView(TemplateView):
    """
    Principal template pour l'application RAG
    """
    template_name = "django_app_rag/main_rag.html" 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['debug'] = settings.DEBUG
        return context

class CollectionsModelViewSet(ModelViewSet):
    """
    Collection viewset
    """
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer

class CollectionFormTemplateView(FormView):
    """
    Vue pour le formulaire de création/modification d'une collection
    """
    template_name = 'django_app_rag/collection_form.html'
    form_class = CollectionForm
    success_url = '/rag_app'  # ou autre URL de redirection

    def get_object(self):
        """
        Récupérer l'objet collection
        """
        pk = self.kwargs.get('pk')
        if pk is not None:
            try:
                return Collection.objects.get(pk=pk)
            except Collection.DoesNotExist:
                return None
        return None

    def get_form_kwargs(self):
        """
        Get the form kwargs
        """
        kwargs = super().get_form_kwargs()
        if obj := self.get_object():
            kwargs['instance'] = obj
        return kwargs

    def get(self, request, *args, **kwargs):
        """
        Get the form.
        """
        form = self.get_form()
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        """
        Post the form.
        """
        form = self.get_form()
        if form.is_valid():
            collection = form.save()
            return super().form_valid(form)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection = self.get_object()
        if collection:
            context['collection'] = collection
            context['is_edit'] = True
        else:
            context['is_edit'] = False
        return context

class SourceModelViewSet(ModelViewSet):
    """
    Source viewset
    """
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    
    def get_queryset(self):
        queryset = Source.objects.all()
        collection_id = self.request.query_params.get('collection', None)
        if collection_id is not None:
            queryset = queryset.filter(collection_id=collection_id)
        return queryset

class QuestionModelViewSet(ModelViewSet):
    """
    Question viewset
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    
    def get_queryset(self):
        queryset = Question.objects.all()
        source_id = self.request.query_params.get('source', None)
        if source_id is not None:
            queryset = queryset.filter(source_id=source_id)
        return queryset

class SourceFormView(FormView):
    """
    View pour le formulaire de création/modification d'une source
    """
    template_name = 'django_app_rag/source_form.html'
    form_class = SourceForm
    success_url = '/rag_app'  # ou autre URL de redirection

    def get_object(self):
        """
        Retrive the source object
        """
        pk = self.kwargs.get('pk')
        if pk is not None:
            try:
                return Source.objects.get(pk=pk)
            except Source.DoesNotExist:
                return None
        return None

    def get_form_kwargs(self):
        """
        Get the form kwargs
        """
        kwargs = super().get_form_kwargs()
        if obj:=self.get_object():
            kwargs['instance'] = obj
        # Pour GET, on regarde si un type est passé en paramètre
        if self.request.method == 'POST':
            # Pour POST, on regarde dans les données postées
            selected_type = self.request.POST.get('type')
            # Inclure les fichiers pour les requêtes POST
            kwargs['files'] = self.request.FILES
        else:
            selected_type = self.request.GET.get('type')
        if selected_type:
            kwargs['selected_type'] = selected_type
        
        # Récupérer le paramètre collection de la requête
        collection_id = self.request.GET.get('collection')
        if collection_id:
            kwargs['collection_id'] = collection_id
            
        return kwargs

    def get(self, request, *args, **kwargs):
        """
        Get the form.
        """
        form = self.get_form()
        return self.render_to_response(self.get_context_data(form=form))
        

    def post(self, request, *args, **kwargs):
        """
        Post the form.
        Source form is done in two steps:
        - First step: get the form and select type of source, it returns the form with 
        the type of source selected and specific fields according to the type of source
        - Second step: post the form
        """
        # On récupère le type sélectionné
        selected_type = request.POST.get('type')
        form = self.get_form()
        # On vérifie si le champ spécifique est rempli
        specific_field = self.form_class.fields_map.get(selected_type)

        if not specific_field or not request.POST.get(specific_field) and not request.FILES.get(specific_field):
            # Si le champ spécifique n'est pas encore rempli, on réaffiche le formulaire avec le champ spécifique
            return self.render_to_response(self.get_context_data(form=form))
        # Sinon, on valide et sauvegarde
        if form.is_valid():
            logger.info(f"Form is valid: {form.cleaned_data}")
            form.save()
            return self.form_valid(form)
        return self.form_invalid(form)
    

    def delete(self, request, *args, **kwargs):
        """
        Delete the source.
        """
        source = self.get_object()
        if source:
            source.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)
    


class QuestionFormView(CreateView):
    """
    Question view to create and update a question
    """
    template_name = 'django_app_rag/question_form.html'
    form_class = QuestionForm
    success_url = '/rag_app/'

    def get_object(self):
        pk = self.kwargs.get('pk')
        if pk is not None:
            try:
                return Question.objects.get(pk=pk)
            except Question.DoesNotExist:
                return None
        return None

    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        # Si on modifie une question existante
        if self.get_object():
            kwargs['instance'] = self.get_object()
        
        # Récupérer la source depuis les paramètres GET ou depuis l'objet existant
        source_id = self.request.GET.get('source_id')
        if source_id:
            try:
                source = Source.objects.get(pk=source_id)
                kwargs['source'] = source
            except Source.DoesNotExist:
                pass
        elif self.get_object():
            kwargs['source'] = self.get_object().source
            
        return kwargs

    def form_valid(self, form):
        # Si on a une source depuis les paramètres GET, l'assigner
        source_id = self.request.GET.get('source_id')
        if source_id:
            try:
                source = Source.objects.get(pk=source_id)
                form.instance.source = source
            except Source.DoesNotExist:
                pass
        
        form.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = self.get_object()
        if question:
            context['question'] = question
            context['is_edit'] = True
        else:
            context['is_edit'] = False
        return context

class ETLTaskView(APIView, TaskViewMixin):
    """
    Vue pour gérer les tâches ETL d'initialisation des collections
    """
    queue_name = "etl_tasks"
    
    def post(self, request, *args, **kwargs):
        """
        Lance une tâche d'initialisation pour une collection
        """
        collection_id = request.data.get('collection_id')
        
        if not collection_id:
            return self._format_task_response(
                status="failed",
                message="ID de collection manquant",
                task_id=None,
                error="Le paramètre collection_id est requis",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Vérifier que la collection existe
            collection = Collection.objects.get(id=collection_id)
        except Collection.DoesNotExist:
            return self._format_task_response(
                status="failed",
                message="Collection non trouvée",
                task_id=None,
                error=f"Collection avec l'ID {collection_id} n'existe pas",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        # Lancer la tâche d'initialisation
        return self.launch_task(
            task_func=initialize_collection_task,
            task_kwargs={
                'collection_id': collection_id,
            },
            success_message=f"Tâche d'initialisation lancée pour la collection '{collection.title}'",
            error_message="Erreur lors du lancement de la tâche d'initialisation"
        )
    
    def get(self, request, *args, **kwargs):
        """
        Récupère le statut d'une tâche d'initialisation
        """
        task_id = request.query_params.get('task_id')
        
        if not task_id:
            return self._format_task_response(
                status="failed",
                message="ID de tâche manquant",
                task_id=None,
                error="Le paramètre task_id est requis",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        return self.get_task_status(task_id, "Tâche d'initialisation")