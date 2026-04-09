import requests
from bs4 import BeautifulSoup
import re
import sys

def clean_text(raw_html):
    if not raw_html:
        return ""
        
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # 1. Remove reply links (>>12345678) so the TTS doesn't read numbers out loud
    for quote_link in soup.find_all("a", class_="quotelink"):
        quote_link.decompose()
        
    # 2. Extract text, using a period/space to replace <br> tags 
    clean_str = soup.get_text(". ", strip=True)
    
    # Clean up multiple spaces/periods if the user spammed line breaks
    clean_str = re.sub(r'\.\s*\.', '.', clean_str) 
    
    return clean_str

def get_post_data(board, thread_id, post_id):
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    
    response = requests.get(
        url,
        headers={"User-Agent": "My4chanVideoMaker/1.0"},
        timeout=10
    )
    response.raise_for_status()
    
    data = response.json()
    posts = data.get("posts", [])

    if not posts:
        raise ValueError("No posts found in thread.")
    
    target_post = next((p for p in posts if p['no'] == post_id), None)

    if not target_post:
        raise ValueError("Post not found in this thread.")
    
    return {
        "id": target_post['no'],
        "text": clean_text(target_post.get('com', '')),
        "author": target_post.get("name"),
        "time": target_post.get("time"),
        "has_image": "filename" in target_post
    }

def truncate(text, length=120):
    """Helper function to shorten text for console preview."""
    if len(text) > length:
        return text[:length] + "..."
    return text if text else "[No text / Image only]"

def interactive_post_selection(board):
    """Displays pages of threads interactively for the user to select."""
    url = f"https://a.4cdn.org/{board}/catalog.json"
    response = requests.get(url, headers={"User-Agent": "My4chanVideoMaker/1.0"}, timeout=10)
    response.raise_for_status()
    
    catalog = response.json()
    current_page = 0
    max_page = len(catalog) - 1

    while True:
        page_data = catalog[current_page]
        threads = page_data.get('threads', [])
        
        print(f"\n{'='*60}")
        print(f" BOARD: /{board}/ | PAGE: {current_page + 1} of {max_page + 1}")
        print(f"{'='*60}")
        
        for t in threads:
            t_id = t.get('no')
            replies_count = t.get('replies', 0)
            op_text = clean_text(t.get('com', ''))
            
            print(f"\n[{t_id}] ({replies_count} replies)")
            print(f"OP: {truncate(op_text)}")
            
            # Show a couple of the last replies if available in the catalog
            last_replies = t.get('last_replies', [])
            if last_replies:
                # Limit to previewing just 2 replies to keep the console clean
                for i, rep in enumerate(last_replies[:2]):
                    rep_text = clean_text(rep.get('com', ''))
                    if rep_text:
                        print(f"  -> Reply {i+1}: {truncate(rep_text, 80)}")
        
        print(f"\n{'-'*60}")
        print("Options: [n] Next Page | [p] Prev Page | [q] Quit")
        print("Or enter a [Thread ID] to generate a video for it.")
        
        choice = input("Choice: ").strip().lower()
        
        if choice == 'n':
            if current_page < max_page:
                current_page += 1
            else:
                print("\n*** You are already on the last page. ***")
        elif choice == 'p':
            if current_page > 0:
                current_page -= 1
            else:
                print("\n*** You are already on the first page. ***")
        elif choice == 'q':
            sys.exit("Script exited by user.")
        elif choice.isdigit():
            selected_id = int(choice)
            
            # Search the entire catalog for the selected ID
            selected_thread = None
            for p in catalog:
                for t in p['threads']:
                    if t['no'] == selected_id:
                        selected_thread = t
                        break
                if selected_thread:
                    break
            
            if selected_thread:
                print(f"\nSelected Thread: {selected_id}")
                return {
                    "thread_id": selected_thread['no'],
                    "post_id": selected_thread['no'], 
                    "text": clean_text(selected_thread.get('com', ''))
                }
            else:
                print(f"\n*** Thread ID {selected_id} not found. Please try again. ***")
        else:
            print("\n*** Invalid input. Please enter 'n', 'p', 'q', or a Thread ID. ***")