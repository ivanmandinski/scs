import requests, time, re
from typing import List, Tuple
from bs4 import BeautifulSoup
from llama_index.core import Document

def _fetch_all(site_base: str, route: str, per_page: int = 50, max_pages: int = 200) -> list:
    items, page = [], 1
    while page <= max_pages:
        url = f"{site_base.rstrip('/')}{route}"
        resp = requests.get(url, params={"per_page": per_page, "page": page}, timeout=20)
        if resp.status_code == 400 and "rest_post_invalid_page_number" in resp.text:
            break
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        items.extend(batch); page += 1; time.sleep(0.2)
    return items

def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for t in soup(["script", "style", "noscript"]): t.decompose()
    # remove excessive whitespace
    txt = soup.get_text(separator=" ", strip=True)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def fetch_wp_documents(site_base: str, include_pages: bool = True) -> List[Document]:
    posts = _fetch_all(site_base, "/wp-json/wp/v2/posts")
    pages = _fetch_all(site_base, "/wp-json/wp/v2/pages") if include_pages else []
    docs: List[Document] = []
    for item in posts + pages:
        content = _clean_html(item.get("content", {}).get("rendered", "") or "")
        title = _clean_html(item.get("title", {}).get("rendered", "") or "")
        url   = item.get("link") or ""
        text  = f"{title}\n\n{content}".strip()
        meta  = {
            "wp_id": item.get("id"),
            "wp_type": item.get("type"),
            "title": title,
            "url": url,
            "site": site_base,
            "date": item.get("date"),
            "modified": item.get("modified"),
        }
        if text:
            docs.append(Document(text=text, metadata=meta))
    return docs

# Fallback: sitemap ingestion (if REST is blocked/limited)
def fetch_sitemap_documents(site_base: str, sitemap_path: str = "/sitemap.xml", limit: int = 200) -> List[Document]:
    import xml.etree.ElementTree as ET
    import urllib.parse as up

    url = f"{site_base.rstrip('/')}{sitemap_path}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall(".//sm:url/sm:loc", ns)]
    docs: List[Document] = []
    for i, page_url in enumerate(urls[:limit]):
        try:
            r = requests.get(page_url, timeout=20)
            if r.status_code != 200: 
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for t in soup(["script", "style", "noscript"]): t.decompose()
            title = (soup.title.string or "").strip() if soup.title else ""
            content = _clean_html(str(soup))
            text = f"{title}\n\n{content}".strip()
            docs.append(Document(text=text, metadata={"url": page_url, "title": title, "site": site_base}))
            time.sleep(0.2)
        except Exception:
            continue
    return docs
