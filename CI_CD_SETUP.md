# Configuration CI/CD - Guide Complet

## 📋 Vue d'Ensemble

Ce projet utilise GitHub Actions pour l'intégration et le déploiement continus (CI/CD) avec :

- **Tests automatiques** sur chaque push/PR
- **Build Docker** automatique après succès des tests
- **Déploiement automatique** sur serveur distant via SSH

## 🏗️ Architecture CI/CD

```
┌─────────────────┐
│  Push to GitHub │
└────────┬────────┘
         │
         v
┌─────────────────┐
│   Run Tests     │  ← PostgreSQL + Python 3.11
│   - Linting     │
│   - Unit Tests  │
│   - Coverage    │
└────────┬────────┘
         │ ✅ Tests pass
         v
┌─────────────────┐
│  Build Docker   │  ← Build & Push to GHCR
│   Image         │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Deploy via SSH │  ← docker-compose on remote
│   to Server     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Health Check   │  ← Verify deployment
└─────────────────┘
```

## 🔧 Configuration Requise

### 1. Secrets GitHub à Configurer

Aller dans **Settings → Secrets and variables → Actions** et ajouter :

#### Secrets Obligatoires

| Secret | Description | Exemple |
|--------|-------------|---------|
| `DEVELOP_IP` | IP du serveur de développement | `192.168.1.100` |
| `SSH_USER` | Utilisateur SSH sur le serveur | `ubuntu` ou `deploy` |
| `SSH_PRIVATE_KEY` | Clé SSH privée pour connexion | Contenu de `~/.ssh/id_rsa` |
| `DJANGO_SECRET_KEY` | Secret key Django (générer) | `django-insecure-xyz...` |
| `OPENAI_API_KEY` | Clé API OpenAI | `sk-...` |
| `DATABASE_URL` | URL de connexion PostgreSQL | `postgresql://user:pass@host:5432/db` |

#### Secrets Optionnels (Production)

| Secret | Description |
|--------|-------------|
| `PRODUCTION_IP` | IP du serveur de production |
| `PRODUCTION_DOMAIN` | Domaine de production |
| `DATABASE_URL_PROD` | URL DB production |
| `NOTION_SECRET_KEY` | Clé Notion API (si utilisé) |
| `AWS_ACCESS_KEY_ID` | Clé AWS (si S3 utilisé) |
| `AWS_SECRET_ACCESS_KEY` | Secret AWS |

### 2. Générer une Clé SSH

Sur votre machine locale :

```bash
# Générer une paire de clés SSH
ssh-keygen -t ed25519 -C "github-actions@your-repo" -f ~/.ssh/deploy_key

# Copier la clé publique sur le serveur distant
ssh-copy-id -i ~/.ssh/deploy_key.pub user@DEVELOP_IP

# Copier la clé privée dans GitHub Secrets
cat ~/.ssh/deploy_key
# → Copier tout le contenu dans SSH_PRIVATE_KEY
```

### 3. Préparer le Serveur Distant

Sur le serveur de déploiement (`DEVELOP_IP`), installer Docker :

```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installer Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Vérifier l'installation
docker --version
docker compose version

# Créer les répertoires
sudo mkdir -p /opt/django-app-rag-dev
sudo chown $USER:$USER /opt/django-app-rag-dev
```

### 4. Configurer le Pare-feu

```bash
# Ouvrir les ports nécessaires
sudo ufw allow 8080/tcp  # HTTP dev
sudo ufw allow 8443/tcp  # HTTPS dev (optionnel)
sudo ufw allow 80/tcp    # HTTP prod
sudo ufw allow 443/tcp   # HTTPS prod
sudo ufw allow 22/tcp    # SSH
sudo ufw enable
```

## 🚀 Workflow CI/CD

### Branches et Environnements

| Branche | Environnement | URL | Déploiement |
|---------|---------------|-----|-------------|
| `develop` | Development | `http://DEVELOP_IP:8080` | Automatique |
| `main` | Production | `https://PRODUCTION_DOMAIN` | Automatique |

### Processus de Déploiement

#### 1. **Tests** (job `test`)
- Installation des dépendances système (tesseract)
- Installation des dépendances Python
- Linting avec flake8
- Exécution des tests avec pytest
- Génération du rapport de couverture
- Upload vers Codecov

#### 2. **Build** (job `build`)
- Construction de l'image Docker
- Tag avec le nom de la branche + SHA
- Push vers GitHub Container Registry (GHCR)

#### 3. **Déploiement** (job `deploy-develop` ou `deploy-production`)
- Connexion SSH au serveur
- Copie des fichiers de configuration
- Exécution du script de déploiement
- Pull de la nouvelle image Docker
- Arrêt des anciens conteneurs
- Backup de la base de données (production)
- Démarrage des nouveaux conteneurs
- Migrations de base de données
- Health check
- Nettoyage des anciennes images

## 📦 Composants du Déploiement

### Services Docker

Le `docker-compose.prod.yml` lance 5 services :

1. **db** (PostgreSQL 15)
   - Base de données principale
   - Volume persistant
   - Health checks

2. **redis** (Redis 7)
   - Cache et queue Dramatiq
   - Volume persistant

3. **app** (Django + Gunicorn)
   - Application web principale
   - 4 workers, 2 threads
   - Port 8000

4. **dramatiq** (Workers asynchrones)
   - 2 processus, 4 threads
   - Traitement des tâches RAG

5. **nginx** (Reverse proxy)
   - Port 80 (HTTP) et 443 (HTTPS)
   - Gestion des fichiers statiques
   - Load balancing

## 🔍 Monitoring et Logs

### Voir les Logs

Sur le serveur de déploiement :

