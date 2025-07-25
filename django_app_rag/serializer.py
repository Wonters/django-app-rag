from rest_framework.serializers import ModelSerializer
from .models import Source, Question, Answer, Document

class SourceSerializer(ModelSerializer):
    class Meta:
        model = Source
        fields = '__all__'

class QuestionsSerializer(ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class AnswerSerializer(ModelSerializer):
    class Meta:
        model = Answer
        fields = '__all__'

class DocumentsSerializer(ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__' 