import os

POSTED_FILE = "posted_links.txt"


def already_posted(link):
    if not os.path.exists(POSTED_FILE):
        return False

    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        links = {line.strip() for line in f if line.strip()}

    return link in links


def save_posted_link(link):
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")