import threading
import queue
import time
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from server import RenderRequest, get_random_background
from screenshot import capture_posts_batch
from tts import generate_tts
from video import make_video
from Uploader import upload_to_youtube
import json
from scraper import get_all_boards, get_catalog_page_candidates
from llm import scout_best_thread, curate_and_censor_thread
from server import get_all_thread_data
from config import load_config

# ── Batch Queue System ────────────────────────────────────────────────────────
BATCH_QUEUE = queue.Queue()
JOB_STATUS = {}  # Stores job details and progress logs
JOB_HISTORY = [] # Keeps track of finished/failed jobs

def add_batch_job(config: dict):
    job_id = f"job_{int(time.time())}_{config.get('board', 'unknown')}"
    job = {
        "id": job_id,
        "config": config,
        "status": "pending",
        "progress": 0,
        "log": "Job added to queue.",
        "created_at": time.time()
    }
    JOB_STATUS[job_id] = job
    BATCH_QUEUE.put(job_id)
    return job_id

def process_batch_queue():
    while True:
        job_id = BATCH_QUEUE.get()
        if job_id is None:
            break
            
        job = JOB_STATUS[job_id]
        job["status"] = "running"
        
        try:
            execute_batch_job(job)
            job["status"] = "completed"
            job["progress"] = 100
        except Exception as e:
            job["status"] = "failed"
            job["log"] = str(e)
            print(f"[Batch] Job {job_id} failed: {e}")
            
        JOB_HISTORY.append(job)
        BATCH_QUEUE.task_done()

def execute_batch_job(job: dict):
    def update_log(msg, prog):
        job["log"] = msg
        job["progress"] = prog
        print(f"[Batch] {msg}")

    config = job["config"]
    board = config.get("board", "b")
    
    update_log(f"Scouting best thread on /{board}/...", 5)
    candidates = get_catalog_page_candidates(board, 0)
    if not candidates:
        raise Exception(f"No candidates found on /{board}/")

    best_id, reason, preview = scout_best_thread(candidates)
    if not best_id:
        raise Exception("LLM failed to scout a suitable thread.")

    update_log(f"Fetching thread {best_id}...", 15)
    op_text, replies_data = get_all_thread_data(board, best_id)
    if not op_text:
        raise Exception("Failed to fetch thread data.")

    update_log("Curating script...", 25)
    llm_result = curate_and_censor_thread(op_text, replies_data[:25])
    if not llm_result:
        raise Exception("LLM failed to curate thread.")

    selected_replies = llm_result.get("selected_replies", [])
    for sr in selected_replies:
        if "censored_text" in sr:
            sr["text"] = sr.pop("censored_text")

    playlist = [{"id": best_id, "text": llm_result.get("op_censored", op_text)}] + selected_replies
    
    update_log("Preparing render assets...", 35)
    bg_video = get_random_background()
    if not bg_video:
        raise Exception("No video files found in assets/.")

    os.makedirs("temp", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # ── Phase 1: Batch Screenshots ──
    update_log("Capturing post screenshots...", 40)
    screenshot_results = capture_posts_batch(
        board, best_id, playlist,
        output_dir="temp",
        progress_callback=lambda d, t: update_log(f"Captured screenshot {d}/{t}", 40 + int((d/t)*15))
    )
    if not screenshot_results:
        raise Exception("No screenshots captured.")

    # ── Phase 2: TTS ──
    update_log("Generating voiceover audio...", 60)
    tts_voice = config.get("tts_voice", "en-US-ChristopherNeural")
    tts_rate = config.get("tts_rate", "+15%")
    total_tts = len(playlist)
    completed_tts = 0

    with ThreadPoolExecutor(max_workers=min(4, max(1, total_tts))) as pool:
        futures = {}
        for post in playlist:
            audio_path = f"temp/audio_{post['id']}.mp3"
            fut = pool.submit(generate_tts, post['text'], audio_path, voice=tts_voice, rate=tts_rate)
            futures[fut] = (post['id'], audio_path)

        for fut in as_completed(futures):
            pid, apath = futures[fut]
            try:
                fut.result()
            except Exception as e:
                print(f"  [TTS] Error for post {pid}: {e}")
            completed_tts += 1
            update_log(f"Generated audio {completed_tts}/{total_tts}", 60 + int((completed_tts/total_tts)*15))

    # ── Phase 3: Assembly ──
    ordered_imgs, ordered_audios = [], []
    for post in playlist:
        pid = post['id']
        img_path = f"temp/post_{pid}.png"
        audio_path = f"temp/audio_{pid}.mp3"
        if os.path.exists(img_path) and os.path.exists(audio_path):
            ordered_imgs.append(img_path)
            ordered_audios.append(audio_path)

    if not ordered_imgs:
        raise Exception("No scenes generated.")

    # ── Phase 4: Render ──
    update_log("Encoding video...", 80)
    out = f"output/shorts_{best_id}.mp4"
    
    cfg = load_config()
    v_fps = int(cfg.get("video_fps", 30))
    v_preset = cfg.get("video_preset", "fast")
    music_file = config.get("music_file", "")
    music_volume = float(config.get("music_volume", 0.15))
    
    make_video(
        bg_video, ordered_imgs, ordered_audios, out,
        music_path=os.path.join("assets", "music", music_file) if music_file else None,
        music_volume=music_volume,
        fps=v_fps,
        preset=v_preset
    )

    update_log(f"Done! Rendered to {out}", 100)

# Start background thread automatically
threading.Thread(target=process_batch_queue, daemon=True).start()
