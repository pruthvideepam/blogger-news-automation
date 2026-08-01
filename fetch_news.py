import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://kannada.news18.com/",
    "Connection": "keep-alive",
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
    if not page_html:
        return ""

    soup = BeautifulSoup(page_html, "lxml")

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

    if not container:
        container = soup.body or soup

    for tag in container.find_all(["script", "style", "noscript", "iframe", "form", "svg", "figure", "aside"]):
        tag.decompose()

    for tag in container.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()

    parts = []
    for el in container.find_all(["p", "ul", "ol", "blockquote", "h2", "h3"]):
        text = el.get_text(" ", strip=True)
        if len(text) > 30:
            parts.append(str(el))

    return "\n".join(parts[:20]).strip()


def pick_image_from_summary_html(summary_html, base_url=""):
    if not summary_html:
        return ""

    soup = BeautifulSoup(summary_html, "lxml")
    img = soup.find("img")
    if img:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy")
        if src:
            return urljoin(base_url, src)
    return ""


def pick_image_from_entry(entry):
    media = entry.get("media_content", [])
    for m in media:
        url = m.get("url", "").strip()
        medium = m.get("medium", "").strip().lower()
        if url and (medium in ("", "image") or any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])):
            return url

    enclosures = entry.get("enclosures", [])
    for enc in enclosures:
        url = enc.get("url", "").strip()
        enc_type = enc.get("type", "").lower()
        if url and ("image" in enc_type or any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])):
            return url

    summary = entry.get("summary", "") or entry.get("description", "")
    img = pick_image_from_summary_html(summary, entry.get("link", ""))
    if img:
        return img

    return ""


def pick_image_from_page(page_html, page_url=""):
    if not page_html:
        return ""

    soup = BeautifulSoup(page_html, "lxml")

    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return urljoin(page_url, og["content"])

    twitter = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter and twitter.get("content"):
        return urljoin(page_url, twitter["content"])

    imgs = soup.find_all("img")
    for img in imgs:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy")
        if not src:
            continue
        src_low = src.lower()
        if any(x in src_low for x in ("logo", "icon", "sprite", "avatar", "tracker")):
            continue
        return urljoin(page_url, src)

    return ""


def get_rss_items(feed_url, limit=10):
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return []

    results = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()

        summary = (
            entry.get("summary", "").strip()
            or entry.get("description", "").strip()
            or (
                entry.get("content", [{}])[0].get("value", "").strip()
                if entry.get("content") else ""
            )
        )

        image = pick_image_from_entry(entry)

        page_html = safe_get(link) if link else ""
        content_html = extract_article_html(page_html)

        if not content_html:
            content_html = summary

        if not image:
            image = pick_image_from_page(page_html, link)

        results.append({
            "title": title,
            "link": link,
            "summary": summary,
            "image": image,
            "content_html": content_html
        })

    return results