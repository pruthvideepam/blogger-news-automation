def already_posted(link):
    try:
        with open("posted_links.txt", "r", encoding="utf-8") as f:
            links = f.read().splitlines()
        return link in links
    except FileNotFoundError:
        return False


def save_posted_link(link):
    with open("posted_links.txt", "a", encoding="utf-8") as f:
        f.write(link + "\n")