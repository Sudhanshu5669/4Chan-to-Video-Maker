import os
import sys
import requests
import time
from scraper import interactive_post_selection, get_catalog_page_candidates, clean_text, get_all_boards
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
    
    # --- 1. INTERACTIVE BOARD SELECTOR ---
    print("Fetching live board list from 4chan...")
    try:
        boards = get_all_boards()
        print("\n--- AVAILABLE BOARDS ---")
        
        col_width = 30
        for i in range(0, len(boards), 3):
            row = boards[i:i+3]
            formatted_row = ""
            for b in row:
                entry = f"/{b['board']}/ - {b['title']}"
                if len(entry) > col_width - 2:
                    entry = entry[:col_width - 4] + "..."
                formatted_row += f"{entry:<{col_width}}"
            print(formatted_row)
            
        valid_boards = [b['board'] for b in boards]
        target_board = ""
        while target_board not in valid_boards:
            target_board = input("\nEnter the board abbreviation you want (e.g., v, g, pol): ").strip().strip('/')
            if target_board not in valid_boards:
                print(f"Error: '{target_board}' is not a valid board. Try again.")
                
    except Exception as e:
        print(f"Failed to fetch boards: {e}")
        target_board = input("Enter the board letter manually: ").strip().strip('/')

    # --- 2. Ask for Mode ---
    print(f"\n[ Selected Board: /{target_board}/ ]")
    print("\nSelect Mode:")
    print("[1] Manual (You browse the catalog and pick the thread)")
    print("[2] Full Auto (The AI browses, finds the best thread, and makes the video)")
    print("[3] Review Mode (The AI scouts threads, but asks YOUR permission before rendering)")
    mode_choice = input("Choice (1, 2, or 3): ").strip()
    
    thread_id = None
    
    if mode_choice == "1":
        print("\n--- Starting MANUAL Mode ---")
        thread_id = interactive_post_selection(target_board)
        
    elif mode_choice in ["2", "3"]:
        mode_name = "AUTO" if mode_choice == "2" else "REVIEW"
        print(f"\n--- Starting {mode_name} Mode ---")
        page = 0
        
        while not thread_id:
            print(f"\nTurning to Page {page + 1} of the Catalog...")
            candidates = get_catalog_page_candidates(target_board, page)
            
            if not candidates:
                print("The AI searched the entire board and found nothing good. Exiting.")
                return
                
            while candidates and not thread_id:
                scout_result = scout_best_thread(candidates)
                if len(scout_result) == 3:
                    best_id, reason, preview = scout_result
                else:
                    best_id, reason = scout_result[0], scout_result[1]
                    preview = "No preview available."

                if best_id:
                    if mode_choice == "3":
                        print(f"\n--- 🎯 AI SUGGESTION (Thread {best_id}) ---")
                        print(f"REASON: {reason}")
                        print(f"PREVIEW: {preview}")
                        choice = input("\nDo you want to make a video of this? (y/n): ").strip().lower()
                        
                        if choice == 'y':
                            thread_id = best_id
                        else:
                            print("Rejected by user. Asking AI to find another on this page...")
                            candidates = [c for c in candidates if c['id'] != best_id]
                    else:
                        print(f"🎯 LLM Scout found a match! Thread ID: {best_id}")
                        print(f"Reason: {reason}")
                        thread_id = best_id
                else:
                    print(f"LLM Scout rejected the rest of Page {page + 1}. Reason: {reason}")
                    break 
            
            if not thread_id:
                page += 1
                time.sleep(1) 
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
            
        # --- 5. NEW: REPLY REVIEW SYSTEM ---
        final_playlist = [{"id": thread_id, "text": llm_decision['op_censored']}]
        
        # If they are in Mode 3, ask them how they want to handle the replies
        reply_mode = "1"
        if mode_choice == "3":
            print("\n--- SCRIPT GENERATED ---")
            print("How do you want to handle the replies the AI selected?")
            print("[1] Auto (Render all of them into the video)")
            print("[2] Review (Approve/Reject each reply individually)")
            reply_mode = input("Choice (1 or 2): ").strip()
            
        if reply_mode == "2":
            print("\n--- SCRIPT REVIEW ---")
            print(f"OP [Included Automatically]: {llm_decision['op_censored']}\n")
            
            for rep in llm_decision.get('selected_replies', []):
                print(f"-> REPLY {rep['id']}: {rep['censored_text']}")
                keep = input("Include this reply? (y/n): ").strip().lower()
                if keep == 'y':
                    final_playlist.append({"id": rep['id'], "text": rep['censored_text']})
                else:
                    print("   [Discarded]")
        else:
            # Auto mode: Just dump them all in
            for rep in llm_decision.get('selected_replies', []):
                final_playlist.append({"id": rep['id'], "text": rep['censored_text']})
        
        print(f"\n[Final Cut] Script ready. Generating {len(final_playlist)} scenes.")
        
        image_paths = []
        audio_paths = []
        
        # 6. Generate Media
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

        # 7. VIDEO ASSEMBLY
        print("\nRendering final sequential video...")
        output_name = f"output/viral_video_{thread_id}.mp4"
        make_video(BG_VIDEO, image_paths, audio_paths, output_name)
        
        print(f"\nSUCCESS! Video ready: {output_name}")

    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    run_automation()