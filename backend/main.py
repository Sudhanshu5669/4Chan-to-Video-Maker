import os
import sys
import requests
import time
from scraper import interactive_post_selection, get_catalog_page_candidates, clean_text
from screenshot import capture_post
from tts import generate_tts
from video import make_video
from llm import curate_and_censor_thread, scout_best_thread

def get_raw_thread_data(board, thread_id):
    """Fetches the OP and the top 20 replies."""
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    resp = requests.get(url, headers={"User-Agent": "MyBot/1.0"}).json()
    posts = resp['posts']
    
    op_text = clean_text(posts[0].get('com', ''))
    
    replies_data = []
    for p in posts[1:21]:
        text = clean_text(p.get('com', ''))
        if text and len(text) > 15: 
            replies_data.append({"id": p['no'], "text": text})
            
    return op_text, replies_data

def run_automation():
    for folder in ["temp", "assets", "output"]:
        os.makedirs(folder, exist_ok=True)
    
    BG_VIDEO = "assets/background.mp4"
    if not os.path.exists(BG_VIDEO):
        print(f"ERROR: You must place a background video at {BG_VIDEO} before running!")
        return

    print("""
    ======================================
    🤖 AUTONOMOUS 4CHAN VIDEO PRODUCER 🤖
    ======================================
    """)
    
    # 1. Ask for Board
    target_board = input("Enter the board letter you want to scrape (e.g., v, g, b, pol, r9k): ").strip().strip('/')
    
    # 2. Ask for Mode
    print("\nSelect Mode:")
    print("[1] Manual (You browse the catalog and pick the thread)")
    print("[2] Auto (The AI browses the catalog, finds the best thread, and makes the video)")
    mode_choice = input("Choice (1 or 2): ").strip()
    
    thread_id = None
    
    if mode_choice == "1":
        print("\n--- Starting MANUAL Mode ---")
        thread_id = interactive_post_selection(target_board)
        
    elif mode_choice == "2":
        print("\n--- Starting AUTO Mode ---")
        page = 0
        while not thread_id:
            print(f"\nTurning to Page {page + 1} of the Catalog...")
            candidates = get_catalog_page_candidates(target_board, page)
            
            if not candidates:
                print("The AI searched the entire board and found nothing good. Exiting.")
                return
                
            # Ask the LLM to pick
            best_id, reason = scout_best_thread(candidates)
            
            if best_id:
                print(f"🎯 LLM Scout found a match! Thread ID: {best_id}")
                print(f"Reason: {reason}")
                thread_id = best_id
            else:
                print(f"LLM Scout rejected Page {page + 1}. Reason: {reason}")
                page += 1
                time.sleep(1) # Be nice to the API
    else:
        print("Invalid choice. Exiting.")
        return

    try:
        # 3. Get raw data
        print(f"\nFetching full thread {thread_id} data...")
        op_text, replies_data = get_raw_thread_data(target_board, thread_id)
        
        # 4. LLM Curation (The Editor)
        llm_decision = curate_and_censor_thread(op_text, replies_data)
        
        if not llm_decision:
            print("The LLM Editor failed to process the thread.")
            return 
            
        final_playlist = [{"id": thread_id, "text": llm_decision['op_censored']}]
        for rep in llm_decision.get('selected_replies', []):
            final_playlist.append({"id": rep['id'], "text": rep['censored_text']})
        
        print(f"\n[LLM Editor] Script ready. Generating {len(final_playlist)} scenes.")
        
        image_paths = []
        audio_paths = []
        
        # 5. Generate Media
        for index, post in enumerate(final_playlist):
            p_id = post["id"]
            censored_text = post["text"]
            
            img_path = f"temp/post_{p_id}.png"
            audio_path = f"temp/audio_{p_id}.mp3"
            
            print(f"Processing Post [{p_id}] ({index + 1}/{len(final_playlist)})")
            capture_post(target_board, thread_id, p_id, img_path, replacement_text=censored_text)
            generate_tts(censored_text, audio_path)
            
            image_paths.append(img_path)
            audio_paths.append(audio_path)

        # 6. VIDEO ASSEMBLY
        print("\nRendering final sequential video...")
        output_name = f"output/viral_video_{thread_id}.mp4"
        make_video(BG_VIDEO, image_paths, audio_paths, output_name)
        
        print(f"\nSUCCESS! Video ready: {output_name}")

    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    run_automation()