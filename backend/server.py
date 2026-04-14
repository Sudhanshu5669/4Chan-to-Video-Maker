import os
import sys
import glob
import random
import requests
import asyncio
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from Uploader import upload_to_youtube
from scraper import get_catalog_page_candidates, clean_text, get_all_boards
from screenshot import capture_post, capture_posts_batch
from tts import generate_tts
from video import make_video
from llm import curate_thread, scout_best_thread

# Add backend to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="4Chan-To-Video API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────────
class BoardListResponse(BaseModel):
    boards: List[dict]

class CatalogRequest(BaseModel):
    board: str
    page: int = 0

class ScoutRequest(BaseModel):
    candidates: List[dict]

class RenderRequest(BaseModel):
    board: str
    thread_id: int
    playlist: List[dict]
    title: str = ""
    description: str = ""
    upload_to_youtube: bool = False
    tts_rate: str = "+15%"
    tts_voice: str = "en-US-ChristopherNeural"
    music_file: str = ""
    music_volume: float = 0.15
    ken_burns: bool = False

# ─────────────────────────────────────────────
#  HELPERS FROM MAIN.PY (COPIED/MODIFIED)
# ─────────────────────────────────────────────
def get_random_background(folder="assets"):
    extensions = ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm")
    videos = []
    for ext in extensions:
        videos.extend(glob.glob(os.path.join(folder, ext)))
    if not videos:
        return None
    return random.choice(videos)

def get_all_thread_data(board, thread_id):
    """Fetches the OP and ALL replies (not just top 25)."""
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    r = requests.get(url, headers={"User-Agent": "4chanBot/2.0"}, timeout=10)
    if r.status_code != 200:
        return None, []
        
    posts = r.json().get("posts", [])
    if not posts:
        return None, []

    op_post = posts[0]
    op_text = clean_text(op_post.get("com", ""))
    op_has_image = "tim" in op_post
    op_data = {
        "text": op_text,
        "has_image": op_has_image,
        "image_url": f"https://i.4cdn.org/{board}/{op_post['tim']}{op_post['ext']}" if op_has_image else None,
        "thumb_url": f"https://i.4cdn.org/{board}/{op_post['tim']}s.jpg" if op_has_image else None
    }

    replies_data = []
    for p in posts[1:]:
        text = clean_text(p.get("com", ""))
        has_image = "tim" in p
        if text and len(text) > 20 or has_image: # Keep short text posts if they have an image
            reply_img = f"https://i.4cdn.org/{board}/{p['tim']}{p['ext']}" if has_image else None
            reply_thumb = f"https://i.4cdn.org/{board}/{p['tim']}s.jpg" if has_image else None
            replies_data.append({
                "id": p["no"], 
                "text": text,
                "has_image": has_image,
                "image_url": reply_img,
                "thumb_url": reply_thumb
            })

    return op_data, replies_data

def generate_scene(args):
    index, board, thread_id, post = args
    p_id   = post["id"]
    text   = post["text"]
    
    os.makedirs("temp", exist_ok=True)
    img    = f"temp/post_{p_id}.png"
    audio  = f"temp/audio_{p_id}.mp3"

    capture_post(board, thread_id, p_id, img, replacement_text=text)
    generate_tts(text, audio)
    return index, img, audio

# ─────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/api/boards")
def api_get_boards():
    try:
        boards = get_all_boards()
        return {"boards": boards}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/catalog/{board}")
def api_get_catalog(board: str, page: int = 0):
    candidates = get_catalog_page_candidates(board, page)
    if candidates is None:
        return {"candidates": []}
    return {"candidates": candidates}

@app.post("/api/scout")
def api_scout_thread(req: ScoutRequest):
    if not req.candidates:
        return {"best_id": None, "reason": "No candidates provided"}
    best_id, reason, preview = scout_best_thread(req.candidates)
    return {
        "best_id": best_id,
        "reason": reason,
        "preview": preview
    }

