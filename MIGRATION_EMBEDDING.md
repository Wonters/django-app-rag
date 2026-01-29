# Migration vers un Meilleur Modèle d'Embedding - Guide Rapide

## 🎯 Problème Actuel

Votre RAG utilise `sentence-transformers/all-MiniLM-L6-v2` (Score MTEB: ~56) qui donne des résultats de qualité moyenne.

## ⚡ Solution Rapide (3 étapes)

### Option 1: OpenAI (RECOMMANDÉ - Plus Rapide) ⭐

**Temps: ~30 min pour 10k documents**

```bash
# 1. Éditer django_app_rag/rag/config/rag.yaml
embedding_model_id: text-embedding-3-large
embedding_model_type: openai
embedding_model_dim: 3072

# 2. Supprimer les anciens index
rm -rf data/rag_data/*/faiss_store
rm -rf data/rag_data/*/storage

# 3. Réindexer (via interface ou API)
python manage.py shell
>>> from django_app_rag.tasks.etl_tasks import indexing_collection_task
>>> indexing_collection_task.send(collection_id=YOUR_COLLECTION_ID)
```

**Amélioration attendue:** +15% de qualité (MTEB 56 → 64.6)

---

### Option 2: BGE-M3 Open-Source (GPU requis)

**Temps: ~1-2h pour 10k documents**

```bash
# 1. Copier la config
cp django_app_rag/rag/config/rag_bge_m3.yaml django_app_rag/rag/config/rag.yaml

# 2. Vérifier le GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# 3. Supprimer et réindexer (comme Option 1)
```

**Amélioration attendue:** +12% de qualité (MTEB 56 → 63.0)

---

### Option 3: GTE-Large CPU (Déjà configuré par défaut)

**Temps: ~4-8h pour 10k documents (CPU)**

La configuration par défaut a déjà été mise à jour vers `Alibaba-NLP/gte-large-en-v1.5`.

```bash
# Juste supprimer les anciens index et réindexer
rm -rf data/rag_data/*/faiss_store
rm -rf data/rag_data/*/storage
```

**Amélioration attendue:** +10% de qualité (MTEB 56 → 61.5)

---

## 📊 Comparaison Rapide

| Modèle | Score MTEB | Temps (10k docs) | Coût | Requis |
|--------|------------|------------------|------|--------|
| **MiniLM (actuel)** | 56 | ~2h (CPU) | Gratuit | CPU |
| **GTE-Large (nouveau défaut)** | 61.5 | ~4-8h (CPU) | Gratuit | CPU |
| **OpenAI Large** ⭐ | 64.6 | ~30min | $13/100k docs | API key |
| **BGE-M3** | 63.0 | ~1-2h | Gratuit | GPU 8GB+ |

---

## 🧪 Tester la Qualité

Avant/après, testez avec vos requêtes :

```python
from django_app_rag.rag.agents.tools import DiskStorageRetrieverTool

retriever = DiskStorageRetrieverTool(config_path="path/to/config.yaml")
results = retriever.forward("Votre question de test")

# Vérifier la pertinence des documents retournés
```

---

## 📚 Documentation Complète

Voir `EMBEDDING_MODELS_GUIDE.md` pour:
- Comparatif détaillé de tous les modèles
- Guide de migration pas à pas
- Troubleshooting
- Benchmarks internes

---

## 🆘 Problèmes Courants

### "Dimension mismatch"
Vous devez supprimer ET réindexer. Les anciens embeddings ne sont pas compatibles.

### "CUDA out of memory"
Réduisez `processing_batch_size` à 1 dans la config.

### "Lenteur sur CPU"
Normal pour les grands modèles. Utilisez OpenAI ou un GPU.

---

**Dernière mise à jour**: 2026-01-29
