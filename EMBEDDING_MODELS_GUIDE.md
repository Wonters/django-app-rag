# Guide de Sélection des Modèles d'Embedding

## 🎯 Problème Actuel

Le modèle d'embedding par défaut `sentence-transformers/all-MiniLM-L6-v2` présente des limitations :

- **Score MTEB** : ~56-58 (moyen)
- **Dimension** : 384 (configuré à 1536 par erreur)
- **Performance** : Qualité de récupération moyenne
- **Usage** : Bon pour prototypage rapide, mais insuffisant en production

## 📊 Comparatif des Meilleurs Modèles (2025)

### 🏆 Top 5 Modèles Multilingues (MTEB Leaderboard)

| Rang | Modèle | Score MTEB | Dimensions | Langues | Type | Coût/Performance |
|------|--------|------------|------------|---------|------|------------------|
| 1 | **Qwen3-Embedding-8B** | 70.58 | 8192 | 100+ | HuggingFace | ⚠️ GPU requis |
| 2 | **NVIDIA Llama-Embed-Nemotron-8B** | ~69 | 4096 | 100+ | HuggingFace | ⚠️ GPU requis |
| 3 | **Cohere embed-v4** | 65.2 | 1024 | 100+ | API Cohere | 💰 Payant |
| 4 | **OpenAI text-embedding-3-large** | 64.6 | 3072 | Multi | API OpenAI | 💰 Payant |
| 5 | **BGE-M3** | 63.0 | 1024 | 100+ | HuggingFace | ✅ Open-source |

### 🇬🇧 Top Modèles Anglophones (Alternatifs)

| Modèle | Score MTEB | Dimensions | Type | Recommandation |
|--------|------------|------------|------|----------------|
| **gte-Qwen2-7B-instruct** | ~68 | 3584 | HuggingFace | Excellent pour anglais |
| **text-embedding-3-small** | 62.3 | 1536 | API OpenAI | Bon rapport qualité/coût |
| **Alibaba-NLP/gte-large-en-v1.5** | 61.5 | 1024 | HuggingFace | Déjà présent dans configs |
| **BAAI/bge-large-en-v1.5** | 61.0 | 1024 | HuggingFace | Très populaire |

## 🎯 Recommandations par Cas d'Usage

### 1. Production avec Budget API ✅ **RECOMMANDÉ**

**OpenAI text-embedding-3-large**

```yaml
embedding_model_id: text-embedding-3-large
embedding_model_type: openai
embedding_model_dim: 3072
```

**Avantages :**
- ✅ Excellent score MTEB (64.6)
- ✅ Multilingue performant
- ✅ Pas besoin de GPU
- ✅ Scaling automatique
- ✅ Latence faible

**Coût :** $0.13 / 1M tokens (~$0.0013 par 10k documents)

---

### 2. Production Open-Source (GPU disponible) ⚡ **MEILLEUR RAPPORT QUALITÉ**

**BGE-M3 (BAAI)**

```yaml
embedding_model_id: BAAI/bge-m3
embedding_model_type: huggingface
embedding_model_dim: 1024
device: cuda  # ou mps pour Mac M1/M2/M3
```

**Avantages :**
- ✅ Score MTEB élevé (63.0)
- ✅ 100+ langues
- ✅ Open-source (gratuit)
- ✅ Bonne dimension (1024)

**Requis :** GPU avec 8GB+ VRAM

---

### 3. Production Open-Source (CPU uniquement) 💻

**Alibaba-NLP/gte-large-en-v1.5** (déjà dans vos configs)

```yaml
embedding_model_id: Alibaba-NLP/gte-large-en-v1.5
embedding_model_type: huggingface
embedding_model_dim: 1024
device: cpu
```

**Avantages :**
- ✅ Bon score MTEB (61.5)
- ✅ Compatible CPU
- ✅ Open-source
- ✅ Performances correctes

**Note :** Plus lent sur CPU, mais acceptable

---

### 4. Budget Limité (API économique)

**OpenAI text-embedding-3-small**

