import feedparser
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
}

ALLOWED_TAGS = {"p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "blockquote", "h2", "h3"}

def safe_get(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("HTTP error:", e, "for", url)
        return ""

def extract_article_html(page_html):
    soup = BeautifulSoup(page_html, "lxml")

    # prefer common article containers
    selectors = [
        "article",
        "div[itemprop='articleBody']",
        "div.story-content",
        "div.article-content",
        "div.content",
        "div.field-body",
        "div#content",
        "main"
    ]

    container = None
    for sel in selectors:
        container = soup.select_one(sel)
        if container:
            break

    # fallback to body if none found
    if not container:
        container = soup.body or soup

    # remove scripts/styles and heavy junk
    for tag in container.find_all(["script", "style", "noscript", "iframe", "form", "svg", "figure", "aside"]):
        tag.decompose()

    # unwrap tags we don't allow, keep allowed tags and inline formatting
    for tag in container.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()

    # collect cleaned paragraphs/lists preserving allowed tags
    parts = []
    for el in container.find_all(["p", "ul", "ol", "blockquote", "h2", "h3"]):
        text = el.get_text(" ", strip=True)
        if len(text) > 30:  # filter very short noise lines
            parts.append(str(el))

    # limit size to avoid posting very long articles (you can increase if needed)
    return "\n".join(parts[:20]).strip()

def pick_image_from_page(page_html):
    if not page_html:
        return ""
    soup = BeautifulSoup(page_html, "lxml")
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"]
    # fallback: first large <img> inside article
    imgs = soup.find_all("img")
    for img in imgs:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy")
        if not src:
            continue
        # skip tiny icons or trackers by rough heuristic
        if any(x in src.lower() for x in ("logo", "icon", "sprite")):
            continue
        return src
    return ""

def get_rss_items(feed_url, limit=10):
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return []

    results = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        summary = entry.get("summary", "") or entry.get("description", "")
        page_html = safe_get(link)
        content_html = extract_article_html(page_html)
        if not content_html:
            # use summary HTML if full article scraping failed (keeps inline tags)
            content_html = summary

        image = pick_image_from_page(page_html)
        results.append({
            "title": title,
            "link": link,
            "summary": summary,
            "image": image,
            "content_html": content_html
        })
    return results