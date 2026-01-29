# Dockerfile de production pour django-app-rag
FROM python:3.11-slim as base

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    # Tesseract pour OCR
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    # Git pour ZenML
    git \
    # Build tools
    gcc \
    g++ \
    make \
    # Cleaning
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Créer utilisateur non-root
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/data /app/log /app/media /app/static && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copier et installer les dépendances Python
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn psycopg2-binary

# Copier le code de l'application
COPY --chown=appuser:appuser . .

# Changer vers l'utilisateur non-root
USER appuser

# Créer les répertoires nécessaires
RUN mkdir -p /app/data/rag_data /app/log /app/media /app/static

# Collecter les fichiers statiques (si nécessaire)
# RUN python manage.py collectstatic --noinput

# Exposer le port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Script d'entrée
COPY --chown=appuser:appuser scripts/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
