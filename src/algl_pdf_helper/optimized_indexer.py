"""
Performance-optimized indexing operations.

This module provides optimized versions of critical indexing operations
to improve performance for large PDF processing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

# Try to use orjson for faster JSON serialization
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False


def fast_json_dumps(obj: Any, indent: bool = False) -> str:
    """Fast JSON serialization using orjson if available.
    
    Args:
        obj: Object to serialize
        indent: Whether to pretty-print with indentation
        
    Returns:
        JSON string
    """
    if HAS_ORJSON:
        option = orjson.OPT_INDENT_2 if indent else 0
        return orjson.dumps(obj, option=option).decode('utf-8')
    else:
        # Fall back to standard json
        indent_val = 2 if indent else None
        return json.dumps(obj, indent=indent_val)


def fast_json_dump(obj: Any, path: Path, indent: bool = False) -> None:
    """Fast JSON file write using orjson if available.
    
    Args:
        obj: Object to serialize
        path: Output file path
        indent: Whether to pretty-print with indentation
    """
    if HAS_ORJSON:
        option = orjson.OPT_INDENT_2 if indent else 0
        path.write_bytes(orjson.dumps(obj, option=option))
    else:
        indent_val = 2 if indent else None
        path.write_text(json.dumps(obj, indent=indent_val), encoding='utf-8')


def batch_process_chunks(
    chunks: list[Any],
    batch_size: int = 1000,
) -> list[dict]:
    """Process chunks in batches to reduce memory pressure.
    
    Args:
        chunks: List of chunk objects
        batch_size: Number of chunks per batch
        
    Returns:
        List of serialized chunk dictionaries
    """
    result = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        # Process batch
        for chunk in batch:
            if hasattr(chunk, 'model_dump'):
                result.append(chunk.model_dump())
            else:
                result.append(chunk)
    return result


def estimate_memory_usage(
    page_count: int,
    avg_words_per_page: int = 500,
    chunk_words: int = 180,
    overlap_words: int = 30,
    embedding_dim: int = 24,
) -> dict[str, float]:
    """Estimate memory usage for processing a PDF.
    
    Args:
        page_count: Number of pages in PDF
        avg_words_per_page: Average words per page
        chunk_words: Words per chunk
        overlap_words: Overlap between chunks
        embedding_dim: Embedding dimensions
        
    Returns:
        Dictionary with memory estimates in MB
    """
    # Estimate chunk count
    step = max(1, chunk_words - overlap_words)
    words_per_page = avg_words_per_page
    chunks_per_page = max(1, (words_per_page - chunk_words) // step + 1)
    total_chunks = page_count * chunks_per_page
    
    # Memory estimates (rough approximations)
    text_memory_mb = (page_count * words_per_page * 6) / 1024 / 1024  # ~6 bytes per word
    embedding_memory_mb = (total_chunks * embedding_dim * 8) / 1024 / 1024  # float64
    chunk_metadata_mb = (total_chunks * 200) / 1024 / 1024  # ~200 bytes per chunk metadata
    pdf_overhead_mb = page_count * 0.01  # ~10KB per page overhead
    
    return {
        "text_content_mb": text_memory_mb,
        "embeddings_mb": embedding_memory_mb,
        "chunk_metadata_mb": chunk_metadata_mb,
        "pdf_overhead_mb": pdf_overhead_mb,
        "total_estimate_mb": text_memory_mb + embedding_memory_mb + chunk_metadata_mb + pdf_overhead_mb,
        "estimated_chunks": total_chunks,
    }


def streaming_json_write(
    chunks: list[Any],
    output_path: Path,
    batch_size: int = 1000,
) -> None:
    """Write chunks to JSON file in a streaming manner.
    
    This reduces peak memory usage by writing chunks incrementally
    rather than building the entire JSON structure in memory.
    
    Args:
        chunks: List of chunk objects
        output_path: Output JSON file path
        batch_size: Number of chunks to buffer before writing
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('[\n')
        
        for i, chunk in enumerate(chunks):
            if hasattr(chunk, 'model_dump'):
                chunk_dict = chunk.model_dump()
            else:
                chunk_dict = chunk
            
            # Write chunk
            if i > 0:
                f.write(',\n')
            json.dump(chunk_dict, f)
            
            # Optional: flush periodically
            if i % batch_size == 0:
                f.flush()
        
        f.write('\n]\n')


class MemoryEfficientChunkProcessor:
    """Process chunks with memory efficiency in mind.
    
    This class provides methods for processing large numbers of chunks
    without loading everything into memory at once.
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.processed_count = 0
    
    def process_in_batches(
        self,
        items: list[Any],
        processor: Callable[[list[Any]], list[Any]],
    ) -> list[Any]:
        """Process items in batches.
        
        Args:
            items: List of items to process
            processor: Function to process each batch
            
        Returns:
            List of processed results
        """
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = processor(batch)
            results.extend(batch_results)
            self.processed_count += len(batch)
        
        return results
    
    def generate_embeddings_batch(
        self,
        texts: list[str],
        embedding_dim: int,
        embedding_func: Callable[[str, int], list[float]],
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings
            embedding_dim: Embedding dimension
            embedding_func: Function to generate embedding from text
            
        Returns:
            List of embeddings
        """
        return [embedding_func(text, embedding_dim) for text in texts]


def optimize_for_large_document(page_count: int) -> dict[str, Any]:
    """Get optimized settings for processing large documents.
    
    Args:
        page_count: Number of pages in document
        
    Returns:
        Dictionary with optimized settings
    """
    if page_count > 1000:
        # Very large document optimizations
        return {
            "batch_size": 2000,
            "use_streaming_write": True,
            "gc_interval": 500,  # Force GC every N pages
            "embedding_batch_size": 500,
            "skip_pretty_print": True,  # Use compact JSON
        }
    elif page_count > 500:
        # Large document optimizations
        return {
            "batch_size": 1000,
            "use_streaming_write": True,
            "gc_interval": 1000,
            "embedding_batch_size": 1000,
            "skip_pretty_print": False,
        }
    else:
        # Default settings for normal documents
        return {
            "batch_size": 1000,
            "use_streaming_write": False,
            "gc_interval": None,
            "embedding_batch_size": 1000,
            "skip_pretty_print": False,
        }
