#!/usr/bin/env python3
"""
Script pour identifier les documents dupliqués dans media/rag_data/1/crawled/
"""

import os
import hashlib
import json
from pathlib import Path
from collections import defaultdict
import difflib

def get_file_hash(file_path):
    """Calcule le hash MD5 d'un fichier"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_content_hash(content):
    """Calcule le hash MD5 du contenu textuel"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def read_file_content(file_path):
    """Lit le contenu d'un fichier"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"Erreur lecture {file_path}: {e}")
            return None

def analyze_crawled_directory(crawled_dir="/app/media/rag_data/1/crawled"):
    """Analyse le répertoire crawled pour trouver les doublons"""
    
    crawled_path = Path(crawled_dir)
    if not crawled_path.exists():
        print(f"❌ Le répertoire {crawled_dir} n'existe pas!")
        return
    
    print(f"🔍 Analyse du répertoire: {crawled_path.absolute()}")
    print("=" * 80)
    
    # Collecter tous les fichiers
    txt_files = list(crawled_path.glob("*.txt"))
    json_files = list(crawled_path.glob("*.json"))
    
    print(f"📁 Fichiers trouvés:")
    print(f"  - Fichiers .txt: {len(txt_files)}")
    print(f"  - Fichiers .json: {len(json_files)}")
    print()
    
    # Analyser les fichiers .txt (contenu principal)
    print("📝 ANALYSE DES FICHIERS .TXT")
    print("-" * 50)
    
    # 1. Doublons par taille de fichier
    size_groups = defaultdict(list)
    for txt_file in txt_files:
        size = txt_file.stat().st_size
        size_groups[size].append(txt_file)
    
    print(f"📊 Groupes par taille de fichier:")
    for size, files in sorted(size_groups.items()):
        if len(files) > 1:
            print(f"  {size} bytes: {len(files)} fichiers")
            for file in files:
                print(f"    - {file.name}")
        else:
            print(f"  {size} bytes: {len(files)} fichier")
    
    print()
    
    # 2. Doublons par hash de contenu
    content_hash_groups = defaultdict(list)
    content_groups = defaultdict(list)
    
    for txt_file in txt_files:
        content = read_file_content(txt_file)
        if content is not None:
            content_hash = get_content_hash(content)
            content_hash_groups[content_hash].append(txt_file)
            content_groups[content_hash].append((txt_file, content))
    
    print(f"🔐 Doublons par hash de contenu:")
    duplicates_found = False
    for content_hash, files in content_hash_groups.items():
        if len(files) > 1:
            duplicates_found = True
            print(f"\n  Hash: {content_hash}")
            print(f"  Nombre de fichiers: {len(files)}")
            print(f"  Fichiers:")
            for file in files:
                print(f"    - {file.name} ({file.stat().st_size} bytes)")
            
            # Afficher un aperçu du contenu dupliqué
            if content_groups[content_hash]:
                sample_content = content_groups[content_hash][0][1]
                print(f"  Aperçu du contenu (premiers 200 caractères):")
                print(f"    {sample_content[:200]}...")
    
    if not duplicates_found:
        print("  ✅ Aucun doublon de contenu trouvé dans les fichiers .txt")
    
    print()
    
    # 3. Analyser les fichiers .json (métadonnées)
    print("📋 ANALYSE DES FICHIERS .JSON")
    print("-" * 50)
    
    json_content_groups = defaultdict(list)
    json_metadata_groups = defaultdict(list)
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Hash du contenu JSON complet
            json_content = json.dumps(data, sort_keys=True)
            json_content_hash = get_content_hash(json_content)
            json_content_groups[json_content_hash].append(json_file)
            
            # Grouper par métadonnées communes (title, url, etc.)
            if isinstance(data, dict):
                title = data.get('title', 'N/A')
                url = data.get('url', 'N/A')
                metadata_key = f"{title}|{url}"
                json_metadata_groups[metadata_key].append(json_file)
                
        except Exception as e:
            print(f"  ❌ Erreur lecture {json_file.name}: {e}")
    
    print(f"🔐 Doublons par contenu JSON:")
    json_duplicates = False
    for content_hash, files in json_content_groups.items():
        if len(files) > 1:
            json_duplicates = True
            print(f"\n  Hash JSON: {content_hash}")
            print(f"  Nombre de fichiers: {len(files)}")
            for file in files:
                print(f"    - {file.name}")
    
    if not json_duplicates:
        print("  ✅ Aucun doublon de contenu JSON trouvé")
    
    print()
    
    # 4. Correspondance txt/json
    print("🔗 CORRESPONDANCE TXT/JSON")
    print("-" * 50)
    
    txt_names = {f.stem for f in txt_files}
    json_names = {f.stem for f in json_files}
    
    txt_only = txt_names - json_names
    json_only = json_names - txt_names
    both = txt_names & json_names
    
    print(f"📊 Correspondance des noms de fichiers:")
    print(f"  - Fichiers .txt uniquement: {len(txt_only)}")
    print(f"  - Fichiers .json uniquement: {len(json_only)}")
    print(f"  - Fichiers .txt + .json: {len(both)}")
    
    if txt_only:
        print(f"\n  Fichiers .txt sans .json correspondant:")
        for name in sorted(txt_only)[:10]:  # Limiter à 10
            print(f"    - {name}.txt")
        if len(txt_only) > 10:
            print(f"    ... et {len(txt_only) - 10} autres")
    
    if json_only:
        print(f"\n  Fichiers .json sans .txt correspondant:")
        for name in sorted(json_only)[:10]:  # Limiter à 10
            print(f"    - {name}.json")
        if len(json_only) > 10:
            print(f"    ... et {len(json_only) - 10} autres")
    
    print()
    
    # 5. Résumé et recommandations
    print("📋 RÉSUMÉ ET RECOMMANDATIONS")
    print("=" * 80)
    
    total_duplicates = sum(1 for files in content_hash_groups.values() if len(files) > 1)
    total_unique_content = len(content_hash_groups)
    
    print(f"📊 Statistiques finales:")
    print(f"  - Contenu unique: {total_unique_content}")
    print(f"  - Groupes de doublons: {total_duplicates}")
    print(f"  - Fichiers avec doublons: {sum(len(files) for files in content_hash_groups.values() if len(files) > 1)}")
    
    if total_duplicates > 0:
        print(f"\n⚠️  PROBLÈME DÉTECTÉ: {total_duplicates} groupes de contenu dupliqué!")
        print(f"   Cela explique pourquoi votre index FAISS a des chunks avec le même 'id'.")
        print(f"\n🛠️  Actions recommandées:")
        print(f"   1. Nettoyer l'index FAISS existant")
        print(f"   2. Supprimer ou déplacer les fichiers dupliqués")
        print(f"   3. Relancer l'indexation avec des sources propres")
    else:
        print(f"\n✅ Aucun doublon de contenu détecté dans les fichiers sources.")
        print(f"   Le problème pourrait venir d'ailleurs (exécutions multiples du pipeline, etc.)")

if __name__ == "__main__":
    analyze_crawled_directory()
