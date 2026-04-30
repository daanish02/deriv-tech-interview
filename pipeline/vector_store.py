"""Pinecone vector store for failure taxonomy semantic search (LangChain integration)."""

import json
import logging
import hashlib
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

import config

logger = logging.getLogger(__name__)

# Local query cache file
_QUERY_CACHE_FILE = config.VECTOR_QUERY_CACHE_FILE


def _load_query_cache() -> dict:
    """Load cached query results from disk.

    Returns:
        Dict mapping cache keys to serialized Document lists.
    """
    if _QUERY_CACHE_FILE.exists():
        try:
            return json.loads(_QUERY_CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_query_cache(cache: dict) -> None:
    """Save query cache to disk.

    Args:
        cache: Dict mapping cache keys to serialized Document lists.
    """
    _QUERY_CACHE_FILE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _cache_key(query: str, top_k: int) -> str:
    """Generate cache key from query and top_k.

    Args:
        query: Search query string.
        top_k: Number of results requested.

    Returns:
        MD5 hex digest string.
    """
    return hashlib.md5(f"{query}::{top_k}".encode()).hexdigest()


def _chunk_taxonomy(taxonomy: dict) -> list[Document]:
    """Break taxonomy into LangChain Documents for indexing.

    Args:
        taxonomy: Parsed failure taxonomy dict.

    Returns:
        List of LangChain Document objects.
    """
    documents = []

    def _process(obj, path: str = "") -> None:
        """Recursively traverse taxonomy and append Documents.

        Args:
            obj: Current taxonomy node (dict or list).
            path: Slash-delimited path to current node.
        """
        if isinstance(obj, dict):
            text_parts = []
            metadata = {"path": path}

            for k, v in obj.items():
                if isinstance(v, str):
                    text_parts.append(f"{k}: {v}")
                    metadata[k] = v[:config.METADATA_MAX_LENGTH]
                elif isinstance(v, list) and all(isinstance(i, str) for i in v):
                    text_parts.append(f"{k}: {', '.join(v)}")
                    metadata[k] = ", ".join(v)[:config.METADATA_MAX_LENGTH]

            if text_parts:
                content = f"[{path}] " + " | ".join(text_parts) if path else " | ".join(text_parts)
                documents.append(Document(page_content=content, metadata=metadata))

            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    new_path = f"{path}/{k}" if path else k
                    _process(v, new_path)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _process(item, f"{path}[{i}]")

    _process(taxonomy)
    return documents


def _index_has_data() -> bool:
    """Check if Pinecone index exists and already has vectors.

    Returns:
        True if the index has vectors in the configured namespace.
    """
    pc = Pinecone()
    if not pc.has_index(config.PINECONE_INDEX_NAME):
        return False
    index_config = pc.describe_index(config.PINECONE_INDEX_NAME)
    index = pc.Index(host=index_config.host)
    stats = index.describe_index_stats()
    ns_stats = stats.get("namespaces", {}).get(config.PINECONE_NAMESPACE, {})
    vector_count = ns_stats.get("vector_count", 0)
    if vector_count > 0:
        logger.info("Index '%s' already has %d vectors, skipping rebuild",
                    config.PINECONE_INDEX_NAME, vector_count)
        return True
    return False


def build_taxonomy_index() -> None:
    """Load failure taxonomy, chunk it, embed and upsert to Pinecone.

    Skips if index already has data (idempotent).
    """
    # Skip if already populated
    if _index_has_data():
        return

    taxonomy_path = config.FAILURE_TAXONOMY_FILE
    if not taxonomy_path.exists():
        logger.error("Taxonomy file not found: %s", taxonomy_path)
        return

    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    documents = _chunk_taxonomy(taxonomy)
    logger.info("Chunked taxonomy into %d documents", len(documents))

    if not documents:
        logger.warning("No documents to index")
        return

    # Create index if needed
    pc = Pinecone()
    if not pc.has_index(config.PINECONE_INDEX_NAME):
        logger.info("Creating Pinecone index: %s", config.PINECONE_INDEX_NAME)
        pc.create_index(
            name=config.PINECONE_INDEX_NAME,
            dimension=config.EMBEDDING_DIMENSION,
            metric=config.PINECONE_METRIC,
            spec=ServerlessSpec(cloud=config.PINECONE_CLOUD, region=config.PINECONE_REGION),
        )

    embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)

    PineconeVectorStore.from_documents(
        documents,
        embedding=embeddings,
        index_name=config.PINECONE_INDEX_NAME,
        namespace=config.PINECONE_NAMESPACE,
    )
    logger.info("Taxonomy indexed: %d docs in '%s/%s'",
                len(documents), config.PINECONE_INDEX_NAME, config.PINECONE_NAMESPACE)


def get_taxonomy_store() -> PineconeVectorStore:
    """Get existing PineconeVectorStore for searching.

    Returns:
        PineconeVectorStore connected to taxonomy index.
    """
    embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
    return PineconeVectorStore(
        index_name=config.PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=config.PINECONE_NAMESPACE,
    )


def search_taxonomy(query: str, top_k: int = config.VECTOR_SEARCH_TOP_K) -> list[Document]:
    """Semantic search over failure taxonomy with local caching.

    Args:
        query: Natural language search query.
        top_k: Number of results.

    Returns:
        List of matching Documents.
    """
    # Check cache first
    cache = _load_query_cache()
    key = _cache_key(query, top_k)
    if key in cache:
        logger.info("Cache hit for query: %s", query[:50])
        return [
            Document(page_content=d["page_content"], metadata=d["metadata"])
            for d in cache[key]
        ]

    # Cache miss — query Pinecone
    store = get_taxonomy_store()
    results = store.similarity_search_with_score(query, k=top_k)
    for doc, score in results:
        logger.info("  [%.3f] %s", score, doc.page_content[:80])

    docs = [doc for doc, _ in results]

    # Save to cache
    cache[key] = [{"page_content": d.page_content, "metadata": d.metadata} for d in docs]
    _save_query_cache(cache)

    return docs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)
    from dotenv import load_dotenv
    load_dotenv()

    print("Building taxonomy index (skips if exists)...")
    build_taxonomy_index()

    print("\nTest search: 'connection pool exhaustion'")
    results = search_taxonomy("connection pool exhaustion")
    for doc in results:
        print(f"  {doc.page_content[:100]}")

    print("\nTest search: 'missing database index'")
    results = search_taxonomy("missing database index")
    for doc in results:
        print(f"  {doc.page_content[:100]}")
