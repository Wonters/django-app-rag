import os
from pathlib import Path
from typing_extensions import Annotated
from zenml import get_step_context, step
from django_app_rag.logging import get_logger_loguru

logger = get_logger_loguru(__name__)

# Désactiver NNPACK et optimisations CPU problématiques
os.environ["USE_NNPACK"] = "0"
os.environ["USE_NATIVE_ARCH"] = "0"
os.environ["USE_AVX"] = "0"
os.environ["USE_AVX2"] = "0"
os.environ["USE_FMA"] = "0"
os.environ["USE_F16C"] = "0"

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractCliOcrOptions,
    PdfBackend,
)
from docling.document_converter import PdfFormatOption

from django_app_rag.rag.models import Document, DocumentMetadata
from django_app_rag.rag import utils


def _get_file_converter(file_path: Path) -> DocumentConverter:
    """Crée un DocumentConverter configuré selon le type de fichier.
    
    Args:
        file_path: Chemin du fichier à traiter
        
    Returns:
        DocumentConverter configuré pour le type de fichier
    """
    file_extension = file_path.suffix.lower()
    
    try:
        if file_extension == '.pdf':
            # Configuration optimisée pour les PDF avec PyPDFium2 (non-ML)
            pdf_opts = PdfPipelineOptions(
                pdf_backend=PdfBackend.PYPDFIUM2,  # parseur non-ML
                do_ocr=True,
                ocr_options=TesseractCliOcrOptions(lang=["eng", "fra"]),
                do_table_structure=False,  # coupe TableFormer (PyTorch)
            )
            
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts)
                }
            )
            logger.info(f"DocumentConverter créé avec configuration PDF optimisée pour {file_path}")
            
        elif file_extension in ['.docx', '.doc']:
            # Configuration pour les documents Word
            converter = DocumentConverter(
                format_options={
                    InputFormat.DOCX: None,  # Utiliser les options par défaut
                    InputFormat.DOC: None,
                }
            )
            logger.info(f"DocumentConverter créé avec configuration Word pour {file_path}")
            
        elif file_extension in ['.txt', '.md', '.rst', '.csv']:
            # Configuration pour les fichiers texte
            converter = DocumentConverter(
                format_options={
                    InputFormat.TEXT: None,
                    InputFormat.MARKDOWN: None,
                    InputFormat.CSV: None,
                }
            )
            logger.info(f"DocumentConverter créé avec configuration texte pour {file_path}")
            
        elif file_extension in ['.html', '.htm']:
            # Configuration pour les fichiers HTML
            converter = DocumentConverter(
                format_options={
                    InputFormat.HTML: None,
                }
            )
            logger.info(f"DocumentConverter créé avec configuration HTML pour {file_path}")
            
        elif file_extension in ['.xlsx', '.xls']:
            # Configuration pour les fichiers Excel
            converter = DocumentConverter(
                format_options={
                    InputFormat.EXCEL: None,
                }
            )
            logger.info(f"DocumentConverter créé avec configuration Excel pour {file_path}")
            
        else:
            # Configuration générique pour les autres types de fichiers
            converter = DocumentConverter()
            logger.info(f"DocumentConverter créé avec configuration générique pour {file_path}")
            
        return converter
        
    except Exception as e:
        logger.warning(f"Impossible de créer DocumentConverter pour {file_path}: {e}")
        return None


def _safe_text_fallback(file_path: Path) -> str:
    """Tentative de lecture sécurisée du fichier en mode texte.
    
    Args:
        file_path: Chemin du fichier à lire
        
    Returns:
        Contenu du fichier en texte, ou message d'erreur si impossible
    """
    file_extension = file_path.suffix.lower()
    
    # Pour les fichiers binaires, on ne peut pas utiliser read_text()
    if file_extension in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.7z']:
        return f"[FICHIER BINAIRE - {file_extension.upper()}] Impossible de lire le contenu en mode texte. Utilisez Docling pour extraire le contenu."
    
    # Pour les fichiers texte, essayer différents encodages
    encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings_to_try:
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.warning(f"Erreur lors de la lecture avec l'encodage {encoding}: {e}")
            continue
    
    # Si aucun encodage ne fonctionne
    return f"[ERREUR ENCODAGE] Impossible de lire le fichier {file_path.name} avec les encodages standards."