@app.post("/api/scout_stream")
def api_scout_stream(req: ScoutRequest):
    from llm import scout_best_thread_stream
    import json
    if not req.candidates:
        raise HTTPException(status_code=400, detail="No candidates provided")

    def generate():
        for event_type, data in scout_best_thread_stream(req.candidates):
            if event_type == "chunk":
                yield f"event: chunk\ndata: {json.dumps(data)}\n\n"
            elif event_type == "result":
                yield f"event: result\ndata: {json.dumps(data)}\n\n"
            elif event_type == "error":
                yield f"event: error\ndata: {json.dumps({'error': data})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/thread/{board}/{thread_id}")
def api_get_thread(board: str, thread_id: int):
    # Fetch all replies for pagination purposes
    op_data, replies_data = get_all_thread_data(board, thread_id)
    if not op_data and not replies_data:
        raise HTTPException(status_code=404, detail="Thread not found or no readable text.")

    # We only curate using top 25 replies for LLM context length/time
    llm_result = curate_thread(op_data["text"], replies_data[:25])
    
    if not llm_result:
        raise HTTPException(status_code=500, detail="LLM Editor failed to curate thread.")

    selected_replies = llm_result.get("selected_replies", [])
    reply_meta_map = {r["id"]: r for r in replies_data}
    
    for sr in selected_replies:
        if sr["id"] in reply_meta_map:
            meta = reply_meta_map[sr["id"]]
            sr["has_image"] = meta.get("has_image", False)
            sr["image_url"] = meta.get("image_url")
            sr["thumb_url"] = meta.get("thumb_url")
            
    selected_ids = {r["id"] for r in selected_replies}
    
    # Filter out selected replies from 'all replies' to return 'other replies'
    other_replies = [r for r in replies_data if r["id"] not in selected_ids]

    op_entry = dict(op_data)
    op_entry["id"] = thread_id
    op_entry["text"] = llm_result.get("op_text", op_data["text"])

    return {
        "op": op_entry,
        "selected_replies": selected_replies,
        "other_replies": other_replies
    }

@app.get("/api/thread_stream/{board}/{thread_id}")
def api_get_thread_stream(board: str, thread_id: int):
    # Fetch all replies for pagination purposes
    op_data, replies_data = get_all_thread_data(board, thread_id)
    if not op_data and not replies_data:
        raise HTTPException(status_code=404, detail="Thread not found or no readable text.")

    from llm import curate_thread_stream
    import json
    
    def generate():
        for event_type, data in curate_thread_stream(op_data["text"], replies_data[:25]):
            if event_type == "chunk":
                yield f"event: chunk\ndata: {json.dumps(data)}\n\n"
            elif event_type == "result":
                selected_replies = data.get("selected_replies", [])
                reply_meta_map = {r["id"]: r for r in replies_data}
                
                for sr in selected_replies:
                    if sr["id"] in reply_meta_map:
                        meta = reply_meta_map[sr["id"]]
                        sr["has_image"] = meta.get("has_image", False)
                        sr["image_url"] = meta.get("image_url")
                        sr["thumb_url"] = meta.get("thumb_url")
                        
                selected_ids = {r["id"] for r in selected_replies}
                other_replies = [r for r in replies_data if r["id"] not in selected_ids]
                
                op_entry = dict(op_data)
                op_entry["id"] = thread_id
                op_entry["text"] = data.get("op_text", op_data["text"])

                final_payload = {
                    "op": op_entry,
                    "selected_replies": selected_replies,
                    "other_replies": other_replies
                }
                yield f"event: result\ndata: {json.dumps(final_payload)}\n\n"
            elif event_type == "error":
                yield f"event: error\ndata: {json.dumps({'error': data})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/render_stream")
