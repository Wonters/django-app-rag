from django_app_rag.models import Collection
import math

for collection in Collection.objects.all():
    for source in collection.sources.all():
        source.compute_quality_score(reset=False)
        quality_score = source.quality_score
        print(f"{source.title}: {quality_score} {type(quality_score)}")