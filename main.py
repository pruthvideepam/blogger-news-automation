from config import BLOG_ID, RSS_FEEDS, DEFAULT_LABELS, POST_AS_DRAFT
from fetch_news import get_rss_items
from post_to_blogger import create_blogger_service, create_post
from utils import already_posted, save_posted_link
import time

SERVICE = None
MAX_POSTS_PER_RUN = 1


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

    items = get_rss_items(feed_url, limit=5)

    if not items:
        print("  no items")
        return False

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

            print("  Post created:", item["title"])
            print("  Labels:", final_labels)
            print("  URL:", result.get("url"))

            time.sleep(10)
            return True

        except Exception as e:
            print("  Error creating post:", e)
            time.sleep(20)

    return False


def main():
    posts_created = 0

    for feed in RSS_FEEDS:
        if posts_created >= MAX_POSTS_PER_RUN:
            break

        success = process_feed(feed)

        if success:
            posts_created += 1

    print(f"Finished. Total posts created this run: {posts_created}")


if __name__ == "__main__":
    main()