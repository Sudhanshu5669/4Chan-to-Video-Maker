import os
import sys
import glob
import random
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from scraper import interactive_post_selection, get_catalog_page_candidates, clean_text, get_all_boards
from screenshot import capture_post
from tts import generate_tts
from video import make_video
from llm import curate_and_censor_thread, scout_best_thread


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def get_random_background(folder="assets"):
    """Pick a random video file from the assets folder."""
    extensions = ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm")
    videos = []
    for ext in extensions:
        videos.extend(glob.glob(os.path.join(folder, ext)))
    if not videos:
        return None
    chosen = random.choice(videos)
    print(f"  🎬  Background: {os.path.basename(chosen)}")
    return chosen


def get_raw_thread_data(board, thread_id):
    """Fetches the OP and the top 25 replies, skipping image-only posts."""
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    resp = requests.get(url, headers={"User-Agent": "4chanBot/2.0"}, timeout=10).json()
    posts = resp["posts"]

    op_text = clean_text(posts[0].get("com", ""))

    replies_data = []
    for p in posts[1:26]:
        text = clean_text(p.get("com", ""))
        if text and len(text) > 20:
            replies_data.append({"id": p["no"], "text": text})

    return op_text, replies_data


def generate_scene(args):
    """Worker: captures screenshot + generates TTS for one post. Returns (index, img, audio)."""
    index, board, thread_id, post = args
    p_id   = post["id"]
    text   = post["text"]
    img    = f"temp/post_{p_id}.png"
    audio  = f"temp/audio_{p_id}.mp3"

    print(f"  ⚙️  Scene {index+1} – post {p_id}")
    capture_post(board, thread_id, p_id, img, replacement_text=text)
    generate_tts(text, audio)
    return index, img, audio


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def run_automation():
    for folder in ("temp", "assets", "output"):
        os.makedirs(folder, exist_ok=True)

    print("""
╔══════════════════════════════════════╗
║  🤖  4CHAN → SHORTS AUTOPILOT  🤖   ║
╚══════════════════════════════════════╝
""")

    # ── 1. BACKGROUND VIDEO ──────────────────
    bg_video = get_random_background()
    if not bg_video:
        print("ERROR: No video files found in assets/. Add at least one .mp4 file.")
        return

    # ── 2. BOARD SELECTION ───────────────────
    print("Fetching live board list…")
    try:
        boards      = get_all_boards()
        valid_boards = [b["board"] for b in boards]

        col = 32
        for i in range(0, len(boards), 3):
            row = boards[i : i + 3]
            print("".join(f"/{b['board']}/ - {b['title']}"[:col-2].ljust(col) for b in row))

        target_board = ""
        while target_board not in valid_boards:
            target_board = input("\nBoard (e.g. v, g, pol): ").strip().strip("/")
            if target_board not in valid_boards:
                print(f"  ✗ '{target_board}' not found – try again.")
    except Exception as e:
        print(f"Failed to fetch boards: {e}")
        target_board = input("Enter board letter manually: ").strip().strip("/")

    # ── 3. MODE ──────────────────────────────
    print(f"\n[ /{target_board}/ selected ]\n")
    print("  [1]  Manual   – browse catalog yourself")
    print("  [2]  Auto     – AI picks the best thread & renders immediately")
    print("  [3]  Review   – AI scouts, you approve each step\n")
    mode = input("Choice (1/2/3): ").strip()

    thread_id      = None
    rejected_ids   = set()   # prevent re-suggesting the same thread

    # ── 4. THREAD SELECTION ──────────────────
    if mode == "1":
        thread_id = interactive_post_selection(target_board)

    elif mode in ("2", "3"):
        page = 0
        while thread_id is None:
            print(f"\n  📄  Scanning catalog page {page + 1}…")
            candidates = get_catalog_page_candidates(target_board, page)

            if not candidates:
                print("  No more pages. Nothing good found – exiting.")
                return

            # Filter already-rejected threads
            candidates = [c for c in candidates if c["id"] not in rejected_ids]

            while candidates and thread_id is None:
                best_id, reason, preview = scout_best_thread(candidates)

                if best_id is None:
                    print(f"  🔍  Scout: {reason}")
                    break   # move to next catalog page

                if mode == "3":
                    print(f"\n  🎯  SUGGESTION  (thread {best_id})")
                    print(f"  WHY:     {reason}")
                    print(f"  PREVIEW: {preview}\n")
                    choice = input("  Make this video? (y/n): ").strip().lower()
                    if choice == "y":
                        thread_id = best_id
                    else:
                        rejected_ids.add(best_id)
                        candidates = [c for c in candidates if c["id"] != best_id]
                        print("  Rejected – finding another…")
                else:
                    print(f"  ✅  Auto-selected thread {best_id}: {reason}")
                    thread_id = best_id

            if thread_id is None:
                page += 1
                time.sleep(1.1)
    else:
        print("Invalid choice.")
        return

    # ── 5. FETCH & CURATE ────────────────────
    try:
        print(f"\n  📥  Fetching thread {thread_id}…")
        op_text, replies_data = get_raw_thread_data(target_board, thread_id)

        if not op_text:
            print("  ✗ Thread has no readable text (image-only OP?).")
            return

        llm_result = curate_and_censor_thread(op_text, replies_data)
        if not llm_result:
            print("  ✗ LLM editor failed – aborting.")
            return

        # ── 6. REPLY REVIEW (mode 3 only) ────
        playlist = [{"id": thread_id, "text": llm_result["op_censored"]}]
        reply_mode = "1"

        if mode == "3":
            print("\n  ✂️   Script ready. Reply handling:")
            print("  [1] Auto   – include all selected replies")
            print("  [2] Review – approve each reply individually")
            reply_mode = input("  Choice (1/2): ").strip()

        if reply_mode == "2":
            print(f"\n  OP [auto-included]: {llm_result['op_censored']}\n")
            for rep in llm_result.get("selected_replies", []):
                print(f"  → Reply {rep['id']}: {rep['censored_text']}")
                if input("    Include? (y/n): ").strip().lower() == "y":
                    playlist.append({"id": rep["id"], "text": rep["censored_text"]})
                else:
                    print("    [discarded]")
        else:
            for rep in llm_result.get("selected_replies", []):
                playlist.append({"id": rep["id"], "text": rep["censored_text"]})

        print(f"\n  🎬  {len(playlist)} scenes queued.\n")

        # ── 7. PARALLEL MEDIA GENERATION ─────
        args_list = [
            (i, target_board, thread_id, post)
            for i, post in enumerate(playlist)
        ]

        # Results keyed by index to preserve order
        results = {}
        with ThreadPoolExecutor(max_workers=min(4, len(playlist))) as pool:
            futures = {pool.submit(generate_scene, a): a[0] for a in args_list}
            for fut in as_completed(futures):
                try:
                    idx, img, audio = fut.result()
                    results[idx] = (img, audio)
                except Exception as exc:
                    print(f"  ⚠️  Scene {futures[fut]+1} failed: {exc}")

        # Re-order
        ordered_imgs   = []
        ordered_audios = []
        for i in range(len(playlist)):
            if i in results:
                img, audio = results[i]
                ordered_imgs.append(img)
                ordered_audios.append(audio)
            else:
                print(f"  ⚠️  Skipping scene {i+1} (generation failed).")

        if not ordered_imgs:
            print("  ✗ No scenes were generated successfully.")
            return

        # ── 8. RENDER ────────────────────────
        print("\n  🖥️   Rendering final video…")
        out = f"output/shorts_{thread_id}.mp4"
        make_video(bg_video, ordered_imgs, ordered_audios, out)
        print(f"\n  ✅  Done!  →  {out}\n")

    except Exception as e:
        import traceback
        print(f"\n  ✗ FAILED: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    run_automation()