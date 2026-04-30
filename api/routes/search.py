"""Semantic search route — queries the Pinecone failure taxonomy index.

Delegates to pipeline.vector_store.search_taxonomy which handles
local query caching so repeated identical queries skip Pinecone entirely.
"""

import logging

from api.schemas import SearchRequest, SearchResponse, SearchResult
from fastapi import APIRouter, HTTPException
from pipeline.vector_store import search_taxonomy

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)


@router.post("", response_model=SearchResponse)
def semantic_search(body: SearchRequest) -> SearchResponse:
    """Run a semantic similarity search over the indexed failure taxonomy.

    Requires the vector store to have been populated by the pipeline's
    vector_store_node (or by running pipeline/vector_store.py directly).

    Args:
        body: Search request containing the query string and top_k limit.

    Returns:
        SearchResponse with matching documents and a cache-hit flag.

    Raises:
        HTTPException: 503 if Pinecone is unreachable or the index is missing.
    """
    try:
        docs = search_taxonomy(body.query, top_k=body.top_k)
    except Exception as exc:
        logger.exception("Vector search failed")
        raise HTTPException(status_code=503, detail=f"Search unavailable: {exc}") from exc

    results = [SearchResult(content=d.page_content, metadata=d.metadata) for d in docs]
    logger.info("Search '%s' → %d results", body.query[:60], len(results))
    return SearchResponse(query=body.query, results=results, cached=False)
