import requests
from bs4 import BeautifulSoup
import re
import sys

def clean_text(raw_html):
    if not raw_html: return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for quote_link in soup.find_all("a", class_="quotelink"):
        quote_link.decompose()
    clean_str = soup.get_text(". ", strip=True)
    clean_str = re.sub(r'\.\s*\.', '.', clean_str) 
    return clean_str

def truncate(text, length=100):
    if len(text) > length: return text[:length] + "..."
    return text if text else "[Image only]"

def interactive_post_selection(board):
    """Displays catalog, user selects a thread, returns the Thread ID."""
    url = f"https://a.4cdn.org/{board}/catalog.json"
    response = requests.get(url, headers={"User-Agent": "MyBot/1.0"}, timeout=10)
    response.raise_for_status()
    catalog = response.json()
    
    current_page = 0
    max_page = len(catalog) - 1
    selected_thread_id = None

    while not selected_thread_id:
        page_data = catalog[current_page]
        print(f"\n{'='*60}\n BOARD: /{board}/ | PAGE: {current_page + 1} of {max_page + 1}\n{'='*60}")
        
        for t in page_data.get('threads', []):
            print(f"[{t.get('no')}] ({t.get('replies', 0)} replies) | {truncate(clean_text(t.get('com', '')))}")
            
        choice = input("\n[n] Next | [p] Prev | [q] Quit | OR Enter [Thread ID]: ").strip().lower()
        
        if choice == 'n' and current_page < max_page: current_page += 1
        elif choice == 'p' and current_page > 0: current_page -= 1
        elif choice == 'q': sys.exit("Exited.")
        elif choice.isdigit(): selected_thread_id = int(choice)

    return selected_thread_id