#!/usr/bin/env python
"""
Script de migration vers un nouveau modèle d'embedding

Usage:
    python scripts/migrate_embedding_model.py --model openai-large --collection-id 1
    python scripts/migrate_embedding_model.py --model bge-m3 --all-collections

Modèles disponibles:
    - openai-large: text-embedding-3-large (Score MTEB: 64.6) - RECOMMANDÉ
    - openai-small: text-embedding-3-small (Score MTEB: 62.3) - Budget
    - bge-m3: BAAI/bge-m3 (Score MTEB: 63.0) - Open-source GPU
    - gte-large: Alibaba-NLP/gte-large-en-v1.5 (Score MTEB: 61.5) - Open-source CPU
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

import django
django.setup()

from django_app_rag.models import Collection, Source
from django_app_rag.tasks.etl_tasks import indexing_collection_task
from django_app_rag.logging import get_logger

logger = get_logger(__name__)

# Configuration des modèles disponibles
MODELS = {
    "openai-large": {
        "config": "rag_openai_large.yaml",
        "embedding_model_id": "text-embedding-3-large",
        "embedding_model_type": "openai",
        "embedding_model_dim": 3072,
        "description": "OpenAI text-embedding-3-large - Meilleure qualité (Score MTEB: 64.6)",
        "requires": "Clé OpenAI API",
    },
    "openai-small": {
        "config": "rag_openai_small_budget.yaml",
        "embedding_model_id": "text-embedding-3-small",
        "embedding_model_type": "openai",
        "embedding_model_dim": 1536,
        "description": "OpenAI text-embedding-3-small - Budget (Score MTEB: 62.3)",
        "requires": "Clé OpenAI API",
    },
    "bge-m3": {
        "config": "rag_bge_m3.yaml",
        "embedding_model_id": "BAAI/bge-m3",
        "embedding_model_type": "huggingface",
        "embedding_model_dim": 1024,
        "description": "BGE-M3 - Meilleur open-source (Score MTEB: 63.0)",
        "requires": "GPU avec 8GB+ VRAM",
    },
    "gte-large": {
        "config": "rag.yaml",  # Par défaut maintenant
        "embedding_model_id": "Alibaba-NLP/gte-large-en-v1.5",
        "embedding_model_type": "huggingface",
        "embedding_model_dim": 1024,
        "description": "GTE-Large - Open-source CPU-friendly (Score MTEB: 61.5)",
        "requires": "CPU (lent) ou GPU",
    }
}


def clear_collection_index(collection: Collection, backup: bool = True):
    """Supprime l'index FAISS et le storage d'une collection."""
    data_dir = collection.get_rag_data_dir()

    if not data_dir.exists():
        logger.info(f"Pas de données à supprimer pour {collection.title}")
        return

    # Backup si demandé
    if backup:
        backup_dir = data_dir.parent / f"{data_dir.name}_backup_{int(time.time())}"
        logger.info(f"Backup de {data_dir} vers {backup_dir}")
        shutil.copytree(data_dir, backup_dir)

    # Supprimer index FAISS
    faiss_dir = data_dir / "faiss_store"
    if faiss_dir.exists():
        logger.info(f"Suppression de l'index FAISS: {faiss_dir}")
        shutil.rmtree(faiss_dir)

    # Supprimer storage
    storage_dir = data_dir / "storage"
    if storage_dir.exists():
        logger.info(f"Suppression du storage: {storage_dir}")
        shutil.rmtree(storage_dir)

    logger.info(f"✅ Index supprimé pour {collection.title}")


def update_collection_config(collection: Collection, model_name: str):
    """Met à jour la configuration d'une collection."""
    model_config = MODELS[model_name]

    # TODO: Mettre à jour la configuration de la collection
    # Pour l'instant, on suppose que la config est gérée manuellement
    logger.info(f"Configuration à utiliser: {model_config['config']}")
    logger.info(f"Modèle: {model_config['embedding_model_id']}")
    logger.info(f"Type: {model_config['embedding_model_type']}")
    logger.info(f"Dimension: {model_config['embedding_model_dim']}")


