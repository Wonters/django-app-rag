# Generated by Django 4.2.23 on 2025-07-22 14:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_app_rag', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Documents',
            new_name='Document',
        ),
        migrations.RenameModel(
            old_name='Questions',
            new_name='Question',
        ),
    ]
