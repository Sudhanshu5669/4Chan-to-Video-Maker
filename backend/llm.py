import ollama
import json
import re
import time
from google import genai
from google.genai import types

from config import load_config

_embedder = None
def get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("  [Semantic Scout] Loading embedding model...")
            _embedder = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            print("  [Semantic Scout] sentence-transformers not installed. Skipping embedding.")
            return None
    return _embedder

def get_llm_settings():
    config = load_config()
    return {
        "model": config.get("llm_model", "llama3.1:8b"),
        "temperature": float(config.get("llm_temperature", 0.3)),
        "provider": config.get("llm_provider", "ollama"),
        "gemini_key": config.get("gemini_api_key", ""),
    }

def _get_gemini_client(api_key: str):
    """Create a Gemini client with the given API key."""
    return genai.Client(api_key=api_key)

def _call_llm(prompt: str, model: str = None, retries: int = 3) -> dict | None:
    settings = get_llm_settings()
    provider = settings["provider"]
    cfg_temp = settings["temperature"]
    
    if provider == "gemini" and settings["gemini_key"]:
        client = _get_gemini_client(settings["gemini_key"])
        for attempt in range(1, retries + 1):
            try:
                response = client.models.generate_content(
                    model='gemini-3.1-pro',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=cfg_temp,
                        response_mime_type="application/json",
                    ),
                )
                raw = response.text
                raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
                return json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"  [LLM] JSON parse error (attempt {attempt}/{retries}): {e}")
            except Exception as e:
                print(f"  [LLM] Error (attempt {attempt}/{retries}): {e}")
            time.sleep(1)
        return None
    else:
        cfg_model = settings["model"]
        model = model or cfg_model
        for attempt in range(1, retries + 1):
            try:
                response = ollama.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    format="json",
                    options={"temperature": cfg_temp},
                )
                raw = response["message"]["content"]
                raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
                return json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"  [LLM] JSON parse error (attempt {attempt}/{retries}): {e}")
            except Exception as e:
                print(f"  [LLM] Error (attempt {attempt}/{retries}): {e}")
            time.sleep(1)
        return None

def _call_llm_stream(prompt: str, model: str = None):
    settings = get_llm_settings()
    provider = settings["provider"]
    cfg_temp = settings["temperature"]
    
    if provider == "gemini" and settings["gemini_key"]:
        client = _get_gemini_client(settings["gemini_key"])
        try:
            for chunk in client.models.generate_content_stream(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=cfg_temp,
                    response_mime_type="application/json",
                ),
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise Exception(f"Gemini Streaming Error: {e}")
    else:
        cfg_model = settings["model"]
        model = model or cfg_model
        try:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                options={"temperature": cfg_temp},
                stream=True
            )
            for chunk in response:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
        except Exception as e:
            raise Exception(f"Ollama Streaming Error: {e}")

def semantic_filter(threads_data: list, top_k: int = 15):
    embedder = get_embedder()
    if not embedder or not threads_data:
        return threads_data[:top_k]
    
    import numpy as np
    print("  [Semantic Scout] Ranking threads by semantic dankness...")
    target_embedding = embedder.encode("funny highly engaging absurd story green text dank internet humor")
    target_norm = np.linalg.norm(target_embedding)
    
    scored_threads = []
    for t in threads_data:
        text_preview = t['text'][:500]
        t_emb = embedder.encode(text_preview)
        # Cosine similarity (not raw dot product)
        t_norm = np.linalg.norm(t_emb)
        if target_norm > 0 and t_norm > 0:
            score = float(np.dot(target_embedding, t_emb) / (target_norm * t_norm))
        else:
            score = 0.0
        scored_threads.append((score, t))
    
    scored_threads.sort(key=lambda x: x[0], reverse=True)
    return [t for score, t in scored_threads[:top_k]]

def scout_best_thread(threads_data: list, model: str = None):
    threads_data = semantic_filter(threads_data, top_k=15)
    context = "\n".join(
        f"ID:{t['id']} REPLIES:{t['replies']}\n{t['text']}"
        for t in threads_data
    )

    prompt = f"""You are a YouTube Shorts producer looking for extremely viral, funny, and dank 4chan threads. Review the threads below. Your goal is to pick the PERFECT thread with high comedic or dank potential.

THREADS:
{context}

VIRAL CRITERIA:
- Dank & Comedic: Is it genuinely funny, absurd, or unexpectedly hilarious?
- Strong hook: does the opening line grab attention instantly?
- Clear situation: is there an actual story, conflict, or scenario?
- Payoff: is there a satisfying punchline or twist?

If NONE of the threads pass, YOU MUST return null for selected_thread_id.
Return ONLY valid JSON and USE EXACT KEY NAMES:
{{"selected_thread_id": <int or null>, "reason": "<reason>", "preview": "<preview>"}}"""

    print("  [Scout] Analyzing threads…")
    data = _call_llm(prompt, model)
    if data is None:
        return None, "LLM failed", ""
    return data.get("selected_thread_id"), data.get("reason", ""), data.get("preview", "")

