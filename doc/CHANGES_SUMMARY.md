# Résumé des modifications pour ajouter le champ source_type

## Modifications apportées

### 1. Modèle DocumentMetadata (django_app_rag/rag/models.py)
- Ajout du champ `source_type: Literal["notion", "url", "file"]` dans la classe `DocumentMetadata`
- Ce champ indique le type de source du document

### 2. Steps de collecte de données

#### extract_file_documents.py
- Ajout de `source_type="file"` lors de la création des `DocumentMetadata` pour les fichiers
- Appliqué aux deux endroits où les documents sont créés (succès et fallback)

#### extract_url_documents.py  
- Ajout de `source_type="url"` lors de la création des `DocumentMetadata` pour les URLs

#### extract_notion_documents_metadata.py
- Le `NotionDatabaseClient` crée maintenant les `DocumentMetadata` avec `source_type="notion"`

### 3. Infrastructure Notion

#### database.py
- Ajout de `source_type="notion"` lors de la création des `DocumentMetadata` dans `__build_page_metadata`

#### document.py et page.py
- Ajout de `source_type="notion"` lors de la création des `parent_metadata`

### 4. Crawler (crawler.py)
- Ajout de `source_type="url"` lors de la création des `DocumentMetadata` pour les documents crawlés
- Propagation du `source_type` du parent vers les métadonnées des enfants

## Architecture

Le champ `source_type` est maintenant disponible dans les métadonnées de tous les documents, permettant de :

1. **Identifier la source** : Chaque document sait s'il provient d'un fichier, d'une URL ou de Notion
2. **Filtrer par type** : Possibilité de filtrer les documents selon leur source
3. **Traitement différencié** : Possibilité d'appliquer des traitements spécifiques selon le type de source
4. **Traçabilité** : Meilleur suivi de l'origine des documents dans le pipeline RAG

## Compatibilité

- ✅ **Rétrocompatible** : Les documents existants auront un `source_type` par défaut selon leur contexte
- ✅ **Validation** : Le champ utilise `Literal` pour garantir des valeurs valides
- ✅ **Sérialisation** : Compatible avec les méthodes `model_dump_json()` et `model_validate_json()`

## Utilisation

```python
from django_app_rag.rag.models import Document, DocumentMetadata

# Créer un document avec source_type
metadata = DocumentMetadata(
    id="doc_123",
    url="https://example.com",
    title="Example",
    source_type="url",  # "notion", "url", ou "file"
    properties={}
)

document = Document(
    id="doc_123",
    metadata=metadata,
    content="Contenu du document",
    child_urls=[]
)

# Accéder au type de source
print(document.metadata.source_type)  # "url"
```

## Tests

Un script de test `test_source_type.py` a été créé pour vérifier le bon fonctionnement des modifications.
