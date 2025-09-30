try:
    from core.custom_admin import custom_admin_site
except ImportError:
    from django.contrib import admin
    custom_admin_site = admin.site
from .models import Answer, Document, Question, Source, Collection, RagConfig
# Register your models here.

custom_admin_site.register(Answer)
custom_admin_site.register(Document)
custom_admin_site.register(Question)
custom_admin_site.register(Source)
custom_admin_site.register(Collection)
custom_admin_site.register(RagConfig)