def curate_and_censor_thread(op_text: str, replies_data: list, model: str = None) -> dict | None:
    replies_block = "\n".join(f"ID {r['id']}: {r['text']}" for r in replies_data)
    prompt = f"""You are a script editor for a viral YouTube Shorts channel. Edit the thread into a clean, entertaining short-form video script.

OP:
{op_text}

REPLIES:
{replies_block}

TASKS:
1. Select 2-5 best replies. Remove low-effort replies.
2. Censor profanity by replacing only the remaining letters with <censor> tags. The first letter stays out. E.g., shit -> s<censor>hit</censor>, fucking -> f<censor>ucking</censor>.
3. Add '<pause=1s>' strings where dramatic pauses are needed for comedic timing.

Return ONLY valid JSON:
{{"op_censored": "<string>", "selected_replies": [{{"id": <int>, "censored_text": "<string>"}}]}}"""
    data = _call_llm(prompt, model)
    if data is None: return None
    
    valid_ids = {r["id"] for r in replies_data}
    data["selected_replies"] = [
        r for r in data.get("selected_replies", [])
        if r.get("id") in valid_ids
    ]
    return data

def scout_best_thread_stream(threads_data: list, model: str = None):
    if not threads_data:
        yield ("error", "No threads provided.")
        return
        
    yield ("chunk", "\n[Semantic Scout] Filtering catalog top threads...\n\n")
    threads_data = semantic_filter(threads_data, top_k=15)
    
    yield ("chunk", "\n[Pass 1] Generating Dankness Leaderboard...\n\n")
    context_p1 = "\n".join(
        f"ID:{t['id']} | REPLIES:{t['replies']}\n{t['text'][:500]}..."
        for t in threads_data
    )

    prompt_p1 = f"""Score each thread out of 10 for viral potential.
THREADS:
{context_p1}
Return ONLY valid JSON: {{"scores": [{{"id": <int>, "score": <float>, "hook": "<summary>"}}]}}"""

    try:
        full_text_p1 = ""
        for chunk in _call_llm_stream(prompt_p1, model):
            full_text_p1 += chunk
            yield ("chunk", chunk)
            
        raw_p1 = re.sub(r"```(?:json)?\s*|\s*```", "", full_text_p1).strip()
        data_p1 = json.loads(raw_p1)
        scores = data_p1.get("scores", [])
        if not scores:
            yield ("error", "Failed to score threads.")
            return

        scores.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_candidates = scores[:3]
        
        yield ("chunk", "\n\n[Pass 2] Deep analysis of Top 3 candidates...\n\n")
        valid_ids = {t["id"]: t for t in threads_data}
        context_p2 = "\n\n".join(
            f"ID:{c['id']} | REPLIES:{valid_ids[c['id']]['replies']}\n{valid_ids[c['id']]['text']}"
            for c in top_candidates if c["id"] in valid_ids
        )
        
        prompt_p2 = f"""Pick the BEST thread for a viral video.
Contenders:
{context_p2}
Return valid JSON: {{"selected_thread_id": <int>, "reason": "<string>", "preview": "<string>"}}"""

        full_text_p2 = ""
        for chunk in _call_llm_stream(prompt_p2, model):
            full_text_p2 += chunk
            yield ("chunk", chunk)

        raw_p2 = re.sub(r"```(?:json)?\s*|\s*```", "", full_text_p2).strip()
        data_p2 = json.loads(raw_p2)
        
        best_id = data_p2.get("selected_thread_id")
        if best_id not in valid_ids:
            best_id = top_candidates[0]["id"] if top_candidates else None
            
        leaderboard = [{"id": c["id"], "score": c.get("score", 0), "hook": c.get("hook", "")} for c in scores if c["id"] in valid_ids]
        yield ("result", {"best_id": best_id, "reason": data_p2.get("reason", ""), "preview": data_p2.get("preview", ""), "leaderboard": leaderboard})
    except Exception as e:
        yield ("error", str(e))

def curate_and_censor_thread_stream(op_text: str, replies_data: list, model: str = None):
    replies_block = "\n".join(f"ID {r['id']}: {r['text']}" for r in replies_data)
    prompt = f"""You are a script editor for a viral YouTube Shorts channel. Edit the thread into a clean, entertaining short-form video script.

OP:
{op_text}

REPLIES:
{replies_block}

TASKS:
1. Select 2-5 best replies. Remove low-effort replies.
2. Censor profanity by replacing only the remaining letters with <censor> tags. The first letter stays out. E.g., shit -> s<censor>hit</censor>, fucking -> f<censor>ucking</censor>.
3. Add '<pause=1s>' strings where dramatic pauses are needed for comedic timing.
4. Make sure the sequence reads like a short story from top to bottom.

Return ONLY valid JSON:
{{"op_censored": "<string>", "selected_replies": [{{"id": <int>, "censored_text": "<string>"}}]}}"""

    yield ("chunk", "\n[Editor] Curating script and formatting pacing tags...\n\n")
    try:
        full_text = ""
        for chunk in _call_llm_stream(prompt, model):
            full_text += chunk
            yield ("chunk", chunk)
            
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", full_text).strip()
        data = json.loads(raw)
        
        valid_ids = {r["id"] for r in replies_data}
        data["selected_replies"] = [
            r for r in data.get("selected_replies", [])
            if r.get("id") in valid_ids
        ]
        yield ("result", data)
    except Exception as e:
        yield ("error", str(e))
