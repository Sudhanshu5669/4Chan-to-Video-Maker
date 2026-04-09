import requests
from bs4 import BeautifulSoup
import re
import sys

def clean_text(raw_html):
    if not raw_html: return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Remove standard 4chan reply links (>>123456)
    for quote_link in soup.find_all("a", class_="quotelink"):
        quote_link.decompose()
        
    clean_str = soup.get_text(". ", strip=True)
    
    # --- NEW: DESTROY URLs ---
    # This regex finds anything starting with http/https and removes it
    clean_str = re.sub(r'http[s]?://\S+', '', clean_str)
    
    # Clean up double periods or weird spacing left behind
    clean_str = re.sub(r'\.\s*\.', '.', clean_str) 
    
    return clean_str.strip()

def truncate(text, length=100):
    if len(text) > length: return text[:length] + "..."
    return text if text else "[Image only]"

def get_catalog_page_candidates(board, page_index):
    """Fetches a specific page of the catalog and returns the top 10 most replied threads."""
    url = f"https://a.4cdn.org/{board}/catalog.json"
    response = requests.get(url, headers={"User-Agent": "MyBot/1.0"}, timeout=10)
    response.raise_for_status()
    catalog = response.json()
    
    if page_index >= len(catalog):
        return None # No more pages
        
    threads = catalog[page_index].get('threads', [])
    # Sort by replies to give the LLM the most active threads
    active_threads = sorted(threads, key=lambda x: x.get('replies', 0), reverse=True)
    
    candidates = []
    # Only take the top 10 to avoid overwhelming the LLM's context limit
    for t in active_threads[:10]:
        text = clean_text(t.get('com', ''))
        if len(text) > 20: # Ignore pure image posts
            candidates.append({
                "id": t['no'],
                "replies": t.get('replies', 0),
                "text": truncate(text, 250) # Truncate to save LLM memory
            })
            
    return candidates

def interactive_post_selection(board):
    """Your existing manual mode selector."""
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


def get_all_boards():
    """Fetches the live list of all active 4chan boards."""
    url = "https://a.4cdn.org/boards.json"
    response = requests.get(url, headers={"User-Agent": "MyBot/1.0"}, timeout=10)
    response.raise_for_status()
    return response.json()['boards']