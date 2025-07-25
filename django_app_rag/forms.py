from django import forms
from .models import Source, Question, Collection
from django_app_rag.logging import get_logger

logger = get_logger(__name__)

class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ['title', 'link', 'type', 'notion_db_ids', 'file', 'collection']

    fields_map = {
        'notion': 'notion_db_ids',
        'url': 'link',
        'file': 'file',
    }
    always_fields = ['title', 'type', 'collection']


    def filter_fields(self, selected_type):
        if not selected_type and self.instance.id is None:
            return self.always_fields
        elif selected_type and self.instance.id is None:
            return self.always_fields + [self.fields_map[selected_type]]
        elif selected_type and self.instance.id is not None:
            return self.always_fields + [self.fields_map[selected_type]]
        logger.info(f"selected_type: {selected_type}, instance: {self.instance}")
        if self.instance.id is not None:
            return self.always_fields + [self.fields_map[self.instance.type]]
        # Fallback: retourner au moins les champs toujours présents
        return self.always_fields

    def __init__(self, *args, **kwargs):
        selected_type = kwargs.pop('selected_type', None)
        collection_id = kwargs.pop('collection_id', None)
        super().__init__(*args, **kwargs)
        self.fields['type'].widget = forms.Select(choices=Source.SOURCE_TYPE_CHOICES, attrs={'class': 'form-control'})
        self.fields['link'].widget = forms.URLInput(attrs={'rows': 3, 'class': 'form-control'})
        self.fields['title'].widget = forms.TextInput(attrs={'placeholder': 'Titre de la source', 'class': 'form-control'})
        self.fields['link'].widget.attrs['placeholder'] = 'Lien de la source'
        self.fields['notion_db_ids'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={'rows': 3, 'class': 'form-control js-choice', 'placeholder': 'IDs de bases Notion, séparés par des virgules'})
        )
        self.fields['file'] = forms.FileField(
            required=False,
            widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
        )
        
        # Masquer le champ collection avec un HiddenInput
        self.fields['collection'].widget = forms.HiddenInput()
        
        # Si un collection_id est fourni, pré-remplir le champ collection
        if collection_id:
            try:
                from .models import Collection
                collection = Collection.objects.get(pk=collection_id)
                self.fields['collection'].initial = collection
            except Collection.DoesNotExist:
                pass
        
        # Affichage conditionnel des champs selon le type sélectionné
        keep = self.filter_fields(selected_type)
        for field in list(self.fields.keys()):
            if field not in keep:
                self.fields.pop(field)


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['title', 'field', 'source']

    def __init__(self, *args, **kwargs):
        source = kwargs.pop('source', None)
        super().__init__(*args, **kwargs)
        
        # Configuration des widgets
        self.fields['title'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Titre de la question'
        })
        self.fields['field'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Contenu de la question'
        })
        
        # Si une source est fournie, on la pré-remplit et on la rend en lecture seule
        if source:
            self.fields['source'].initial = source
            self.fields['source'].widget = forms.HiddenInput()

class CollectionForm(forms.ModelForm):
    """
    Formulaire pour la création et modification d'une collection
    """
    class Meta:
        model = Collection
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


