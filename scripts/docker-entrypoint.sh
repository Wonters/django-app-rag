#!/bin/bash

# Docker entrypoint script for django-app-rag

set -e

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[ENTRYPOINT]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[ENTRYPOINT]${NC} $1"
}

log_info "Starting django-app-rag..."

# Attendre que la base de données soit prête
if [ -n "$DATABASE_URL" ]; then
    log_info "Waiting for database..."

    # Extraire les infos de connexion depuis DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    timeout=30
    while ! nc -z $DB_HOST $DB_PORT 2>/dev/null; do
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            log_warn "Database connection timeout"
            break
        fi
        sleep 1
    done

    if [ $timeout -gt 0 ]; then
        log_info "Database is ready"
    fi
fi

# Attendre que Redis soit prêt (si configuré)
if [ -n "$REDIS_URL" ]; then
    log_info "Waiting for Redis..."

    REDIS_HOST=$(echo $REDIS_URL | sed -n 's|redis://\([^:]*\):.*|\1|p')
    REDIS_PORT=$(echo $REDIS_URL | sed -n 's|redis://[^:]*:\([0-9]*\).*|\1|p')

    timeout=30
    while ! nc -z $REDIS_HOST $REDIS_PORT 2>/dev/null; do
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            log_warn "Redis connection timeout"
            break
        fi
        sleep 1
    done

    if [ $timeout -gt 0 ]; then
        log_info "Redis is ready"
    fi
fi

# Créer les répertoires nécessaires
log_info "Creating directories..."
mkdir -p /app/data/rag_data /app/log /app/media /app/static

# Exécuter les migrations (si c'est l'app web)
if [ "$1" = "gunicorn" ] || [ "$1" = "python" ]; then
    log_info "Running database migrations..."
    python manage.py migrate --noinput || log_warn "Migrations failed, continuing..."
fi

log_info "Starting application: $@"

# Exécuter la commande
exec "$@"
