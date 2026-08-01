import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.prajavani.net/",
    "Connection": "keep-alive",
}

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u",
    "ul", "ol", "li", "blockquote", "h2", "h3",
    "a"
}

DROP_TAGS = {
    "script", "style", "noscript", "iframe", "form",
    "svg", "figure", "figcaption", "button", "input"
}


def safe_get(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("HTTP error:", e, "for", url)
        return ""


def clean_html_keep_allowed(html, base_url=""):
    if not html:
        return ""

    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.name == "a":
            href = tag.get("href", "").strip()
            if href:
                tag["href"] = urljoin(base_url, href)
            attrs = dict(tag.attrs)
            for attr in list(attrs.keys()):
                if attr != "href":
                    del tag[attr]
            continue

        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
        else:
            attrs = dict(tag.attrs)
            for attr in list(attrs.keys()):
                del tag[attr]

    parts = []
    for el in soup.find_all(["p", "ul", "ol", "blockquote", "h2", "h3"]):
        text = el.get_text(" ", strip=True)
        if len(text) > 20:
            parts.append(str(el))

    cleaned = "\n".join(parts).strip()

    if not cleaned:
        cleaned = soup.get_text("\n", strip=True)

    return cleaned.strip()


def extract_article_html(page_html, page_url=""):
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

    return clean_html_keep_allowed(str(container), page_url)


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
        url = (m.get("url") or "").strip()
        medium = (m.get("medium") or "").strip().lower()
        if url and (medium in ("", "image") or any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])):
            return url

    thumbnails = entry.get("media_thumbnail", [])
    for t in thumbnails:
        url = (t.get("url") or "").strip()
        if url:
            return url

    enclosures = entry.get("enclosures", [])
    for enc in enclosures:
        url = (enc.get("url") or "").strip()
        enc_type = (enc.get("type") or "").lower()
        if url and ("image" in enc_type or any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])):
            return url

    summary = (
        entry.get("summary", "")
        or entry.get("description", "")
        or get_entry_content_raw(entry)
    )
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

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy")
        if not src:
            continue
        src_low = src.lower()
        if any(x in src_low for x in ("logo", "icon", "sprite", "avatar", "tracker")):
            continue
        return urljoin(page_url, src)

    return ""


def get_entry_content_raw(entry):
    contents = entry.get("content", [])
    if contents:
        parts = []
        for c in contents:
            value = (c.get("value") or "").strip()
            if value:
                parts.append(value)
        if parts:
            return "\n".join(parts).strip()

    summary = (entry.get("summary") or "").strip()
    if summary:
        return summary

    description = (entry.get("description") or "").strip()
    if description:
        return description

    return ""


def get_best_entry_html(entry):
    raw_html = get_entry_content_raw(entry)
    return clean_html_keep_allowed(raw_html, entry.get("link", ""))


def get_rss_items(feed_url, limit=10):
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return []

    results = []

    for entry in feed.entries[:limit]:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()

        summary = (
            (entry.get("summary") or "").strip()
            or (entry.get("description") or "").strip()
        )

        content_html = get_best_entry_html(entry)
        image = pick_image_from_entry(entry)

        page_html = ""
        if link and (not content_html or len(BeautifulSoup(content_html, "lxml").get_text(" ", strip=True)) < 300 or not image):
            page_html = safe_get(link)

        if page_html and (not content_html or len(BeautifulSoup(content_html, "lxml").get_text(" ", strip=True)) < 300):
            page_content = extract_article_html(page_html, link)
            if len(BeautifulSoup(page_content, "lxml").get_text(" ", strip=True)) > len(BeautifulSoup(content_html, "lxml").get_text(" ", strip=True)):
                content_html = page_content

        if not content_html:
            content_html = clean_html_keep_allowed(summary, link)

        if not image and page_html:
            image = pick_image_from_page(page_html, link)

        results.append({
            "title": title,
            "link": link,
            "summary": summary,
            "image": image,
            "content_html": content_html
        })

    return results