import ollama
import json
import re
import time

from config import load_config

def get_llm_settings():
    config = load_config()
    return config.get("llm_model", "llama3.1:8b"), float(config.get("llm_temperature", 0.3))

def _call_ollama(prompt: str, model: str = None, retries: int = 3) -> dict | None:
    """Calls ollama with retry logic and robust JSON extraction."""
    cfg_model, cfg_temp = get_llm_settings()
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
            # Strip any accidental markdown fences
            raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  [LLM] JSON parse error (attempt {attempt}/{retries}): {e}")
        except Exception as e:
            print(f"  [LLM] Error (attempt {attempt}/{retries}): {e}")
        time.sleep(1)
    return None


def scout_best_thread(threads_data: list, model: str = None):
    """
    Picks the single best thread for a viral YouTube Short.
    Returns (thread_id | None, reason: str, preview: str).
    """
    context = "\n".join(
        f"ID:{t['id']} REPLIES:{t['replies']}\n{t['text']}"
        for t in threads_data
    )

    prompt = f"""You are a YouTube Shorts producer looking for extremely viral, funny, and dank 4chan threads. Review the threads below. Your goal is to pick the PERFECT thread with high comedic or dank potential.

THREADS:
{context}

VIRAL CRITERIA (score each internally, pick highest total):
- Dank & Comedic: Is it genuinely funny, absurd, or unexpectedly hilarious?
- Strong hook: does the opening line grab attention instantly?
- Clear situation: is there an actual story, conflict, or scenario?
- Payoff: is there a satisfying punchline or twist?

STRICT REJECTION (Return null if no thread passes):
- No clear story or situation
- Just a random question or boring statement
- Hateful, overly political, or illegal content
- NOT FUNNY OR DANK: If it's just sad or mundane, skip it.

If NONE of the threads are truly perfect or hilarious, YOU MUST return null for selected_thread_id. Do not settle for a mediocre thread.

Return ONLY valid JSON, no commentary:
{{
  "selected_thread_id": <integer id or null>,
  "reason": "<one sentence: explain its funny/dank potential>",
  "preview": "<2-sentence teaser hook for the video>"
}}"""

    print("  [Scout] Analyzing threads…")
    data = _call_ollama(prompt, model)

    if data is None:
        return None, "LLM failed to respond.", ""

    tid = data.get("selected_thread_id")
    # Validate that the returned ID actually exists in our list
    if tid is not None:
        valid_ids = {t["id"] for t in threads_data}
        if tid not in valid_ids:
            return None, f"LLM returned invalid ID {tid}.", ""

    return (
        tid,
        data.get("reason", ""),
        data.get("preview", ""),
    )


def curate_and_censor_thread(op_text: str, replies_data: list, model: str = None) -> dict | None:
    """
    Selects the best 1-5 replies and censors profanity.
    Returns {"op_censored": str, "selected_replies": [{"id": int, "censored_text": str}]}
    """
    replies_block = "\n".join(f"ID {r['id']}: {r['text']}" for r in replies_data)

    prompt = f"""You are a script editor for a viral YouTube Shorts channel. Edit the thread below into a clean, entertaining short-form video script.

OP:
{op_text}

REPLIES:
{replies_block}

TASKS:
1. Select 2 to 5 replies that ADD value — funny reactions, escalating drama, unexpected twists, or a satisfying punchline. Skip low-effort replies ("lol", "same", single words).
2. Censor ALL profanity: replace the ENTIRE word with only its first letter (e.g. "fucking" → "f", "shit" → "s"). Never use asterisks. Catch plural/past-tense variants too.
3. Fix obvious typos but keep the original voice and humor intact.
4. Make sure the sequence reads like a short story from top to bottom.

Return ONLY valid JSON:
{{
  "op_censored": "<cleaned OP>",
  "selected_replies": [
    {{"id": <int>, "censored_text": "<cleaned text>"}}
  ]
}}"""

    print("  [Editor] Curating script…")
    data = _call_ollama(prompt, model)

    if data is None:
        return None

    # Enforce hard limits
    replies = data.get("selected_replies", [])
    if len(replies) > 5:
        data["selected_replies"] = replies[:5]

    # Validate reply IDs
    valid_ids = {r["id"] for r in replies_data}
    data["selected_replies"] = [
        r for r in data["selected_replies"]
        if isinstance(r.get("id"), int) and r["id"] in valid_ids
        and r.get("censored_text", "").strip()
    ]

    return data


