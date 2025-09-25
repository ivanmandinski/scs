# SCS Engineers — Hybrid Search (Qdrant + LlamaIndex), Railway-hosted

A standalone API + minimal UI that ingests **scsengineers.com** (via WordPress REST API or sitemap) and serves **hybrid search** (dense + sparse) using **Qdrant**. 
No code or plugin needs to run on SCS servers — everything is on Railway.

## Endpoints

- `POST /reindex?site=https://www.scsengineers.com` — fetch & (re)index posts/pages.
- `GET /search?q=QUERY&k=10&sparse_k=50&alpha=0.5` — JSON results.
- `GET /` — demo HTML search page (for stakeholders).

## One-time setup

1. **Create Qdrant** (Cloud or self-host). Note URL, API key.
2. **Deploy this repo to Railway** (GitHub → Railway). Add Variables:

   ```
   QDRANT_URL=...
   QDRANT_API_KEY=...
   QDRANT_COLLECTION=scs_wp_hybrid
   CEREBRAS_API_KEY=...
   CEREBRAS_MODEL=llama-3.3-70b
   EMBED_MODEL=BAAI/bge-small-en-v1.5
   SPARSE_MODEL=Qdrant/bm25
   CHUNK_SIZE=512
   DEFAULT_SITE_BASE=https://www.scsengineers.com
   SEARCH_PAGE_TITLE=SCS Engineers Search (Hybrid)
   ```

3. **Open the Railway service URL**, then call:

   ```bash
   curl -X POST "$RAILWAY_URL/reindex?site=https://www.scsengineers.com"
   ```

4. Visit `GET /` to try searches interactively.

## Notes

- Hybrid knobs exposed: `k` (similarity_top_k), `sparse_k` (sparse_top_k), `alpha` (fusion).
- If the WP REST API is limited, ingestion falls back to `sitemap.xml` scraping.
- Multi-tenant ready: index multiple sites; filter by `site` at query time.
- This repo does **not** modify the SCS website. When ready, we can add a small WP plugin or embed to swap results.

## Dev

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

## Smoke test

- `POST /reindex?site=https://www.scsengineers.com`
- `GET /search?q=landfill gas`
- `GET /` and try a few queries; tweak `alpha`, `sparse_k`, `k`.
