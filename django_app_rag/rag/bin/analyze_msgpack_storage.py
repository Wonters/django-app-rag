#!/usr/bin/env python3
"""
Script pour analyser le fichier msgpack Low_Tech_1.msgpack
et identifier les doublons dans le stockage
"""

import msgpack
import hashlib
from collections import defaultdict
from pathlib import Path
import json

def analyze_msgpack_storage(msgpack_path="/app/media/rag_data/1/storage/Low_Tech_1.msgpack"):
    """Analyse le fichier msgpack pour identifier les doublons"""
    
    print("🔍 ANALYSE DU STOCKAGE MSGPACK")
    print("=" * 80)
    
    msgpack_file = Path(msgpack_path)
    if not msgpack_file.exists():
        print(f"❌ Le fichier {msgpack_path} n'existe pas!")
        return
    
    print(f"📁 Fichier analysé: {msgpack_file.absolute()}")
    print(f"📊 Taille du fichier: {msgpack_file.stat().st_size} bytes")
    print()
    
    try:
        # Lire le fichier msgpack
        with open(msgpack_file, 'rb') as f:
            data = msgpack.unpackb(f.read(), raw=False)
        
        print(f"✅ Fichier msgpack lu avec succès")
        print(f"📊 Type de données: {type(data)}")
        
        if isinstance(data, dict):
            print(f"🔑 Clés disponibles: {list(data.keys())}")
            print()
            
            # Analyser chaque section
            for key, value in data.items():
                print(f"📋 ANALYSE DE LA SECTION: {key}")
                print("-" * 50)
                
                if isinstance(value, list):
                    print(f"  Type: Liste de {len(value)} éléments")
                    analyze_list_section(key, value)
                elif isinstance(value, dict):
                    print(f"  Type: Dictionnaire avec {len(value)} clés")
                    analyze_dict_section(key, value)
                else:
                    print(f"  Type: {type(value).__name__}")
                    print(f"  Valeur: {str(value)[:200]}...")
                
                print()
        
        elif isinstance(data, list):
            print(f"📋 ANALYSE DE LA LISTE PRINCIPALE")
            print("-" * 50)
            analyze_list_section("root", data)
        
        else:
            print(f"📋 ANALYSE DU CONTENU")
            print("-" * 50)
            print(f"Type: {type(data).__name__}")
            print(f"Contenu: {str(data)[:500]}...")
        
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier msgpack: {e}")
        return

def analyze_list_section(section_name, items):
    """Analyse une section de type liste"""
    
    if not items:
        print("  Liste vide")
        return
    
    print(f"  Nombre d'éléments: {len(items)}")
    
    # Analyser le premier élément pour comprendre la structure
    first_item = items[0]
    print(f"  Type du premier élément: {type(first_item).__name__}")
    
    if isinstance(first_item, dict):
        print(f"  Clés du premier élément: {list(first_item.keys())}")
        
        # Chercher des clés communes importantes
        common_keys = set(first_item.keys())
        for item in items[1:10]:  # Vérifier les 10 premiers
            if isinstance(item, dict):
                common_keys &= set(item.keys())
        
        print(f"  Clés communes: {list(common_keys)}")
        
        # Analyser les doublons potentiels
        if 'content' in common_keys or 'text' in common_keys or 'page_content' in common_keys:
            analyze_content_duplicates(section_name, items)
        elif 'id' in common_keys or 'doc_id' in common_keys:
            analyze_id_duplicates(section_name, items)
        else:
            print(f"  Structure non reconnue pour l'analyse de doublons")
    
    elif isinstance(first_item, str):
        # Analyser les doublons de chaînes
        analyze_string_duplicates(section_name, items)
    
    else:
        print(f"  Type non supporté pour l'analyse de doublons")

