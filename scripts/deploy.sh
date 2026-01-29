#!/bin/bash

# Script de déploiement pour django-app-rag
# Usage: ./deploy.sh <environment> <docker_image> <openai_key> <secret_key> <database_url>

set -e  # Exit on error

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier les arguments
if [ $# -lt 5 ]; then
    log_error "Usage: $0 <environment> <docker_image> <openai_key> <secret_key> <database_url>"
    exit 1
fi

ENVIRONMENT=$1
DOCKER_IMAGE=$2
OPENAI_API_KEY=$3
SECRET_KEY=$4
DATABASE_URL=$5

log_info "Starting deployment to $ENVIRONMENT environment"
log_info "Docker image: $DOCKER_IMAGE"

# Configuration selon l'environnement
if [ "$ENVIRONMENT" = "production" ]; then
    APP_DIR="/opt/django-app-rag"
    APP_PORT=8000
    HTTP_PORT=80
    HTTPS_PORT=443
    DEBUG=False
elif [ "$ENVIRONMENT" = "develop" ]; then
    APP_DIR="/opt/django-app-rag-dev"
    APP_PORT=8001
    HTTP_PORT=8080
    HTTPS_PORT=8443
    DEBUG=False
else
    log_error "Unknown environment: $ENVIRONMENT"
    exit 1
fi

log_info "Deployment directory: $APP_DIR"

# Créer le répertoire de déploiement
sudo mkdir -p $APP_DIR
cd $APP_DIR

# Copier les fichiers de configuration
log_info "Copying configuration files..."
sudo cp /tmp/docker-compose.yml $APP_DIR/docker-compose.yml

# Créer le fichier .env
log_info "Creating environment file..."
sudo tee $APP_DIR/.env > /dev/null <<EOF
# Environment
ENVIRONMENT=$ENVIRONMENT

# Docker
DOCKER_IMAGE=$DOCKER_IMAGE

# Django
SECRET_KEY=$SECRET_KEY
DEBUG=$DEBUG
ALLOWED_HOSTS=*

# Database
DATABASE_URL=$DATABASE_URL
POSTGRES_PASSWORD=$(echo $DATABASE_URL | sed -n 's/.*:\([^@]*\)@.*/\1/p')
POSTGRES_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
POSTGRES_DB=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

# OpenAI
OPENAI_API_KEY=$OPENAI_API_KEY
OPENAI_MODEL_ID=gpt-4o-mini

# Ports
APP_PORT=$APP_PORT
HTTP_PORT=$HTTP_PORT
HTTPS_PORT=$HTTPS_PORT

# RAG
ENABLE_RAG_FEATURES=True
ENABLE_CACHE=True
EOF

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose is not installed"
    exit 1
fi

# Se connecter au registry GitHub
log_info "Logging in to GitHub Container Registry..."
echo $GITHUB_TOKEN | sudo docker login ghcr.io -u $GITHUB_ACTOR --password-stdin 2>/dev/null || log_warn "Could not login to GHCR, trying without auth..."

# Pull la nouvelle image
log_info "Pulling Docker image..."
sudo docker pull $DOCKER_IMAGE

# Arrêter les anciens conteneurs
log_info "Stopping old containers..."
sudo docker-compose down || log_warn "No containers to stop"

# Backup de la base de données (si production)
if [ "$ENVIRONMENT" = "production" ]; then
    log_info "Creating database backup..."
    BACKUP_DIR="$APP_DIR/backups"
    sudo mkdir -p $BACKUP_DIR
    BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    sudo docker-compose exec -T db pg_dumpall -U postgres > $BACKUP_FILE 2>/dev/null || log_warn "Could not create backup"

    # Garder seulement les 5 derniers backups
    ls -t $BACKUP_DIR/db_backup_*.sql | tail -n +6 | xargs -r rm
fi

# Démarrer les nouveaux conteneurs
log_info "Starting new containers..."
sudo docker-compose up -d

# Attendre que les services soient prêts
log_info "Waiting for services to be healthy..."
sleep 10

# Vérifier la santé des conteneurs
for i in {1..30}; do
    if sudo docker-compose ps | grep -q "unhealthy"; then
        log_warn "Some containers are unhealthy, waiting... ($i/30)"
        sleep 2
    else
        log_info "All containers are healthy"
        break
    fi

    if [ $i -eq 30 ]; then
        log_error "Containers failed to become healthy"
        sudo docker-compose logs
        exit 1
    fi
done

# Exécuter les migrations
log_info "Running database migrations..."
sudo docker-compose exec -T app python manage.py migrate --noinput

# Collecter les fichiers statiques
log_info "Collecting static files..."
sudo docker-compose exec -T app python manage.py collectstatic --noinput || log_warn "Could not collect static files"

# Créer un superuser si nécessaire (seulement en dev)
if [ "$ENVIRONMENT" = "develop" ]; then
    log_info "Creating default superuser (admin/admin)..."
    sudo docker-compose exec -T app python manage.py shell <<PYEOF || log_warn "Could not create superuser"
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created')
else:
    print('Superuser already exists')
PYEOF
fi

# Nettoyer les anciennes images
log_info "Cleaning up old Docker images..."
sudo docker image prune -af --filter "until=48h" || log_warn "Could not prune images"

# Afficher l'état final
log_info "Deployment completed successfully!"
log_info "Container status:"
sudo docker-compose ps

# Afficher les logs récents
log_info "Recent logs:"
sudo docker-compose logs --tail=20

# Health check
log_info "Performing health check..."
sleep 5
if curl -f http://localhost:$APP_PORT/health &>/dev/null; then
    log_info "✅ Health check passed"
else
    log_error "❌ Health check failed"
    log_error "Application logs:"
    sudo docker-compose logs app
    exit 1
fi

log_info "🚀 Deployment to $ENVIRONMENT completed successfully!"
log_info "Application is running on port $APP_PORT"

# Afficher les informations de connexion
if [ "$ENVIRONMENT" = "develop" ]; then
    log_info "Dev server: http://localhost:$HTTP_PORT"
    log_info "Admin credentials: admin/admin"
fi

exit 0