```yaml
embedding_model_id: text-embedding-3-small
embedding_model_type: openai
embedding_model_dim: 1536
```

**Avantages :**
- ✅ Score MTEB correct (62.3)
- ✅ Coût réduit (5x moins cher que large)
- ✅ Multilingue
- ✅ Pas de GPU requis

**Coût :** $0.02 / 1M tokens

---

### 5. Meilleure Performance Absolue (GPU haute performance)

**Qwen3-Embedding-8B** 🏆 #1 MTEB

```yaml
embedding_model_id: Qwen/Qwen3-Embedding-8B
embedding_model_type: huggingface
embedding_model_dim: 8192
device: cuda
```

**Avantages :**
- ✅ **Meilleur score MTEB (70.58)**
- ✅ 100+ langues
- ✅ Open-source

**Requis :** GPU avec 16GB+ VRAM

---

## 🔧 Migration depuis all-MiniLM-L6-v2

### Étape 1 : Choisir le Nouveau Modèle

Selon votre infrastructure :

- **Vous avez une clé OpenAI** → `text-embedding-3-large` ⭐
- **Vous avez un GPU (8GB+)** → `BAAI/bge-m3`
- **CPU uniquement** → `Alibaba-NLP/gte-large-en-v1.5`

### Étape 2 : Mettre à Jour la Configuration

Éditez `django_app_rag/rag/config/rag.yaml` :

```yaml
# AVANT
embedding_model_id: sentence-transformers/all-MiniLM-L6-v2
embedding_model_type: huggingface
embedding_model_dim: 1536  # ❌ ERREUR (dimension réelle = 384)

# APRÈS (exemple OpenAI)
embedding_model_id: text-embedding-3-large
embedding_model_type: openai
embedding_model_dim: 3072  # ✅ Dimension correcte
```

### Étape 3 : Réindexer les Documents

⚠️ **IMPORTANT** : Les embeddings ne sont pas compatibles entre modèles !

```bash
# Supprimer l'ancien index
rm -rf data/rag_data/*/faiss_store
rm -rf data/rag_data/*/storage

# Relancer l'indexation
python manage.py shell
>>> from django_app_rag.tasks.etl_tasks import indexing_collection_task
>>> indexing_collection_task.send(collection_id=YOUR_COLLECTION_ID)
```

### Étape 4 : Tester la Qualité

Comparez les résultats avant/après :

```python
from django_app_rag.rag.agents.tools import DiskStorageRetrieverTool

retriever = DiskStorageRetrieverTool(config_path="path/to/config.yaml")
results = retriever.forward("Votre question test")
```

---

## 📈 Amélioration de Qualité Attendue

### Avec text-embedding-3-large (OpenAI)

- **Score MTEB** : 56 → 64.6 (+15%)
- **Rappel@10** : ~65% → ~78% (+20%)
- **Précision** : Amélioration notable sur requêtes complexes
- **Multilingue** : Support massif amélioré

### Avec BGE-M3 (Open-source)

- **Score MTEB** : 56 → 63.0 (+12%)
- **Rappel@10** : ~65% → ~75% (+15%)
- **Multilingue** : Excellent (100+ langues)

---

## 🛠️ Configuration Avancée

### Normalisation des Embeddings

Pour HuggingFace, activez la normalisation pour FAISS :

```python
# Dans embeddings.py, modifier get_huggingface_embedding_model
encode_kwargs={"normalize_embeddings": True}  # ✅ Pour FAISS avec similarité cosinus
```

### Optimisation Mémoire

Pour les grands modèles (Qwen3, Nemotron) :

```yaml
processing_batch_size: 1  # Réduire pour économiser VRAM
processing_max_workers: 1
```

### Réduction de Dimension (Optionnel)

OpenAI text-embedding-3-large supporte la réduction :

```python
# Dans embeddings.py pour OpenAI
OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=1024,  # Réduire 3072 → 1024 (perte minime de qualité)
)
```

---

## 💰 Analyse des Coûts

### Coûts API (par million de tokens)

