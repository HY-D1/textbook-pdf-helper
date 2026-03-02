# Performance Optimization Guide

This guide documents the performance optimizations available for the ALGL PDF Helper.

## Quick Wins

### 1. Install orjson for Faster JSON

```bash
pip install orjson
```

**Impact**: 2-10x faster JSON serialization for large documents.

**Benchmarks**:
- Without orjson: ~2s for 3000 chunks
- With orjson: ~0.2s for 3000 chunks

### 2. Use Compact JSON for Large Documents

For documents >1000 pages, use compact JSON (no indentation):

```python
from algl_pdf_helper.optimized_indexer import optimize_for_large_document

settings = optimize_for_large_document(page_count=1500)
# Returns: {"skip_pretty_print": True, ...}
```

**Impact**: 30-50% smaller output files, 10-20% faster writes.

## Advanced Optimizations

### 3. Parallel Page Extraction

The PDF extraction is the primary bottleneck (61.5% of processing time). 

**Current** (sequential):
```python
for i in range(doc.page_count):
    page = doc.load_page(i)
    text = page.get_text("text")
```

**Optimized** (parallel - future implementation):
```python
from concurrent.futures import ThreadPoolExecutor

def extract_page(page_num):
    page = doc.load_page(page_num)
    return page_num, page.get_text("text")

with ThreadPoolExecutor(max_workers=4) as executor:
    pages = list(executor.map(extract_page, range(doc.page_count)))
```

**Expected Impact**: 2-4x speedup on multi-core systems for I/O-bound extraction.

### 4. Batch Embedding Generation

**Current** (one at a time):
```python
for chunk_id, chunk_text in chunks:
    emb = build_hash_embedding(chunk_text, dim)
```

**Optimized** (batched):
```python
from algl_pdf_helper.optimized_indexer import MemoryEfficientChunkProcessor

processor = MemoryEfficientChunkProcessor(batch_size=1000)
batch_embeddings = processor.generate_embeddings_batch(
    texts=[text for _, text in chunks],
    embedding_dim=24,
    embedding_func=build_hash_embedding
)
```

**Expected Impact**: 10-20% reduction in embedding time.

### 5. Streaming JSON Writes

For very large documents to reduce peak memory:

```python
from algl_pdf_helper.optimized_indexer import streaming_json_write

streaming_json_write(
    chunks,
    output_path / "chunks.json",
    batch_size=1000
)
```

**Impact**: Constant memory usage regardless of chunk count.

## Memory Optimization

### Estimate Memory Before Processing

```python
from algl_pdf_helper.optimized_indexer import estimate_memory_usage

estimate = estimate_memory_usage(
    page_count=1000,
    avg_words_per_page=500,
    chunk_words=180,
    overlap_words=30,
    embedding_dim=24,
)

print(f"Estimated memory: {estimate['total_estimate_mb']:.1f} MB")
print(f"Estimated chunks: {estimate['estimated_chunks']}")
```

### Memory Tuning by Document Size

| Document Size | Recommended Settings |
|---------------|---------------------|
| < 100 pages | Default settings |
| 100-500 pages | batch_size=1000 |
| 500-1000 pages | batch_size=2000, gc_interval=500 |
| > 1000 pages | streaming writes, batch_size=2000 |

## Profiling Your Own PDFs

Use the provided profiling script:

```bash
cd test_reports
python detailed_profiling.py --pdf /path/to/your.pdf
```

This will generate a cProfile report showing exactly where time is spent.

## Performance Checklist

Before processing large batches:

- [ ] Install orjson: `pip install orjson`
- [ ] Ensure adequate disk space (2x PDF size for OCR temp files)
- [ ] Set appropriate batch sizes for document count
- [ ] Consider disabling asset extraction for speed: `extract_assets=False`
- [ ] Monitor memory with `tracemalloc` for new document types

## Benchmark Your System

```bash
cd test_reports
python performance_stress_test.py
```

This runs the full test suite and generates a report tailored to your hardware.

## Known Limitations

1. **GIL Constraints**: Python's Global Interpreter Lock limits true parallelism for CPU-bound operations
2. **PyMuPDF I/O**: PDF extraction is I/O bound and single-threaded per document
3. **OCR Overhead**: OCR processing is 10-100x slower than direct extraction

## Future Optimizations

Planned improvements:

1. **Process-based parallelism** for PDF batch processing
2. **GPU acceleration** for embedding generation (if using ML-based embeddings)
3. **Memory-mapped file access** for very large PDFs
4. **Incremental indexing** for append-only document updates
