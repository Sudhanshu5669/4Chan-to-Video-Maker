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
    url = f"https://a.4cdn.org/{board}/catalog.json"
    response = requests.get(url, headers={"User-Agent": "MyBot/1.0"}, timeout=10)
    response.raise_for_status()
    catalog = response.json()
    
    current_page = 0
    max_page = len(catalog) - 1
    selected_thread_id = None

    # Step 1: Browse Catalog and pick a thread
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

    # Step 2: Fetch the full thread and pick replies
    print(f"\nFetching full thread {selected_thread_id}...")
    thread_url = f"https://a.4cdn.org/{board}/thread/{selected_thread_id}.json"
    thread_resp = requests.get(thread_url, headers={"User-Agent": "MyBot/1.0"}).json()
    posts = thread_resp['posts']

    print("\n--- THREAD LOADED (Top 15 Posts) ---")
    for p in posts[:15]:
        print(f"[{p['no']}] {truncate(clean_text(p.get('com', '')))}")

    print("\nWhich posts do you want in the video?")
    print("Enter comma-separated IDs (e.g., 12345, 12346).")
    print(f"Leave blank and press Enter to just use the OP ({selected_thread_id}).")
    
    selection = input("IDs: ").strip()
    
    # Parse the user's choice
    if not selection:
        selected_ids = [selected_thread_id]
    else:
        selected_ids = [int(x.strip()) for x in selection.split(',') if x.strip().isdigit()]

    # Gather data for all selected posts
    final_posts_data = []
    for p in posts:
        if p['no'] in selected_ids:
            final_posts_data.append({
                "thread_id": selected_thread_id,
                "post_id": p['no'],
                "text": clean_text(p.get('com', ''))
            })
            
    return final_posts_data