def api_render_stream(req: RenderRequest):
    import json
    q = queue.Queue()

    def worker():
        try:
            q.put({"type": "progress", "status": "Initializing render process...", "progress": 2})

            bg_video = get_random_background()
            if not bg_video:
                raise Exception("No video files found in assets/. Add at least one .mp4 file.")

            from llm import censor_playlist
            q.put({"type": "progress", "status": "Censoring script...", "progress": 3})
            playlist = censor_playlist(req.playlist)
            
            if not playlist:
                raise Exception("Playlist is empty.")
                
            os.makedirs("temp", exist_ok=True)
            os.makedirs("output", exist_ok=True)

            # ── Phase 1: Batch Screenshots (single browser instance) ──
            q.put({"type": "progress", "status": "Capturing post screenshots...", "progress": 5})

            def on_screenshot_progress(done, total):
                prog = 5 + int((done / total) * 20)
                q.put({"type": "progress", "status": f"Captured screenshot {done}/{total}", "progress": prog})

            import re
            ss_playlist = []
            for post in playlist:
                # Strip specific XML tags before screenshotting, replacing profanity with asterisks
                clean_text = re.sub(r'<censor>.*?</censor>', '***', post['text'])
                clean_text = re.sub(r'<pause=[0-9.]+s>', '', clean_text)
                ss_playlist.append({"id": post['id'], "text": clean_text, "hide_image": post.get("hide_image", False)})

            screenshot_results = capture_posts_batch(
                req.board, req.thread_id, ss_playlist,
                output_dir="temp",
                progress_callback=on_screenshot_progress
            )

            if not screenshot_results:
                raise Exception("No screenshots captured successfully.")

            # ── Phase 2: Parallel TTS Generation ──
            q.put({"type": "progress", "status": "Generating voiceover audio...", "progress": 28})

            tts_rate = req.tts_rate
            tts_voice = req.tts_voice
            total_tts = len(playlist)
            completed_tts = 0

            with ThreadPoolExecutor(max_workers=min(4, max(1, total_tts))) as pool:
                futures = {}
                for post in playlist:
                    audio_path = f"temp/audio_{post['id']}.mp3"
                    p_voice = post.get("voice") or tts_voice
                    fut = pool.submit(generate_tts, post['text'], audio_path, voice=p_voice, rate=tts_rate)
                    futures[fut] = (post['id'], audio_path)

                for fut in as_completed(futures):
                    pid, apath = futures[fut]
                    try:
                        fut.result()
                    except Exception as e:
                        print(f"  [TTS] Error for post {pid}: {e}")
                    completed_tts += 1
                    prog = 28 + int((completed_tts / total_tts) * 17)
                    q.put({"type": "progress", "status": f"Generated audio {completed_tts}/{total_tts}", "progress": prog})

            # ── Phase 3: Assemble ordered media ──
            ordered_imgs = []
            ordered_audios = []
            for post in playlist:
                pid = post['id']
                img_path = f"temp/post_{pid}.png"
                audio_path = f"temp/audio_{pid}.mp3"
                if os.path.exists(img_path) and os.path.exists(audio_path):
                    ordered_imgs.append(img_path)
                    ordered_audios.append(audio_path)

            if not ordered_imgs:
                raise Exception("No scenes generated successfully.")

            # ── Phase 4: Render Video ──
            out = f"output/shorts_{req.thread_id}.mp4"
            q.put({"type": "progress", "status": "Encoding final video... (this may take a few minutes)", "progress": 50})
            from config import load_config
            cfg = load_config()
            v_fps = int(cfg.get("video_fps", 30))
            v_preset = cfg.get("video_preset", "fast")

            make_video(
                bg_video, ordered_imgs, ordered_audios, out,
                music_path=os.path.join("assets", "music", req.music_file) if req.music_file else None,
                music_volume=req.music_volume,
                fps=v_fps,
                preset=v_preset,
                apply_ken_burns=req.ken_burns
            )

            # ── Phase 5: YouTube Upload (optional) ──
            uploaded = False
            if req.upload_to_youtube:
                q.put({"type": "progress", "status": "Uploading to YouTube...", "progress": 80})

                video_title = req.title.strip() if req.title.strip() else f"4chan /{req.board}/ is actually unhinged 💀"
                video_description = req.description.strip() if req.description.strip() else f"They really said that... \n\n#4chan #greentext #{req.board} #redditstories #shorts"

                def yt_progress(pct):
                    q.put({"type": "progress", "status": f"Uploading to YouTube... {int(pct*100)}%", "progress": 80 + int(pct * 19)})

                upload_to_youtube(
                    video_path=out,
                    title=video_title,
                    description=video_description,
                    tags=["4chan", "greentext", "reddit stories", "shorts", "tiktok"],
                    privacy="public",
                    progress_callback=yt_progress
                )
                uploaded = True

            # ── Phase 6: Cleanup temp files ──
            q.put({"type": "progress", "status": "Cleaning up...", "progress": 99})
            for f in glob.glob("temp/post_*.png") + glob.glob("temp/audio_*.mp3"):
                try:
                    os.remove(f)
                except OSError:
                    pass

            q.put({"type": "progress", "status": "Done!", "progress": 100})
            q.put({"type": "result", "file": out, "uploaded": uploaded})
        except Exception as str_err:
            q.put({"type": "error", "error": str(str_err)})

    def generate():
        thread = threading.Thread(target=worker)
        thread.start()
        while True:
            msg = q.get()
            if msg["type"] == "progress":
                yield f"event: chunk\ndata: {json.dumps(msg)}\n\n"
            elif msg["type"] == "result":
                yield f"event: result\ndata: {json.dumps(msg)}\n\n"
                break
            elif msg["type"] == "error":
                yield f"event: error\ndata: {json.dumps(msg)}\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─────────────────────────────────────────────