@step
def extract_file_documents(
    file_paths: list[Path],
) -> Annotated[list[Document], "file_documents"]:
    """Extract content from multiple files.

    Args:
        file_paths: List of file paths to extract content from.

    Returns:
        list[Document]: List of Document objects with their extracted content.
    """
    documents = []
    
    for file_path in file_paths:
        try:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            # Créer un converter spécifique pour ce type de fichier
            converter = _get_file_converter(file_path)
            
            # Essayer Docling si disponible
            if converter:
                try:
                    logger.info(f"Processing file with Docling: {file_path}")
                    result = converter.convert(str(file_path))
                    
                    # Extraire le contenu du document Docling
                    if result and result.document:
                        content = result.document.export_to_markdown()
                        logger.info(f"Successfully extracted content from {file_path} using Docling")
                        docling_used = True
                        processing_method = "docling_optimized"
                    else:
                        logger.warning(f"Docling failed to extract content from {file_path}, falling back to text reading")
                        content = _safe_text_fallback(file_path)
                        docling_used = False
                        processing_method = "fallback_text_reading"
                        
                except Exception as docling_error:
                    logger.warning(f"Docling error for {file_path}: {docling_error}, using fallback")
                    content = _safe_text_fallback(file_path)
                    docling_used = False
                    processing_method = "fallback_text_reading_after_error"
            else:
                # Fallback direct si Docling n'est pas disponible
                logger.info(f"Using fallback text reading for {file_path}")
                content = _safe_text_fallback(file_path)
                docling_used = False
                processing_method = "fallback_text_reading"
            
            # L'ID sera généré automatiquement par le constructeur de Document basé sur le contenu
            document_metadata = DocumentMetadata(
                id="",  # ID temporaire, sera remplacé par le constructeur
                url=str(file_path),
                title=file_path.name,
                source_type="file",
                properties={
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "file_extension": file_path.suffix,
                    "file_type": file_path.suffix.lower(),
                    "docling_used": docling_used,
                    "processing_method": processing_method,
                    "docling_pipeline": "optimized" if docling_used else "none",
                }
            )
            
            # Créer le document
            document = Document(
                metadata=document_metadata,
                parent_metadata=None,
                content=content,
                child_urls=[],
            )
            
            # Retourner directement l'objet Document
            documents.append(document)
            
            logger.info(f"Successfully extracted document from {file_path}")
            
        except Exception as e:
            logger.error(f"Error extracting document from {file_path}: {e}")
            # En cas d'erreur avec Docling, essayer de lire le fichier en mode texte simple
            try:
                logger.info(f"Attempting fallback text reading for {file_path}")
                content = _safe_text_fallback(file_path)
                
                # L'ID sera généré automatiquement par le constructeur de Document basé sur le contenu
                document_metadata = DocumentMetadata(
                    id="",  # ID temporaire, sera remplacé par le constructeur
                    url=str(file_path),
                    title=file_path.name,
                    source_type="file",
                    properties={
                        "file_path": str(file_path),
                        "file_size": file_path.stat().st_size,
                        "file_extension": file_path.suffix,
                        "file_type": file_path.suffix.lower(),
                        "docling_used": False,
                        "processing_method": "fallback_text_reading_after_error",
                        "error_message": str(e),
                    }
                )
                
                document = Document(
                    metadata=document_metadata,
                    parent_metadata=None,
                    content=content,
                    child_urls=[],
                )
                
                documents.append(document)
                logger.info(f"Successfully extracted document using fallback method from {file_path}")
                
            except Exception as fallback_error:
                logger.error(f"Fallback extraction also failed for {file_path}: {fallback_error}")
                continue

    step_context = get_step_context()
    
    # Compter les documents traités avec Docling vs fallback
    docling_success_count = sum(1 for doc in documents if doc.metadata.properties.get("docling_used", False))
    fallback_count = len(documents) - docling_success_count
    
    # Analyser les types de fichiers traités
    file_types = {}
    for doc in documents:
        file_type = doc.metadata.properties.get("file_type", "unknown")
        file_types[file_type] = file_types.get(file_type, 0) + 1
    
    step_context.add_output_metadata(
        output_name="file_documents",
        metadata={
            "len_documents": len(documents),
            "processed_files": len(file_paths),
            "successful_extractions": len(documents),
            "docling_successful_extractions": docling_success_count,
            "fallback_extractions": fallback_count,
            "file_types_processed": file_types,
            "docling_version": "2.44.0+",
        },
    )

    return documents 