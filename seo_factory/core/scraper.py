import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SEOFactory/1.0)"
}

def scrape_page(url: str) -> dict:
    """Scrape a single page and return clean text + metadata."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
            tag.decompose()

        title = soup.find("title")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        h1 = soup.find("h1")
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]

        paragraphs = []
        for p in soup.find_all(["p", "li"]):
            text = p.get_text(strip=True)
            if len(text) > 40:
                paragraphs.append(text)

        body_text = " ".join(paragraphs[:30])

        return {
            "url": url,
            "title": title.get_text(strip=True) if title else "",
            "meta_description": meta_desc.get("content", "") if meta_desc else "",
            "h1": h1.get_text(strip=True) if h1 else "",
            "h2s": h2s[:6],
            "body_text": body_text[:2000],
            "success": True,
            "error": None
        }
    except Exception as e:
        return {
            "url": url,
            "title": "", "meta_description": "", "h1": "",
            "h2s": [], "body_text": "",
            "success": False,
            "error": str(e)
        }


def scrape_multiple(urls: list) -> dict:
    """Scrape multiple URLs with a small delay between requests."""
    results = {}
    for url in urls:
        if url.strip():
            results[url] = scrape_page(url.strip())
            time.sleep(0.5)
    return results