#  P2: ADDITIONAL ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/api/voices")
async def api_get_voices():
    """Lists available English TTS voices from edge-tts."""
    import edge_tts
    voices = await edge_tts.list_voices()
    en_voices = [
        {"name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
        for v in voices
        if v["Locale"].startswith("en-")
    ]
    return {"voices": en_voices}


@app.get("/api/video/{filename}")
def api_serve_video(filename: str):
    """Serves a rendered video file for in-browser preview."""
    filepath = os.path.join("output", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(filepath, media_type="video/mp4")


@app.get("/api/config")
def api_get_config():
    """Returns the current configuration."""
    from config import load_config
    return load_config()


@app.put("/api/config")
def api_update_config(body: dict):
    """Updates configuration values."""
    from config import update_config
    return update_config(body)


@app.get("/api/music")
def api_list_music():
    """Lists available background music files from assets/music/."""
    music_dir = os.path.join("assets", "music")
    os.makedirs(music_dir, exist_ok=True)
    tracks = []
    for ext in ("*.mp3", "*.wav", "*.ogg", "*.m4a"):
        for f in glob.glob(os.path.join(music_dir, ext)):
            tracks.append({
                "name": os.path.splitext(os.path.basename(f))[0],
                "file": os.path.basename(f),
            })
    return {"tracks": tracks}


@app.get("/api/models")
def api_get_models():
    """Queries Ollama for locally available models."""
    import ollama
    try:
        models_response = ollama.list()
        # Ollama API response structure often slightly varies between versions.
        # But generally it's models_response['models'][0]['name']
        models = [m.get("name", m.get("model")) for m in models_response.get("models", [])]
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
def api_get_history():
    """Returns local video history."""
    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    videos = []
    for f in glob.glob(os.path.join(out_dir, "*.mp4")):
        videos.append({
            "filename": os.path.basename(f),
            "size_bytes": os.path.getsize(f),
            "created_at": os.path.getctime(f),
        })
    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return {"videos": videos}


@app.delete("/api/history/{filename}")
def api_delete_history(filename: str):
    """Deletes a video from local history."""
    filepath = os.path.join("output", filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="File not found")

# ── P4: BATCH PIPELINE ENDPOINTS ─────────────────────────────────────────────

from pydantic import BaseModel

class BatchJobRequest(BaseModel):
    board: str
    amount: int
    tts_voice: str
    tts_rate: str
    music_file: str
    music_volume: float

@app.post("/api/batch")
def api_add_batch_job(req: BatchJobRequest):
    """Adds a new rendering job to the automated batch queue."""
    import batch
    job_ids = []
    # Queue up `amount` jobs using the provided config.
    for _ in range(req.amount):
        job_id = batch.add_batch_job(req.model_dump())
        job_ids.append(job_id)
    return {"status": "queued", "job_ids": job_ids}

@app.get("/api/batch/status")
def api_get_batch_status():
    """Returns the current pending, running, and historical jobs from the queue."""
    import batch
    active_jobs = [job for job in batch.JOB_STATUS.values() if job["status"] in ("pending", "running")]
    active_jobs.sort(key=lambda x: x["created_at"])
    
    historical = batch.JOB_HISTORY[-20:] # Return last 20 finished
    historical.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "active": active_jobs,
        "history": historical,
        "queue_size": batch.BATCH_QUEUE.qsize()
    }
