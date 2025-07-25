from django.db import models

class Source(models.Model):
    NOTION = 'notion'
    URL = 'url'
    FILE = 'file'
    SOURCE_TYPE_CHOICES = [
        (NOTION, 'Notion'),
        (URL, 'URL'),
        (FILE, 'File'),
    ]
    type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    link = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.type})"

class Question(models.Model):
    title = models.CharField(max_length=255)
    field = models.TextField(blank=True, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='questions')

    def __str__(self):
        return self.title

class Answer(models.Model):
    title = models.CharField(max_length=255)
    field = models.TextField(blank=True, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='answers')

    def __str__(self):
        return self.title

class Document(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='rag_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.source.title}" 