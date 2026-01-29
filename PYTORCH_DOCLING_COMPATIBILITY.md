# PyTorch & Docling Compatibility

## Overview

This document describes the PyTorch and Docling compatibility status, known issues, and workarounds.

## PyTorch Requirements

**Version**: `torch==2.4.1`, `torchvision==0.19.1`

PyTorch is required for:
- **Docling**: Document layout analysis, table extraction, OCR features
- **Sentence Transformers**: Embedding models (some models)
- **Advanced document processing**: Deep learning-based features

## Previous Issues

### I/O Issues (Resolved)

PyTorch and torchvision were temporarily disabled in `requirements.txt` due to I/O issues. These have been resolved in the current version.

**Previous error symptoms**:
- File I/O timeouts during installation
- Slow model loading
- Memory issues during document processing

**Resolution**:
- Updated to PyTorch 2.4.1 (stable)
- Verified compatibility with Docling 2.44.0+
- Tested with various document types (PDF, DOCX, images)

## Docling Features Requiring PyTorch

| Feature | PyTorch Required | Fallback Available |
|---------|------------------|-------------------|
| PDF text extraction | No | ✅ Native PDF parsing |
| Table detection | Yes | ⚠️ Limited fallback |
| Layout analysis | Yes | ⚠️ Text-only mode |
| OCR (images in PDFs) | Yes | ❌ No fallback |
| Mathematical formulas | Yes | ⚠️ Text representation |

## Installation

### Standard Installation (with PyTorch)

```bash
pip install -r requirements.txt
```

### Lightweight Installation (without PyTorch)

If you don't need advanced document features:

```bash
pip install -r requirements.txt --no-deps
pip install crawl4ai tiktoken pydantic-settings django-dramatiq \
    langchain langchain-community zenml faiss-cpu sentence-transformers
```

**Note**: This will disable:
- Advanced table extraction
- OCR for images
- Layout analysis

## Testing PyTorch Installation

Run the following to verify PyTorch is working:

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CPU threads: {torch.get_num_threads()}")
```

## Testing Docling with PyTorch

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("test.pdf")
print(f"Extracted {len(result.pages)} pages")
```

## Performance Considerations

### CPU vs GPU

- **CPU mode** (default): Works on all systems, slower for large documents
- **GPU mode**: Requires CUDA-compatible GPU, 10-50x faster for complex documents

### Memory Requirements

| Document Type | RAM Required (CPU) | RAM Required (GPU) |
|---------------|-------------------|-------------------|
| Simple PDF (<10 pages) | 2-4 GB | 1-2 GB |
| Complex PDF (tables, images) | 4-8 GB | 2-4 GB |
| Large PDF (>100 pages) | 8-16 GB | 4-8 GB |

### Optimization Tips

1. **Batch processing**: Process documents in batches of 5-10
2. **Device selection**: Use `device="cpu"` in config for CPU-only systems
3. **Model caching**: PyTorch models are cached after first use
4. **Memory cleanup**: Call `torch.cuda.empty_cache()` after processing (GPU only)

## Troubleshooting

### Issue: "RuntimeError: torch not compiled with CUDA"

**Solution**: This is expected on CPU-only systems. Ensure `device: "cpu"` is set in your RAG config.

### Issue: "OSError: [Errno 5] Input/output error"

**Potential causes**:
1. Insufficient disk space
2. Permission issues
3. Corrupted PyTorch installation

**Solution**:
```bash
pip uninstall torch torchvision
pip cache purge
pip install torch==2.4.1 torchvision==0.19.1
```

### Issue: Slow document processing

**Solutions**:
1. Reduce batch size in config
2. Use simpler Docling features (disable OCR if not needed)
3. Increase worker count (but watch memory usage)
4. Consider GPU acceleration for large workloads

## Configuration Examples

### CPU-Only Configuration (rag.yaml)

```yaml
device: "cpu"
quality_agent_mock: false
# Docling will use CPU for all operations
```

### GPU Configuration (if available)

```yaml
device: "cuda"  # or "mps" for Apple Silicon
quality_agent_mock: false
```

### Minimal Processing (no PyTorch features)

```yaml
device: "cpu"
quality_agent_mock: true  # Skip quality scoring
# Use basic text extraction only
```

## Migration from Previous Version

If upgrading from a version where PyTorch was disabled:

1. **Update requirements**:
   ```bash
   pip install torch==2.4.1 torchvision==0.19.1
   ```

2. **Test Docling**:
   ```bash
   python -m django_app_rag.tests.test
   ```

3. **Verify configs**: Ensure `device: "cpu"` is set if you don't have GPU

4. **Monitor resources**: Check memory usage during first runs

## Support Matrix

| Python Version | PyTorch 2.4.1 | Docling 2.44.0+ | Status |
|---------------|---------------|-----------------|--------|
| 3.9 | ✅ | ✅ | Fully supported |
| 3.10 | ✅ | ✅ | Fully supported |
| 3.11 | ✅ | ✅ | Fully supported |
| 3.12 | ⚠️ | ✅ | Limited testing |

## Known Limitations

1. **macOS ARM (M1/M2)**: Use `device: "mps"` for Metal acceleration
2. **Windows**: Some Docling features may require WSL2
3. **Docker**: Ensure sufficient memory allocation (4GB minimum)

## References

- [PyTorch Documentation](https://pytorch.org/docs/stable/)
- [Docling GitHub](https://github.com/DS4SD/docling)
- [Project Issue Tracker](https://github.com/Wonters/django-app-rag/issues)

## Last Updated

- **Date**: 2026-01-29
- **PyTorch Version**: 2.4.1
- **Docling Version**: 2.44.0+
- **Status**: ✅ Stable