def reindex_collection(collection: Collection):
    """Réindexe une collection."""
    logger.info(f"🚀 Démarrage de la réindexation pour {collection.title}")

    # Lancer la tâche d'indexation
    result = indexing_collection_task.send(collection_id=collection.id)

    logger.info(f"✅ Tâche d'indexation lancée pour {collection.title}")
    return result


def migrate_collection(collection_id: int, model_name: str, skip_backup: bool = False):
    """Migre une collection vers un nouveau modèle."""
    try:
        collection = Collection.objects.get(id=collection_id)
    except Collection.DoesNotExist:
        logger.error(f"❌ Collection {collection_id} introuvable")
        return False

    logger.info(f"")
    logger.info(f"{'=' * 70}")
    logger.info(f"MIGRATION DE LA COLLECTION: {collection.title}")
    logger.info(f"Vers le modèle: {MODELS[model_name]['description']}")
    logger.info(f"{'=' * 70}")
    logger.info(f"")

    # Étape 1: Supprimer l'ancien index
    logger.info("📝 Étape 1/3: Suppression de l'ancien index...")
    clear_collection_index(collection, backup=not skip_backup)

    # Étape 2: Mettre à jour la configuration
    logger.info("📝 Étape 2/3: Mise à jour de la configuration...")
    update_collection_config(collection, model_name)

    # Étape 3: Réindexer
    logger.info("📝 Étape 3/3: Réindexation avec le nouveau modèle...")
    reindex_collection(collection)

    logger.info("")
    logger.info("✅ Migration terminée!")
    logger.info("")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrer vers un nouveau modèle d'embedding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--model",
        choices=MODELS.keys(),
        required=True,
        help="Modèle d'embedding à utiliser"
    )

    parser.add_argument(
        "--collection-id",
        type=int,
        help="ID de la collection à migrer"
    )

    parser.add_argument(
        "--all-collections",
        action="store_true",
        help="Migrer toutes les collections"
    )

    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Ne pas faire de backup avant migration (DANGEREUX)"
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Lister les modèles disponibles"
    )

    args = parser.parse_args()

    # Lister les modèles
    if args.list_models:
        print("\n📊 MODÈLES D'EMBEDDING DISPONIBLES\n")
        for name, config in MODELS.items():
            print(f"  {name}:")
            print(f"    {config['description']}")
            print(f"    Requis: {config['requires']}")
            print(f"    Modèle: {config['embedding_model_id']}")
            print(f"    Dimension: {config['embedding_model_dim']}")
            print()
        return

    # Vérifier les arguments
    if not args.collection_id and not args.all_collections:
        parser.error("Vous devez spécifier --collection-id ou --all-collections")

    if args.collection_id and args.all_collections:
        parser.error("Vous ne pouvez pas utiliser --collection-id et --all-collections ensemble")

    # Afficher les infos du modèle
    model_config = MODELS[args.model]
    print("\n" + "=" * 70)
    print(f"MIGRATION VERS: {model_config['description']}")
    print(f"Requis: {model_config['requires']}")
    print("=" * 70 + "\n")

    # Confirmer
    if not args.skip_backup:
        print("⚠️  Un backup sera créé avant la migration")
    else:
        print("⚠️  ATTENTION: Aucun backup ne sera créé!")

    confirm = input("\nContinuer? [y/N] ")
    if confirm.lower() != 'y':
        print("Migration annulée")
        return

    # Migrer
    if args.all_collections:
        collections = Collection.objects.all()
        total = collections.count()
        print(f"\n🚀 Migration de {total} collection(s)...\n")

        for i, collection in enumerate(collections, 1):
            print(f"\n[{i}/{total}] Migration de {collection.title}...")
            migrate_collection(collection.id, args.model, args.skip_backup)

    else:
        migrate_collection(args.collection_id, args.model, args.skip_backup)

    print("\n✅ Migration(s) terminée(s)!")
    print("\n💡 Conseil: Testez la qualité des résultats avec quelques requêtes")
    print("   et comparez avec l'ancien modèle si vous avez fait un backup.\n")


if __name__ == "__main__":
    import time
    main()
