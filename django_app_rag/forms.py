from django import forms
from .models import Source, Question

class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ['title', 'link', 'type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].widget = forms.Select(choices=Source.SOURCE_TYPE_CHOICES, attrs={'class': 'form-control'})
        self.fields['link'].widget = forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        self.fields['title'].widget = forms.TextInput(attrs={'placeholder': 'Titre de la source', 'class': 'form-control'})
        self.fields['link'].widget.attrs['placeholder'] = 'Lien de la source'


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['title', 'field', 'source']


