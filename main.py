from config import BLOG_ID, RSS_FEEDS, DEFAULT_LABELS, POST_AS_DRAFT
from fetch_news import get_rss_items
from post_to_blogger import create_blogger_service, create_post
from utils import already_posted, save_posted_link
import time

SERVICE = None


def ensure_service():
    global SERVICE
    if SERVICE is None:
        SERVICE = create_blogger_service()
    return SERVICE


def make_post_html(item):
    title = item["title"]
    image_html = ""

    if item.get("image"):
        image_html = f'<p><img src="{item["image"]}" alt="{title}" style="max-width:100%;height:auto;" /></p>'

    body = item.get("content_html") or item.get("summary") or ""

    if not body:
        body = "<p>Summary unavailable.</p>"

    return f"{image_html}<h2>{title}</h2>{body}"


def process_feed(feed):
    feed_name = feed["name"]
    feed_url = feed["url"]
    feed_labels = feed.get("labels", [])

    print(f"Checking feed: {feed_name} -> {feed_url}")

    items = get_rss_items(feed_url, limit=8)

    if not items:
        print("  no items")
        return

    service = ensure_service()

    for item in items:
        if already_posted(item["link"]):
            continue

        content = make_post_html(item)

        final_labels = feed_labels + DEFAULT_LABELS

        try:
            result = create_post(
                service=service,
                blog_id=BLOG_ID,
                title=item["title"],
                content=content,
                labels=final_labels,
                is_draft=POST_AS_DRAFT
            )

            save_posted_link(item["link"])

            print("  Draft created:", item["title"])
            print("  Labels:", final_labels)

            time.sleep(1)
            break

        except Exception as e:
            print("  Error creating post:", e)


def main():
    for feed in RSS_FEEDS:
        process_feed(feed)


if __name__ == "__main__":
    main()