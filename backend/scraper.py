import requests
from bs4 import BeautifulSoup
import re
import random

def clean_text(raw_html):
    if not raw_html:
        return ""
        
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # 1. Remove reply links (>>12345678) so the TTS doesn't read numbers out loud
    for quote_link in soup.find_all("a", class_="quotelink"):
        quote_link.decompose()
        
    # 2. Extract text, using a period/space to replace <br> tags 
    # This forces the TTS voice to pause at line breaks.
    clean_str = soup.get_text(". ", strip=True)
    
    # Optional: Clean up multiple spaces/periods if the user spammed line breaks
    import re
    clean_str = re.sub(r'\.\s*\.', '.', clean_str) 
    
    return clean_str

def get_post_data(board, thread_id, post_id):
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
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



def get_trending_thread(board):
    """Finds the thread with the most replies on the board catalog."""
    url = f"https://a.4cdn.org/{board}/catalog.json"
    response = requests.get(url, headers={"User-Agent": "MyBot/1.0"}, timeout=10)
    response.raise_for_status()
    
    catalog = response.json()
    all_threads = []
    
    # Flatten the catalog pages into one list
    for page in catalog:
        all_threads.extend(page['threads'])
        
    # Sort by number of replies (descending)
    trending = sorted(all_threads, key=lambda x: x.get('replies', 0), reverse=True)
    
    # Filter: must have text and shouldn't be too short
    # We ignore threads without a 'com' (comment) field
    valid_threads = [t for t in trending if 'com' in t and len(clean_text(t['com'])) > 100]
    
    if not valid_threads:
        raise ValueError("No suitable threads found.")
        
    # Return the top one (or a random one from the top 5 to keep content fresh)
    return random.choice(valid_threads[:5])

def get_automated_post(board):
    """Automatically finds a trending thread and returns the OP data."""
    thread = get_trending_thread(board)
    print(f"Found trending thread: {thread['no']} with {thread['replies']} replies.")
    
    return {
        "thread_id": thread['no'],
        "post_id": thread['no'], # Usually we want the OP (Original Poster)
        "text": clean_text(thread['com'])
    }