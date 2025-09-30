from django_app_rag.models import Answer
from django.core.management.base import BaseCommand



class Command(BaseCommand):
    help = 'Build the frontend assets for production'
    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-answers',
            type=str,
            help='Delete answers from the database',
        )
    def handle(self, *args, **options):
        if options['delete_answers']:
            print("Deleting answers...")
            Answer.objects.all().delete()
            print("Answers deleted")
