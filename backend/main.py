import os
import sys
from scraper import interactive_post_selection
from screenshot import capture_post
from tts import generate_tts
from video import make_video

def run_automation(target_board="greentext"):
    # Ensure directories exist
    for folder in ["temp", "assets", "output"]:
        os.makedirs(folder, exist_ok=True)
    
    BG_VIDEO = "assets/background.mp4"
    if not os.path.exists(BG_VIDEO):
        print(f"Error: Please place a video file at {BG_VIDEO}")
        return

    try:
        print(f"--- Starting Automation for /{target_board}/ ---")
        
        # 1. FIND CONTENT
        post_data = interactive_post_selection(target_board)
        t_id, p_id = post_data["thread_id"], post_data["post_id"]
        text = post_data["text"]
        
        # Define paths
        img_path = f"temp/post_{p_id}.png"
        audio_path = f"temp/audio_{p_id}.mp3"
        output_path = f"output/auto_video_{p_id}.mp4"

        # 2. SCREENSHOT
        print(f"[1/3] Capturing post #{p_id}...")
        capture_post(target_board, t_id, p_id, img_path)
        
        # 3. TTS
        print("[2/3] Generating voiceover...")
        generate_tts(text, audio_path)
        
        # 4. VIDEO ASSEMBLY
        print("[3/3] Rendering video...")
        make_video(BG_VIDEO, img_path, audio_path, output_path)
        
        print(f"\nSUCCESS! Video ready: {output_path}")

    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    # You can pass the board as a command line argument
    # Usage: python main.py v
    board = sys.argv[1] if len(sys.argv) > 1 else "greentext"
    run_automation(board)