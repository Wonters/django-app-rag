#!/usr/bin/env python3
"""
Script pour analyser les doublons dans l'index FAISS
et comprendre pourquoi il y a des chunks avec le même ID
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from django_app_rag.rag.retrievers import get_retriever
from django_app_rag.rag.models import Document
from collections import defaultdict
import hashlib

def analyze_faiss_duplicates():
    """Analyse les doublons dans l'index FAISS"""
    
    print("🔍 ANALYSE DES DOUBLONS DANS L'INDEX FAISS")
    print("=" * 80)
    
    # Initialiser le retriever
    retriever = get_retriever(
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        embedding_model_type="huggingface",
        retriever_type="parent",
        k=3,
        device="cpu",
        vectorstore="faiss",
        persistent_path="media/rag_data/1",
    )
    
    # Accéder au vectorstore
    vectorstore = retriever.vectorstore
    docstore = vectorstore.docstore
    
    print(f"📊 Statistiques de l'index:")
    print(f"  - Total chunks: {len(docstore._dict)}")
    
    # Analyser les chunks par ID
    chunks_by_id = defaultdict(list)
    chunks_by_doc_id = defaultdict(list)
    chunks_by_content_hash = defaultdict(list)
    
    for chunk_id, chunk in docstore._dict.items():
        # Regroupement par ID de chunk
        chunks_by_id[chunk.metadata['id']].append(chunk)
        
        # Regroupement par ID de document
        chunks_by_doc_id[chunk.metadata['doc_id']].append(chunk)
        
        # Regroupement par hash du contenu
        content_hash = hashlib.md5(chunk.page_content.encode('utf-8')).hexdigest()
        chunks_by_content_hash[content_hash].append(chunk)
    
    print(f"  - Chunks uniques par ID: {len(chunks_by_id)}")
    print(f"  - Documents originaux: {len(chunks_by_doc_id)}")
    print(f"  - Contenus uniques: {len(chunks_by_content_hash)}")
    print()
    
    # === ANALYSE DES CHUNKS AVEC LE MÊME ID ===
    print("🔐 CHUNKS AVEC LE MÊME ID")
    print("-" * 50)
    
    id_duplicates = {chunk_id: chunks for chunk_id, chunks in chunks_by_id.items() if len(chunks) > 1}
    
    if id_duplicates:
        print(f"⚠️  PROBLÈME DÉTECTÉ: {len(id_duplicates)} IDs de chunks dupliqués!")
        print()
        
        for chunk_id, chunks in id_duplicates.items():
            print(f"📝 ID dupliqué: {chunk_id}")
            print(f"  Nombre de chunks: {len(chunks)}")
            print(f"  Chunks:")
            
            for i, chunk in enumerate(chunks):
                print(f"    Chunk {i+1}:")
                print(f"      - doc_id: {chunk.metadata['doc_id']}")
                print(f"      - title: {chunk.metadata.get('title', 'N/A')}")
                print(f"      - url: {chunk.metadata.get('url', 'N/A')}")
                print(f"      - content_hash: {hashlib.md5(chunk.page_content.encode('utf-8')).hexdigest()}")
                print(f"      - content_preview: {chunk.page_content[:100]}...")
                
                # Vérifier si le contenu est identique
                if i > 0:
                    is_identical = chunk.page_content == chunks[0].page_content
                    print(f"      - Identique au premier: {'✅ OUI' if is_identical else '❌ NON'}")
                print()
    else:
        print("✅ Aucun doublon d'ID de chunk détecté")
    
    print()
    
    # === ANALYSE DES CHUNKS AVEC LE MÊME CONTENU ===
    print("📄 CHUNKS AVEC LE MÊME CONTENU")
    print("-" * 50)
    
    content_duplicates = {content_hash: chunks for content_hash, chunks in chunks_by_content_hash.items() if len(chunks) > 1}
    
    if content_duplicates:
        print(f"📊 {len(content_duplicates)} groupes de contenu dupliqué:")
        print()
        
        for content_hash, chunks in content_duplicates.items():
            print(f"🔍 Hash de contenu: {content_hash}")
            print(f"  Nombre de chunks: {len(chunks)}")
            print(f"  Aperçu du contenu: {chunks[0].page_content[:100]}...")
            print(f"  Chunks:")
            
            for i, chunk in enumerate(chunks):
                print(f"    - Chunk {i+1}: ID={chunk.metadata['id']}, doc_id={chunk.metadata['doc_id']}")
                print(f"      Title: {chunk.metadata.get('title', 'N/A')}")
                print(f"      URL: {chunk.metadata.get('url', 'N/A')}")
            print()
    else:
        print("✅ Aucun doublon de contenu détecté")
    
    print()
    
    # === ANALYSE DES DOCUMENTS AVEC PLUSIEURS CHUNKS ===
    print("📚 DOCUMENTS AVEC PLUSIEURS CHUNKS")
    print("-" * 50)
    
    doc_multiple_chunks = {doc_id: chunks for doc_id, chunks in chunks_by_doc_id.items() if len(chunks) > 1}
    
    if doc_multiple_chunks:
        print(f"📊 {len(doc_multiple_chunks)} documents avec plusieurs chunks:")
        print()
        
        # Trier par nombre de chunks décroissant
        sorted_docs = sorted(doc_multiple_chunks.items(), key=lambda x: len(x[1]), reverse=True)
        
        for doc_id, chunks in sorted_docs[:10]:  # Afficher les 10 premiers
            print(f"📄 Document: {doc_id[:12]}...")
            print(f"  Nombre de chunks: {len(chunks)}")
            
            # Afficher les métadonnées du premier chunk
            first_chunk = chunks[0]
            print(f"  Titre: {first_chunk.metadata.get('title', 'N/A')}")
            print(f"  URL: {first_chunk.metadata.get('url', 'N/A')}")
            
            # Vérifier la cohérence des métadonnées
            metadata_consistent = True
            for chunk in chunks[1:]:
                if (chunk.metadata.get('title') != first_chunk.metadata.get('title') or
                    chunk.metadata.get('url') != first_chunk.metadata.get('url')):
                    metadata_consistent = False
                    break
            
            print(f"  Métadonnées cohérentes: {'✅ OUI' if metadata_consistent else '❌ NON'}")
            print()
    else:
        print("✅ Tous les documents ont un seul chunk")
    
    print()
    
    # === RÉSUMÉ ET RECOMMANDATIONS ===
    print("📋 RÉSUMÉ ET RECOMMANDATIONS")
    print("=" * 80)
    
    total_duplicate_chunks = sum(len(chunks) for chunks in id_duplicates.values())
    total_unique_chunks = len(docstore._dict) - total_duplicate_chunks + len(id_duplicates)
    
    print(f"📊 Statistiques finales:")
    print(f"  - Chunks totaux: {len(docstore._dict)}")
    print(f"  - Chunks uniques: {total_unique_chunks}")
    print(f"  - Chunks dupliqués: {total_duplicate_chunks}")
    print(f"  - Taux de duplication: {(total_duplicate_chunks / len(docstore._dict)) * 100:.1f}%")
    
    if id_duplicates:
        print(f"\n🚨 PROBLÈME MAJEUR: {len(id_duplicates)} IDs de chunks dupliqués!")
        print(f"   Cela explique pourquoi votre index FAISS a des chunks avec le même 'id'.")
        print(f"\n🔍 Causes probables:")
        print(f"   1. Documents sources avec du contenu identique (erreurs 403, pages vides, etc.)")
        print(f"   2. Pipeline d'indexation exécuté plusieurs fois sans nettoyage")
        print(f"   3. Problème dans le splitter qui génère des chunks identiques")
        print(f"\n🛠️  Solutions:")
        print(f"   1. Nettoyer l'index FAISS existant")
        print(f"   2. Filtrer les documents sources avec un score de qualité trop bas")
        print(f"   3. Ajouter une vérification de doublons avant l'indexation")
        print(f"   4. Relancer l'indexation avec des sources propres")
    else:
        print(f"\n✅ Aucun problème de duplication d'ID détecté")

if __name__ == "__main__":
    analyze_faiss_duplicates()
