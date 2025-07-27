# Pipelines de Collecte de Données

Ce document décrit les pipelines de collecte de données disponibles pour récupérer des informations depuis différentes sources.

## Pipelines Disponibles

### 1. Collecte de Données Notion (`collect_notion_data`)

Collecte des pages depuis des bases de données Notion.

**Utilisation :**
```bash
python run.py retrieve
```

**Configuration :**
- Modifier directement les `database_ids` dans le fichier `run.py`
- Ou créer un fichier de configuration personnalisé

### 2. Collecte de Données depuis des Fichiers (`collect_file_data`)

Extrait le contenu de fichiers locaux (txt, md, etc.).

**Utilisation :**
```bash
python run.py collect-files --config config/collect_files.yaml
```

**Configuration (`config/collect_files.yaml`) :**
```yaml
file_paths:
  - "data/input/documents/document1.txt"
  - "data/input/documents/document2.md"
  - "data/input/documents/document3.pdf"
data_dir: "data"
to_s3: false
```

### 3. Collecte de Données depuis des URLs (`collect_url_data`)

Extrait le contenu de pages web en utilisant un crawler.

**Utilisation :**
```bash
python run.py collect-urls --config config/collect_urls.yaml
```

**Configuration (`config/collect_urls.yaml`) :**
```yaml
urls:
  - "https://example.com/article1"
  - "https://example.com/article2"
  - "https://example.com/documentation"
data_dir: "data"
to_s3: false
max_workers: 10
```

## Pipeline ETL Mixte (`etl_mixed`)

Pipeline ETL qui peut traiter les données de toutes les sources (Notion, fichiers, URLs) en une seule exécution.

**Utilisation :**
```bash
python run.py etl-mixed --config config/etl_mixed.yaml
```

**Configuration (`config/etl_mixed.yaml`) :**
```yaml
data_dir: "data"
load_collection_name: "mixed_collection"
to_s3: false
max_workers: 10
quality_agent_model_id: "gpt-4o-mini"
quality_agent_mock: true
include_notion: true
include_files: true
include_urls: true
```

## Workflow Complet

1. **Collecte des données :**
   ```bash
   # Collecter depuis Notion
   python run.py retrieve
   
   # Collecter depuis des fichiers
   python run.py collect-files --config config/collect_files.yaml
   
   # Collecter depuis des URLs
   python run.py collect-urls --config config/collect_urls.yaml
   ```

2. **Traitement ETL :**
   ```bash
   # Traiter toutes les sources
   python run.py etl-mixed --config config/etl_mixed.yaml
   
   # Ou traiter seulement Notion
   python run.py etl --config config/etl.yaml
   ```

3. **Création de l'index vectoriel :**
   ```bash
   python run.py index --config config/index.yaml
   ```

## Structure des Données

Les données collectées sont organisées dans le répertoire `data/` :

```
data/
├── notion/           # Données collectées depuis Notion
├── files/            # Données collectées depuis des fichiers
├── urls/             # Données collectées depuis des URLs
└── crawled/          # Données traitées par le pipeline ETL
```

## Formats de Fichiers Supportés

### Fichiers
- `.txt` - Fichiers texte
- `.md` - Fichiers Markdown
- `.pdf` - Fichiers PDF (nécessite des dépendances supplémentaires)

### URLs
- Pages web HTML
- Sites avec JavaScript (via le crawler)
- Limitation : respect des robots.txt et rate limiting

## Notes Importantes

1. **Encodage :** Les fichiers sont lus en UTF-8 par défaut
2. **Rate Limiting :** Le crawler d'URLs inclut un délai de 0.5s entre les requêtes
3. **Concurrence :** Configurable via le paramètre `max_workers`
4. **Stockage S3 :** Optionnel, configurable via `to_s3: true`
5. **Qualité :** Les documents reçoivent automatiquement un score de qualité 