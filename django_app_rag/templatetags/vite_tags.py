import json
import os
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()

manifest_path = os.path.join(settings.BASE_DIR,'django-app-rag', 'static', 'django_app_rag', 'dist', 'manifest.json')

@register.simple_tag
def vite_asset(entry_name):
    """
    Charge un asset Vite depuis le manifest.json
    Usage: {% vite_asset 'frontend/main.js' %}
    """
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        if entry_name in manifest:
            asset_path = manifest[entry_name]['file']
            return static(f'django_app_rag/dist/{asset_path}')
        else:
            return f'<!-- Asset {entry_name} not found in manifest -->'
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return f'<!-- Error loading manifest for {entry_name} -->'

@register.simple_tag
def vite_css(entry_name):
    """
    Charge le CSS d'un entry Vite
    Usage: {% vite_css 'frontend/main.js' %}
    """    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        if entry_name in manifest and 'css' in manifest[entry_name]:
            css_files = manifest[entry_name]['css']
            # Retourne seulement le premier fichier CSS (ou tous séparés par des virgules)
            if len(css_files) == 1:
                return static(f'django_app_rag/dist/{css_files[0]}')
            else:
                return ','.join([static(f'django_app_rag/dist/{css_file}') for css_file in css_files])
        else:
            return f'<!-- No CSS found for {entry_name} -->'
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return f'<!-- Error loading CSS for {entry_name} -->'
