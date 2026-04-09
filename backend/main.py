import os
import sys
import requests
from scraper import interactive_post_selection, clean_text
from screenshot import capture_post
from tts import generate_tts
from video import make_video
from llm import curate_and_censor_thread

def get_raw_thread_data(board, thread_id):
    """Fetches the raw thread data so we can feed it to the LLM."""
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    resp = requests.get(url, headers={"User-Agent": "MyBot/1.0"}).json()
    posts = resp['posts']
    
    op_text = clean_text(posts[0].get('com', ''))
    
    # Grab the top 15 replies to give the LLM some options
    replies_data = []
    for p in posts[1:16]:
        text = clean_text(p.get('com', ''))
        if text and len(text) > 10: # Ignore super short posts
            replies_data.append({"id": p['no'], "text": text})
            
    return op_text, replies_data

def run_automation(target_board="g"):
    for folder in ["temp", "assets", "output"]:
        os.makedirs(folder, exist_ok=True)
    
    BG_VIDEO = "assets/background.mp4"

    try:
        # 1. Pick a thread from the catalog (Interactive)
        # We modify interactive_post_selection to just return the Thread ID you want
        print("Select a thread to process...")
        posts_data = interactive_post_selection(target_board) 
        thread_id = posts_data[0]['thread_id'] # Assume the user just picked the OP
        
        # 2. Get raw data
        op_text, replies_data = get_raw_thread_data(target_board, thread_id)
        
        # 3. LLM Curation
        llm_decision = curate_and_censor_thread(op_text, replies_data, model="blaifa/InternVL3_5:8b")
        
        if not llm_decision:
            return # Exit if LLM failed
            
        # Assemble the final playlist based on LLM output
        final_playlist = [
            {"id": thread_id, "text": llm_decision['op_censored']}
        ]
        for rep in llm_decision['selected_replies']:
            final_playlist.append({"id": rep['id'], "text": rep['censored_text']})
        
        image_paths = []
        audio_paths = []
        
        # 4. Generate Media
        for index, post in enumerate(final_playlist):
            p_id = post["id"]
            censored_text = post["text"]
            
            img_path = f"temp/post_{p_id}.png"
            audio_path = f"temp/audio_{p_id}.mp3"
            
            print(f"\nProcessing Post [{p_id}] ({index + 1}/{len(final_playlist)})")
            
            # Pass the censored text to the screenshotter so it updates the web page visually!
            capture_post(target_board, thread_id, p_id, img_path, replacement_text=censored_text)
            generate_tts(censored_text, audio_path)
            
            image_paths.append(img_path)
            audio_paths.append(audio_path)

        # 5. VIDEO ASSEMBLY
        print("\nRendering final sequential video...")
        output_name = f"output/curated_thread_{thread_id}.mp4"
        make_video(BG_VIDEO, image_paths, audio_paths, output_name)
        
        print(f"\nSUCCESS! Video ready: {output_name}")

    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    board = sys.argv[1] if len(sys.argv) > 1 else "g"
    run_automation(board)