```bash
# Logs de tous les services
cd /opt/django-app-rag-dev
sudo docker-compose logs

# Logs d'un service spécifique
sudo docker-compose logs app
sudo docker-compose logs dramatiq

# Logs en temps réel
sudo docker-compose logs -f

# Dernières 100 lignes
sudo docker-compose logs --tail=100
```

### État des Conteneurs

```bash
# Voir l'état
sudo docker-compose ps

# Vérifier la santé
sudo docker-compose ps | grep healthy

# Ressources utilisées
sudo docker stats
```

### Accéder à un Conteneur

```bash
# Shell dans le conteneur app
sudo docker-compose exec app bash

# Shell Django
sudo docker-compose exec app python manage.py shell

# Voir les migrations
sudo docker-compose exec app python manage.py showmigrations
```

## 🛠️ Dépannage

### Problème : Tests échouent

```bash
# Vérifier les logs GitHub Actions
# Aller dans l'onglet "Actions" du repo

# Lancer les tests localement
pytest django_app_rag/tests/ --verbose
```

### Problème : Build Docker échoue

```bash
# Vérifier les secrets GitHub
# Settings → Secrets → Vérifier GITHUB_TOKEN

# Tester le build localement
docker build -t test-image .
```

### Problème : Déploiement SSH échoue

```bash
# Tester la connexion SSH manuellement
ssh -i ~/.ssh/deploy_key user@DEVELOP_IP

# Vérifier les permissions
ls -la ~/.ssh/deploy_key
# Devrait être: -rw------- (600)

# Vérifier la clé dans GitHub Secrets
# Ne pas inclure d'espaces ou de retours à la ligne supplémentaires
```

### Problème : Conteneurs ne démarrent pas

```bash
# Voir les logs
cd /opt/django-app-rag-dev
sudo docker-compose logs

# Vérifier la configuration
sudo docker-compose config

# Recréer les conteneurs
sudo docker-compose down
sudo docker-compose up -d

# Vérifier les volumes
sudo docker volume ls
```

### Problème : Health check échoue

```bash
# Tester manuellement
curl http://localhost:8000/health

# Voir les logs de l'app
sudo docker-compose logs app

# Entrer dans le conteneur
sudo docker-compose exec app bash
# Puis tester:
python manage.py check
```

## 🔄 Rollback

En cas de problème après déploiement :

```bash
# Sur le serveur
cd /opt/django-app-rag-dev

# Voir les images disponibles
sudo docker images | grep django-app-rag

# Modifier .env pour utiliser l'ancienne image
sudo nano .env
# Changer DOCKER_IMAGE vers l'ancienne version

# Redéployer
sudo docker-compose down
sudo docker-compose up -d

# Restaurer la base de données (si nécessaire)
sudo docker-compose exec -T db psql -U postgres < backups/db_backup_YYYYMMDD_HHMMSS.sql
```

## 📊 Optimisations

### Accélérer les Tests

Modifier `.github/workflows/ci-cd.yml` :

```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### Accélérer le Build Docker

Utilise déjà `cache-from` et `cache-to` avec GitHub Actions cache.

### Réduire la Taille de l'Image

L'image actuelle utilise déjà Python slim et nettoie les dépendances.

Pour aller plus loin :
```dockerfile
# Utiliser une image alpine (plus petite)
FROM python:3.11-alpine

# Multi-stage build (non implémenté actuellement)
```

## 🔐 Sécurité

### Bonnes Pratiques Implémentées

- ✅ Conteneurs en mode non-root
- ✅ Secrets stockés dans GitHub Secrets
- ✅ Clés SSH dédiées pour le déploiement
- ✅ Health checks sur tous les services
- ✅ Logs détaillés pour audit
- ✅ Backups automatiques de la base de données
- ✅ Isolation réseau avec Docker networks

### Recommandations Supplémentaires

1. **SSL/TLS** : Configurer Let's Encrypt pour HTTPS
2. **Pare-feu** : Restreindre l'accès SSH à des IPs spécifiques
3. **Rotation des secrets** : Changer régulièrement les clés
4. **Monitoring** : Ajouter Prometheus + Grafana
5. **Rate limiting** : Configurer dans nginx

## 📚 Commandes Utiles

### Déploiement Manuel

```bash
# Sur votre machine locale
ssh user@DEVELOP_IP

# Sur le serveur
cd /opt/django-app-rag-dev
sudo docker-compose pull
sudo docker-compose up -d
sudo docker-compose exec app python manage.py migrate
```

### Créer un Backup

```bash
# Base de données
sudo docker-compose exec db pg_dumpall -U postgres > backup_$(date +%Y%m%d).sql

# Volumes
sudo tar czf volumes_backup.tar.gz /var/lib/docker/volumes/django-app-rag*
```

### Nettoyer Docker

```bash
# Supprimer les images non utilisées
sudo docker image prune -a

# Supprimer les conteneurs arrêtés
sudo docker container prune

# Nettoyer tout
sudo docker system prune -a --volumes
```

## 📞 Support

En cas de problème :

1. Vérifier les logs : `sudo docker-compose logs`
2. Vérifier GitHub Actions : Onglet "Actions" du repo
3. Vérifier les secrets : Settings → Secrets
4. Consulter la documentation Docker
5. Ouvrir une issue GitHub

---

## 🎯 Checklist de Configuration

Avant le premier déploiement :

- [ ] Secrets GitHub configurés
- [ ] Clé SSH générée et copiée sur le serveur
- [ ] Docker installé sur le serveur
- [ ] Pare-feu configuré
- [ ] Variables d'environnement vérifiées
- [ ] Tests locaux passent
- [ ] Build Docker réussit localement
- [ ] Connexion SSH testée

**Prêt pour le déploiement !** 🚀

---

**Dernière mise à jour** : 2026-01-29
**Version** : 1.0.0