def analyze_content_duplicates(section_name, items):
    """Analyse les doublons de contenu"""
    
    print(f"  🔍 ANALYSE DES DOUBLONS DE CONTENU")
    
    # Identifier la clé de contenu
    content_key = None
    for key in ['content', 'text', 'page_content']:
        if key in items[0]:
            content_key = key
            break
    
    if not content_key:
        print(f"    ❌ Aucune clé de contenu trouvée")
        return
    
    print(f"    Clé de contenu utilisée: {content_key}")
    
    # Grouper par hash de contenu
    content_groups = defaultdict(list)
    content_samples = {}
    
    for i, item in enumerate(items):
        if isinstance(item, dict) and content_key in item:
            content = item[content_key]
            if isinstance(content, str):
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                content_groups[content_hash].append(i)
                if content_hash not in content_samples:
                    content_samples[content_hash] = content[:100]
    
    # Analyser les doublons
    duplicates = {hash_val: indices for hash_val, indices in content_groups.items() if len(indices) > 1}
    
    if duplicates:
        print(f"    ⚠️  DOUBLONS DÉTECTÉS: {len(duplicates)} groupes de contenu dupliqué")
        print()
        
        for content_hash, indices in list(duplicates.items())[:5]:  # Limiter à 5 pour l'affichage
            print(f"    📝 Hash: {content_hash}")
            print(f"      Nombre de doublons: {len(indices)}")
            print(f"      Indices: {indices[:10]}{'...' if len(indices) > 10 else ''}")
            print(f"      Aperçu: {content_samples[content_hash]}...")
            print()
        
        if len(duplicates) > 5:
            print(f"    ... et {len(duplicates) - 5} autres groupes de doublons")
        
        # Statistiques
        total_duplicates = sum(len(indices) for indices in duplicates.values())
        print(f"    📊 Statistiques:")
        print(f"      - Contenu unique: {len(content_groups) - len(duplicates)}")
        print(f"      - Groupes de doublons: {len(duplicates)}")
        print(f"      - Total d'éléments dupliqués: {total_duplicates}")
        print(f"      - Taux de duplication: {(total_duplicates / len(items)) * 100:.1f}%")
    else:
        print(f"    ✅ Aucun doublon de contenu détecté")

def analyze_id_duplicates(section_name, items):
    """Analyse les doublons d'ID"""
    
    print(f"  🔍 ANALYSE DES DOUBLONS D'ID")
    
    # Identifier les clés d'ID
    id_keys = []
    for key in ['id', 'doc_id', 'document_id']:
        if key in items[0]:
            id_keys.append(key)
    
    if not id_keys:
        print(f"    ❌ Aucune clé d'ID trouvée")
        return
    
    print(f"    Clés d'ID trouvées: {id_keys}")
    
    # Analyser chaque clé d'ID
    for id_key in id_keys:
        print(f"    📋 Analyse de la clé: {id_key}")
        
        id_groups = defaultdict(list)
        for i, item in enumerate(items):
            if isinstance(item, dict) and id_key in item:
                item_id = item[id_key]
                if item_id is not None:
                    id_groups[str(item_id)].append(i)
        
        # Trouver les doublons
        duplicates = {item_id: indices for item_id, indices in id_groups.items() if len(indices) > 1}
        
        if duplicates:
            print(f"      ⚠️  {len(duplicates)} IDs dupliqués trouvés")
            
            # Afficher quelques exemples
            for item_id, indices in list(duplicates.items())[:3]:
                print(f"        ID: {item_id[:20]}...")
                print(f"          Nombre d'occurrences: {len(indices)}")
                print(f"          Indices: {indices[:5]}{'...' if len(indices) > 5 else ''}")
        else:
            print(f"      ✅ Aucun doublon d'ID trouvé")
        
        print()

def analyze_string_duplicates(section_name, items):
    """Analyse les doublons de chaînes"""
    
    print(f"  🔍 ANALYSE DES DOUBLONS DE CHAÎNES")
    
    # Grouper par hash de contenu
    string_groups = defaultdict(list)
    
    for i, item in enumerate(items):
        if isinstance(item, str):
            string_hash = hashlib.md5(item.encode('utf-8')).hexdigest()
            string_groups[string_hash].append(i)
    
    # Analyser les doublons
    duplicates = {hash_val: indices for hash_val, indices in string_groups.items() if len(indices) > 1}
    
    if duplicates:
        print(f"    ⚠️  {len(duplicates)} chaînes dupliquées trouvées")
        
        # Afficher quelques exemples
        for string_hash, indices in list(duplicates.items())[:3]:
            sample_string = items[indices[0]]
            print(f"      Hash: {string_hash}")
            print(f"        Nombre d'occurrences: {len(indices)}")
            print(f"        Aperçu: {sample_string[:100]}...")
    else:
        print(f"    ✅ Aucune chaîne dupliquée trouvée")

def analyze_dict_section(section_name, data):
    """Analyse une section de type dictionnaire"""
    
    print(f"  Clés: {list(data.keys())}")
    
    # Analyser les valeurs
    for key, value in data.items():
        if isinstance(value, list):
            print(f"    {key}: Liste de {len(value)} éléments")
        elif isinstance(value, dict):
            print(f"    {key}: Dictionnaire avec {len(value)} clés")
        else:
            print(f"    {key}: {type(value).__name__} = {str(value)[:100]}...")

if __name__ == "__main__":
    analyze_msgpack_storage()
