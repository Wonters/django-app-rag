from rest_framework.serializers import ModelSerializer
from .models import Source, Question, Answer, Collection, Document
from rest_framework import serializers

class SourceSerializer(ModelSerializer):
    questions_count = serializers.SerializerMethodField()
    answers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Source
        fields = '__all__'
    
    def get_questions_count(self, obj):
        return obj.questions.count()
    
    def get_answers_count(self, obj):
        return Answer.objects.filter(question__source=obj).count()
    

class DocumentSerializer(ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'

class AnswerSerializer(ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)
    class Meta:
        model = Answer
        fields = '__all__'

class QuestionSerializer(ModelSerializer):
    answer = AnswerSerializer(read_only=True)
    class Meta:
        model = Question
        fields = '__all__'

class CollectionSerializer(ModelSerializer):
    sources_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = '__all__'
    
    def get_sources_count(self, obj):
        return obj.sources.count() 