| Modèle | Coût / 1M tokens | Coût pour 100k documents* |
|--------|------------------|---------------------------|
| text-embedding-3-small | $0.02 | ~$2 |
| text-embedding-3-large | $0.13 | ~$13 |
| Cohere embed-v4 | $0.10 | ~$10 |
| BGE-M3 / Qwen3 (HF) | Gratuit | Coût GPU |

*Estimé à 1000 tokens par document

### Coûts Infrastructure GPU

| Configuration | Coût mensuel | Modèles supportés |
|---------------|--------------|-------------------|
| GPU V100 16GB | ~$300-500 | BGE-M3, GTE-large |
| GPU A100 40GB | ~$1000-1500 | Qwen3, Nemotron |
| CPU (gratuit) | $0 | GTE-large (lent) |

---

## 🧪 Benchmarks Internes Recommandés

### 1. Créer un Jeu de Test

```python
TEST_QUERIES = [
    ("Question simple en français", ["doc_id_expected"]),
    ("Complex multilingual query", ["expected_doc_1", "expected_doc_2"]),
    ("Question technique spécialisée", ["technical_doc_id"]),
]
```

### 2. Mesurer le Rappel

```python
def evaluate_model(config_path):
    retriever = DiskStorageRetrieverTool(config_path=config_path)

    total_recall = 0
    for query, expected_ids in TEST_QUERIES:
        results = retriever.forward(query)
        # Parser results et calculer rappel
        recall = calculate_recall(results, expected_ids)
        total_recall += recall

    return total_recall / len(TEST_QUERIES)
```

---

## 🚀 Actions Immédiates Recommandées

### Scénario 1 : Vous avez une clé OpenAI ⭐ **PLUS RAPIDE**

1. Modifier `rag.yaml` :
   ```yaml
   embedding_model_id: text-embedding-3-large
   embedding_model_type: openai
   embedding_model_dim: 3072
   ```

2. Supprimer les anciens index : `rm -rf data/rag_data/*/faiss_store`

3. Réindexer : `python manage.py reindex_all`

**Temps estimé** : 30 min pour 10k documents

---

### Scénario 2 : Open-source avec GPU

1. Modifier `rag.yaml` :
   ```yaml
   embedding_model_id: BAAI/bge-m3
   embedding_model_type: huggingface
   embedding_model_dim: 1024
   device: cuda
   ```

2. Installer le modèle (1ère fois, ~3GB) :
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('BAAI/bge-m3')
   ```

3. Réindexer

**Temps estimé** : 1-2h pour 10k documents (GPU)

---

### Scénario 3 : Open-source CPU

1. Utiliser `Alibaba-NLP/gte-large-en-v1.5` (déjà dans vos configs)

2. Copier la config :
   ```bash
   cp django_app_rag/rag/config/compute_rag_vector_index_huggingface_contextual_simple.yaml \
      django_app_rag/rag/config/rag.yaml
   ```

3. Réindexer

**Temps estimé** : 4-8h pour 10k documents (CPU)

---

## 📚 Références

- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) - Classement officiel des modèles
- [Best Embedding Models 2025](https://app.ailog.fr/en/blog/guides/choosing-embedding-models) - Guide comparatif
- [OpenAI Embeddings Pricing](https://openai.com/api/pricing/) - Tarifs OpenAI
- [Qwen3 Embedding](https://ollama.com/library/qwen3-embedding) - Documentation Qwen3
- [NVIDIA Llama-Embed-Nemotron](https://huggingface.co/blog/nvidia/llama-embed-nemotron-8b) - Modèle NVIDIA

---

## 🆘 Support

Pour toute question ou problème lors de la migration :

1. Vérifier les logs : `tail -f log/rag.log`
2. Tester avec un petit dataset d'abord
3. Comparer les métriques avant/après
4. Ouvrir une issue GitHub si problème

---

**Dernière mise à jour** : 2026-01-29
**Modèle recommandé** : text-embedding-3-large (OpenAI) ou BAAI/bge-m3 (open-source)