def scout_best_thread_stream(threads_data: list, model: str = None):
    """
    Streaming version of scout_best_thread with two-pass Multi-Scouting.
    Yields ("chunk", text) and finally ("result", dict) or ("error", str).
    """
    if not threads_data:
        yield ("error", "No threads provided.")
        return

    cfg_model, cfg_temp = get_llm_settings()
    model = model or cfg_model

    # ── Pass 1: Score all threads ──
    yield ("chunk", "\\n[Pass 1] Generating initial Dankness Leaderboard...\\n\\n")
    context_p1 = "\\n".join(
        f"ID:{t['id']} | REPLIES:{t['replies']}\\n{t['text'][:500]}..."
        for t in threads_data
    )

    prompt_p1 = f"""You are a YouTube Shorts producer auditing 4chan threads for viral potential.
Review the threads below and score EACH ONE out of 10.

THREADS:
{context_p1}

CRITERIA:
10/10: Incredible hook, hilarious, clear conflict/story, pure dankness or a weird question for the audience that is not racist, hateful or offensive.
1/10: Boring, overly political, hateful, offensive.

Return ONLY valid JSON:
{{
  "scores": [
    {{"id": <int>, "score": <float>, "hook": "<1-sentence summary>"}}
  ]
}}"""

    try:
        response_p1 = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt_p1}],
            format="json",
            options={"temperature": cfg_temp},
            stream=True
        )
        
        full_text_p1 = ""
        for chunk in response_p1:
            content = chunk['message']['content']
            full_text_p1 += content
            yield ("chunk", content)
            
        raw_p1 = re.sub(r"```(?:json)?\\s*|\\s*```", "", full_text_p1).strip()
        data_p1 = json.loads(raw_p1)
        
        scores = data_p1.get("scores", [])
        if not scores:
            yield ("error", "Pass 1 failed to score threads.")
            return

        # Sort and get top 3
        scores.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_candidates = scores[:3]
        
        yield ("chunk", "\\n\\n[Pass 2] Deep analysis of Top 3 candidates...\\n\\n")
        
        # ── Pass 2: Deep Analysis ──
        valid_ids = {t["id"]: t for t in threads_data}
        context_p2 = "\\n\\n".join(
            f"ID:{c['id']} | PREV_SCORE:{c.get('score')} | REPLIES:{valid_ids[c['id']]['replies']}\\n{valid_ids[c['id']]['text']}"
            for c in top_candidates if c["id"] in valid_ids
        )
        
        prompt_p2 = f"""Out of the following top contenders, pick the ABSOLUTE BEST thread for a viral video.

Contenders:
{context_p2}

Return ONLY valid JSON:
{{
  "selected_thread_id": <int>,
  "reason": "<detailed reason why this beats the others>",
  "preview": "<2-sentence teaser hook for the video>"
}}"""

        response_p2 = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt_p2}],
            format="json",
            options={"temperature": cfg_temp},
            stream=True
        )

        full_text_p2 = ""
        for chunk in response_p2:
            content = chunk['message']['content']
            full_text_p2 += content
            yield ("chunk", content)

        raw_p2 = re.sub(r"```(?:json)?\\s*|\\s*```", "", full_text_p2).strip()
        data_p2 = json.loads(raw_p2)
        
        best_id = data_p2.get("selected_thread_id")
        
        if best_id not in valid_ids:
            best_id = top_candidates[0]["id"] if top_candidates else None
            
        leaderboard = [
            {"id": c["id"], "score": c.get("score", 0), "hook": c.get("hook", "")}
            for c in scores if c["id"] in valid_ids
        ]

        yield ("result", {
            "best_id": best_id,
            "reason": data_p2.get("reason", "Highest rated overall."),
            "preview": data_p2.get("preview", ""),
            "leaderboard": leaderboard
        })

    except json.JSONDecodeError as e:
        yield ("error", f"JSON parse error: {e}")
    except Exception as e:
        yield ("error", str(e))



def curate_and_censor_thread_stream(op_text: str, replies_data: list, model: str = None):
    """
    Streaming version of curate_and_censor_thread.
    """
    replies_block = "\n".join(f"ID {r['id']}: {r['text']}" for r in replies_data)

    prompt = f"""You are a script editor for a viral YouTube Shorts channel. Edit the thread below into a clean, entertaining short-form video script.

OP:
{op_text}

REPLIES:
{replies_block}

TASKS:
1. Select 2 to 5 replies that ADD value — funny reactions, escalating drama, unexpected twists, or a satisfying punchline. Skip low-effort replies ("lol", "same", single words).
2. Censor ALL profanity: replace the ENTIRE word with only its first letter (e.g. "fucking" → "f", "shit" → "s"). Never use asterisks. Catch plural/past-tense variants too.
3. Fix obvious typos but keep the original voice and humor intact.
4. Make sure the sequence reads like a short story from top to bottom.

Return ONLY valid JSON:
{{
  "op_censored": "<cleaned OP>",
  "selected_replies": [
    {{"id": <int>, "censored_text": "<cleaned text>"}}
  ]
}}"""

    print("  [Editor] Curating script (streaming)…")
    cfg_model, cfg_temp = get_llm_settings()
    model = model or cfg_model
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": cfg_temp},
            stream=True
        )
        
        full_text = ""
        for chunk in response:
            content = chunk['message']['content']
            full_text += content
            yield ("chunk", content)
            
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", full_text).strip()
        data = json.loads(raw)
        
        replies = data.get("selected_replies", [])
        if len(replies) > 5:
            data["selected_replies"] = replies[:5]

        valid_ids = {r["id"] for r in replies_data}
        data["selected_replies"] = [
            r for r in data["selected_replies"]
            if isinstance(r.get("id"), int) and r["id"] in valid_ids
            and r.get("censored_text", "").strip()
        ]
        
        yield ("result", data)
    except Exception as e:
        yield ("error", str(e))
