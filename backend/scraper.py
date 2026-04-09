import requests
from bs4 import BeautifulSoup
import re
import sys


def clean_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove reply links (>>123456)
    for tag in soup.find_all("a", class_="quotelink"):
        tag.decompose()

    text = soup.get_text(". ", strip=True)

    # Strip URLs
    text = re.sub(r"https?://\S+", "", text)
    # Collapse double-periods left by URL removal
    text = re.sub(r"\.\s*\.", ".", text)
    # Collapse excessive whitespace
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def truncate(text: str, length: int = 100) -> str:
    if not text:
        return "[Image only]"
    return text[:length] + "…" if len(text) > length else text


def get_all_boards() -> list[dict]:
    """Returns list of {board, title} dicts for all active boards."""
    url = "https://a.4cdn.org/boards.json"
    r = requests.get(url, headers={"User-Agent": "4chanBot/2.0"}, timeout=10)
    r.raise_for_status()
    return r.json()["boards"]


def get_catalog_page_candidates(board: str, page_index: int) -> list[dict] | None:
    """
    Returns the top 10 most-replied text threads on catalog page `page_index`.
    Returns None when there are no more pages.
    """
    url = f"https://a.4cdn.org/{board}/catalog.json"
    r = requests.get(url, headers={"User-Agent": "4chanBot/2.0"}, timeout=10)
    r.raise_for_status()
    catalog = r.json()

    if page_index >= len(catalog):
        return None

    threads = catalog[page_index].get("threads", [])
    # Sort by reply count descending – more replies = more engagement
    threads = sorted(threads, key=lambda t: t.get("replies", 0), reverse=True)

    candidates = []
    for t in threads:
        text = clean_text(t.get("com", ""))
        # Skip image-only posts and very short stubs
        if len(text) < 30:
            continue
        candidates.append({
            "id":      t["no"],
            "replies": t.get("replies", 0),
            "text":    truncate(text, 280),
        })
        if len(candidates) == 10:
            break

    return candidates or None


def interactive_post_selection(board: str) -> int:
    """Manual mode: browse catalog pages and pick a thread ID."""
    url = f"https://a.4cdn.org/{board}/catalog.json"
    r = requests.get(url, headers={"User-Agent": "4chanBot/2.0"}, timeout=10)
    r.raise_for_status()
    catalog = r.json()

    page     = 0
    max_page = len(catalog) - 1
    selected = None

    while selected is None:
        print(f"\n{'═'*60}")
        print(f"  /{board}/  │  Page {page + 1} of {max_page + 1}")
        print(f"{'═'*60}")
        for t in catalog[page].get("threads", []):
            preview = truncate(clean_text(t.get("com", "")))
            print(f"  [{t['no']}] ({t.get('replies', 0)} replies)  {preview}")
        print()
        choice = input("  [n] Next  [p] Prev  [q] Quit  or Thread ID: ").strip().lower()

        if   choice == "n" and page < max_page: page += 1
        elif choice == "p" and page > 0:        page -= 1
        elif choice == "q":                     sys.exit("Exited.")
        elif choice.isdigit():                  selected = int(choice)

    return selected