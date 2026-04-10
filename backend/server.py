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
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from Uploader import upload_to_youtube
from scraper import get_catalog_page_candidates, clean_text, get_all_boards
from screenshot import capture_post
from tts import generate_tts
from video import make_video
from llm import curate_and_censor_thread, scout_best_thread

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

    op_text = clean_text(posts[0].get("com", ""))

    replies_data = []
    for p in posts[1:]:
        text = clean_text(p.get("com", ""))
        if text and len(text) > 20: # Ensure valid text
            replies_data.append({"id": p["no"], "text": text})

    return op_text, replies_data

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
    op_text, replies_data = get_all_thread_data(board, thread_id)
    if not op_text and not replies_data:
        raise HTTPException(status_code=404, detail="Thread not found or no readable text.")

    # We only curate using top 25 replies for LLM context length/time
    llm_result = curate_and_censor_thread(op_text, replies_data[:25])
    
    if not llm_result:
        raise HTTPException(status_code=500, detail="LLM Editor failed to curate thread.")

    selected_replies = llm_result.get("selected_replies", [])
    for sr in selected_replies:
        if "censored_text" in sr:
            sr["text"] = sr.pop("censored_text")
            
    selected_ids = {r["id"] for r in selected_replies}
    
    # Filter out selected replies from 'all replies' to return 'other replies'
    other_replies = [r for r in replies_data if r["id"] not in selected_ids]

    return {
        "op": {
            "id": thread_id,
            "text": llm_result.get("op_censored", op_text)
        },
        "selected_replies": selected_replies,
        "other_replies": other_replies
    }

@app.get("/api/thread_stream/{board}/{thread_id}")
def api_get_thread_stream(board: str, thread_id: int):
    # Fetch all replies for pagination purposes
    op_text, replies_data = get_all_thread_data(board, thread_id)
    if not op_text and not replies_data:
        raise HTTPException(status_code=404, detail="Thread not found or no readable text.")

    from llm import curate_and_censor_thread_stream
    import json
    
    def generate():
        for event_type, data in curate_and_censor_thread_stream(op_text, replies_data[:25]):
            if event_type == "chunk":
                yield f"event: chunk\ndata: {json.dumps(data)}\n\n"
            elif event_type == "result":
                selected_replies = data.get("selected_replies", [])
                for sr in selected_replies:
                    if "censored_text" in sr:
                        sr["text"] = sr.pop("censored_text")
                selected_ids = {r["id"] for r in selected_replies}
                other_replies = [r for r in replies_data if r["id"] not in selected_ids]
                
                final_payload = {
                    "op": {
                        "id": thread_id,
                        "text": data.get("op_censored", op_text)
                    },
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

            playlist = req.playlist
            if not playlist:
                raise Exception("Playlist is empty.")
                
            os.makedirs("temp", exist_ok=True)
            os.makedirs("output", exist_ok=True)

            q.put({"type": "progress", "status": "Generating scenes and TTS audio...", "progress": 5})

            args_list = [(i, req.board, req.thread_id, post) for i, post in enumerate(playlist)]
            results = {}
            
            total_scenes = len(playlist)
            completed_scenes = 0
            
            with ThreadPoolExecutor(max_workers=min(4, max(1, total_scenes))) as pool:
                futures = {pool.submit(generate_scene, a): a[0] for a in args_list}
                for fut in as_completed(futures):
                    try:
                        idx, img, audio = fut.result()
                        results[idx] = (img, audio)
                    except Exception as exc:
                        print(f"Scene error: {exc}")
                    completed_scenes += 1
                    prog = 5 + int((completed_scenes / total_scenes) * 40)
                    q.put({"type": "progress", "status": f"Generated scene {completed_scenes}/{total_scenes}", "progress": prog})

            ordered_imgs = []
            ordered_audios = []
            for i in range(total_scenes):
                if i in results:
                    img, audio = results[i]
                    ordered_imgs.append(img)
                    ordered_audios.append(audio)

            if not ordered_imgs:
                raise Exception("No scenes generated successfully.")

            out = f"output/shorts_{req.thread_id}.mp4"
            
            q.put({"type": "progress", "status": "Encoding final video... (this will take a few minutes)", "progress": 50})
            make_video(bg_video, ordered_imgs, ordered_audios, out)
            
            uploaded = False
            if req.upload_to_youtube:
                q.put({"type": "progress", "status": "Uploading to YouTube...", "progress": 80})
                
                # Enforce fallback titles if user skipped them
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
                yield f"event: progress\ndata: {json.dumps(msg)}\n\n"
            elif msg["type"] == "result":
                yield f"event: result\ndata: {json.dumps(msg)}\n\n"
                break
            elif msg["type"] == "error":
                yield f"event: error\ndata: {json.dumps(msg)}\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")
