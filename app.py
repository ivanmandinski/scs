import os
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from qdrant_client import QdrantClient, AsyncQdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core import Document
from settings import Settings  # ensures LLM + Embeddings are configured
from ingest_wp import fetch_wp_documents, fetch_sitemap_documents

templates = Jinja2Templates(directory="templates")

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION = os.getenv("QDRANT_COLLECTION", "scs_wp_hybrid")
SPARSE_MODEL = os.getenv("SPARSE_MODEL", "Qdrant/bm25")
DEFAULT_SITE = os.getenv("DEFAULT_SITE_BASE", "https://www.scsengineers.com")
SEARCH_PAGE_TITLE = os.getenv("SEARCH_PAGE_TITLE", "SCS Engineers Search (Hybrid)")

app = FastAPI(title="SCS Engineers Hybrid Search (Qdrant + LlamaIndex)")

client  = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
aclient = AsyncQdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Create vector store with hybrid enabled
vector_store = QdrantVectorStore(
    collection_name=COLLECTION,
    client=client,
    aclient=aclient,
    enable_hybrid=True,
    fastembed_sparse_model=SPARSE_MODEL,
    batch_size=32,
)

storage = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_vector_store(vector_store)

@app.get("/", response_class=HTMLResponse)
def root(request: Request, q: Optional[str] = None, k: int = 10, sparse_k: int = 50, alpha: float = 0.5):
    # Simple demo UI
    results = []
    error = None
    if q:
        try:
            engine = index.as_query_engine(
                vector_store_query_mode="hybrid",
                similarity_top_k=k,
                sparse_top_k=sparse_k,
                alpha=alpha,
            )
            resp = engine.query(q)
            for sn in resp.source_nodes:
                meta = getattr(sn, "metadata", None) or getattr(getattr(sn, "node", None), "metadata", {}) or {}
                results.append({
                    "text": sn.get_text(),
                    "score": getattr(sn, "score", None),
                    "metadata": meta,
                })
        except Exception as e:
            error = str(e)
    return templates.TemplateResponse("search.html", {"request": request, "q": q or "", "results": results, "error": error, "title": SEARCH_PAGE_TITLE, "k": k, "sparse_k": sparse_k, "alpha": alpha})

@app.post("/reindex")
def reindex(site: Optional[str] = None, include_pages: bool = True, use_sitemap_fallback: bool = True):
    site_base = site or DEFAULT_SITE
    docs = fetch_wp_documents(site_base, include_pages=include_pages)
    if not docs and use_sitemap_fallback:
        docs = fetch_sitemap_documents(site_base)
    if not docs:
        raise HTTPException(status_code=404, detail="No content found from WP REST or sitemap.")
    local_index = VectorStoreIndex.from_documents(docs, storage_context=storage)
    return {"site": site_base, "count": len(docs)}

@app.get("/search")
def search(
    q: str = Query(..., min_length=1),
    site: Optional[str] = None,
    k: int = 10,
    sparse_k: int = 50,
    alpha: float = 0.5,
):
    engine = index.as_query_engine(
        vector_store_query_mode="hybrid",
        similarity_top_k=k,
        sparse_top_k=sparse_k,
        alpha=alpha,
    )
    resp = engine.query(q)
    out = []
    for sn in resp.source_nodes:
        meta = getattr(sn, "metadata", None) or getattr(getattr(sn, "node", None), "metadata", {}) or {}
        out.append({
            "text": sn.get_text(),
            "score": getattr(sn, "score", None),
            "metadata": meta,
        })
    return {"query": q, "results": out, "k": k, "sparse_k": sparse_k, "alpha": alpha}
