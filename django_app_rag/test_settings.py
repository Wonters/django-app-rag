"""
Configuration de test pour pytest-django
Ce fichier contient les paramètres spécifiques pour l'exécution des tests
"""

import os
from pathlib import Path

# Définir le répertoire de base du projet
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Configuration de base Django
SECRET_KEY = 'test-secret-key-for-testing-only'
DEBUG = True
MAINTAIN = False

# Configuration des applications installées pour les tests
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Applications tierces
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'bootstrap4',
    'corsheaders',
    'rest_framework',
    'django_dramatiq',
    
    # Applications du projet
    'django_app_rag',
]

# Configuration des middlewares pour les tests
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# Configuration des templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'django-app-rag/django_app_rag/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Configuration de la base de données de test
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Base de données en mémoire pour les tests
    }
}

# Configuration des URLs - configuration minimale pour les tests
ROOT_URLCONF = 'django_app_rag.urls' if os.path.exists(BASE_DIR / 'django-app-rag/django_app_rag/urls.py') else None
WSGI_APPLICATION = None

# Configuration de l'authentification
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# Configuration des fichiers statiques
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'django-app-rag/django_app_rag/static',
]

# Configuration des fichiers média
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Configuration des sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Configuration des messages
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Configuration de la sécurité pour les tests
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
CSRF_TRUSTED_ORIGINS = ['http://localhost', 'http://127.0.0.1', 'http://testserver']

# Configuration CORS pour les tests
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Configuration de la localisation
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Configuration des locales
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Configuration des fichiers de traduction
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]

# Configuration des middlewares de sécurité pour les tests
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Configuration de Django REST Framework pour les tests
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

# Configuration d'Allauth pour les tests
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Désactivé pour les tests

# Configuration des logs pour les tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Configuration spécifique pour les tests
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Configuration des caches pour les tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Configuration des emails pour les tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Configuration des tâches asynchrones pour les tests
DRAMATIQ_BROKER = 'dramatiq.brokers.stub.StubBroker'
DRAMATIQ_RESULT_BACKEND = 'dramatiq.results.stub.StubResultBackend'

# Configuration des tests
NOSE_ARGS = [
    '--with-coverage',
    '--cover-package=django_app_rag',
    '--cover-html',
    '--cover-html-dir=htmlcov',
]

# Configuration spécifique pour pytest-django
pytest_plugins = ['pytest_django']

# Configuration des marqueurs pytest
pytest_mark = {
    'slow': 'marks tests as slow (deselect with "-m \"not slow\")',
    'integration': 'marks tests as integration tests',
    'unit': 'marks tests as unit tests',
}
