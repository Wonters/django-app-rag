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
    link = models.URLField(blank=True, null=True)
    notion_db_ids = models.TextField(blank=True, null=True, help_text="Liste des IDs de bases Notion, séparés par des virgules")
    file = models.FileField(upload_to='rag_sources/', blank=True, null=True)
    collection = models.ForeignKey("Collection", on_delete=models.CASCADE, related_name='sources')

    def __str__(self):
        if self.type == Source.NOTION:
            return f"{self.title} ({self.type}: {self.notion_db_ids})"
        elif self.type == Source.URL:
            return f"{self.title} ({self.type}: {self.link})"
        elif self.type == Source.FILE:
            return f"{self.title} ({self.type}: {self.file.name})"
        else:
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
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', null=True, blank=True)

    def __str__(self):
        return self.title

class Collection(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - sources: {self.sources.count()}"
