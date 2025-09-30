# Commandes de Déploiement Django

Ce document décrit les commandes Django personnalisées créées pour faciliter le déploiement et la gestion de l'application.

## Commandes Disponibles

### 1. `build_frontend` (django-app-rag)

Construit les assets frontend pour la production.

```bash
python manage.py build_frontend [options]
```

**Options :**
- `--clean` : Nettoie le répertoire dist avant la construction
- `--install-deps` : Installe les dépendances npm avant la construction
- `--watch` : Lance le serveur de développement en mode watch
- `--app` : Application spécifique à construire (ex: django-app-rag)

**Exemples :**
```bash
# Construction simple pour django-app-rag
python manage.py build_frontend

# Construction avec nettoyage et installation des dépendances
python manage.py build_frontend --clean --install-deps

# Mode développement (watch)
python manage.py build_frontend --watch

# Construction pour une app spécifique
python manage.py build_frontend --app django-app-rag
```

### 2. `production_deploy` (core)

Déploie l'application en production (build frontend + collect static + migrate).

```bash
python manage.py production_deploy [options]
```

**Options :**
- `--skip-build` : Ignore l'étape de construction du frontend
- `--skip-migrate` : Ignore les migrations de base de données
- `--skip-collectstatic` : Ignore la collecte des fichiers statiques
- `--noinput` : Exécute sans demander d'entrée utilisateur
- `--install-deps` : Installe les dépendances npm avant la construction
- `--app` : Application spécifique à construire (ex: django-app-rag)

**Exemples :**
```bash
# Déploiement complet
python manage.py production_deploy

# Déploiement sans interaction utilisateur
python manage.py production_deploy --noinput

# Déploiement sans construction frontend
python manage.py production_deploy --skip-build

# Déploiement pour une app spécifique
python manage.py production_deploy --app django-app-rag
```

### 3. `check_deployment` (home)

Vérifie l'état du déploiement et la configuration.

```bash
python manage.py check_deployment [options]
```

**Options :**
- `--check-frontend` : Vérifie si le frontend est construit
- `--check-static` : Vérifie la configuration des fichiers statiques
- `--app` : Application spécifique à vérifier (ex: django-app-rag)

**Exemples :**
```bash
# Vérification complète
python manage.py check_deployment --check-frontend --check-static

# Vérification basique
python manage.py check_deployment

# Vérification pour une app spécifique
python manage.py check_deployment --check-frontend --app django-app-rag
```

### 4. `production_deploy` (home)

Déploie l'application en production (build frontend + collect static + migrate).

```bash
python manage.py production_deploy [options]
```

**Options :**
- `--skip-build` : Ignore l'étape de construction du frontend
- `--skip-migrate` : Ignore les migrations de base de données
- `--skip-collectstatic` : Ignore la collecte des fichiers statiques
- `--noinput` : Exécute sans demander d'entrée utilisateur
- `--install-deps` : Installe les dépendances npm avant la construction
- `--app` : Application spécifique à construire (ex: django-app-rag)

**Exemples :**
```bash
# Déploiement complet
python manage.py production_deploy

# Déploiement sans interaction utilisateur
python manage.py production_deploy --noinput

# Déploiement sans construction frontend
python manage.py production_deploy --skip-build

# Déploiement pour une app spécifique
python manage.py production_deploy --app django-app-rag
```

### 5. `load_default_data` (home)

Charge les données par défaut pour l'app home (profil, tags, compétences, etc.).

```bash
python manage.py load_default_data [options]
```

**Options :**
- `--clear` : Efface les données existantes avant de charger les données par défaut
- `--fixture` : Fichier de fixture à charger (défaut: default_data.json)

**Exemples :**
```bash
# Chargement simple
python manage.py load_default_data

# Chargement avec effacement des données existantes
python manage.py load_default_data --clear

# Chargement d'une fixture spécifique
python manage.py load_default_data --fixture custom_data.json
```

### 6. `create_default_user` (home)

Crée un superutilisateur par défaut et l'associe au profil par défaut.

```bash
python manage.py create_default_user [options]
```

**Options :**
- `--username` : Nom d'utilisateur (défaut: admin)
- `--email` : Email (défaut: admin@example.com)
- `--password` : Mot de passe (défaut: admin123)
- `--noinput` : Exécute sans demander d'entrée utilisateur

**Exemples :**
```bash
# Création avec paramètres par défaut
python manage.py create_default_user

# Création avec paramètres personnalisés
python manage.py create_default_user --username myuser --email my@email.com --password mypass123
```

### 7. `setup_default` (home)

Configuration complète : crée un superutilisateur, charge les données par défaut et exécute les migrations.

```bash
python manage.py setup_default [options]
```

**Options :**
- `--username` : Nom d'utilisateur (défaut: admin)
- `--email` : Email (défaut: admin@example.com)
- `--password` : Mot de passe (défaut: admin123)
- `--noinput` : Exécute sans demander d'entrée utilisateur
- `--clear-data` : Efface les données existantes avant de charger les données par défaut

**Exemples :**
```bash
# Configuration complète
python manage.py setup_default

# Configuration sans interaction utilisateur
python manage.py setup_default --noinput

# Configuration avec effacement des données
python manage.py setup_default --clear-data
```

## Workflow de Déploiement Recommandé

### 1. Développement
```bash
# Mode développement avec watch
python manage.py build_frontend --watch
```

### 2. Préparation Production
```bash
# Vérification de l'état actuel
python manage.py check_deployment --check-frontend --check-static

# Construction du frontend
python manage.py build_frontend --clean --install-deps
```

### 3. Déploiement Production
```bash
# Déploiement complet
python manage.py production_deploy --noinput

# Vérification post-déploiement
python manage.py check_deployment --check-frontend --check-static
```

## Prérequis

- Node.js et npm installés
- Python et Django configurés
- Base de données configurée
- Variables d'environnement de production définies

## Structure des Fichiers

```
shiftWebSite/
├── home/
│   ├── management/
│   │   └── commands/
│   │       ├── production_deploy.py
│   │       ├── check_deployment.py
│   │       ├── load_default_data.py
│   │       ├── create_default_user.py
│   │       └── setup_default.py
│   └── fixtures/
│       └── default_data.json
├── django-app-rag/
│   ├── django_app_rag/
│   │   └── management/
│   │       └── commands/
│   │           └── build_frontend.py
│   └── static/
│       ├── package.json
│       ├── vite.config.js
│       ├── frontend/
│       └── dist/  # Généré par la construction
```

## Dépannage

### Erreur "npm not found"
Installez Node.js et npm sur votre système.

### Erreur de construction frontend
Vérifiez que les dépendances npm sont installées :
```bash
cd static/
npm install
```

### Erreur de collecte des fichiers statiques
Vérifiez que `STATIC_ROOT` est configuré dans `settings.py`.

### Erreur de migration
Vérifiez la configuration de la base de données et les permissions.
