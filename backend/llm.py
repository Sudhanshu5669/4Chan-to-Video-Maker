import ollama
import json
import re
import time

# Change this to any model you have pulled locally.
# llama3.1:8b or mistral:7b handle JSON instructions far better than vision models for text tasks.
DEFAULT_MODEL = "llama3.1:8b"


def _call_ollama(prompt: str, model: str, retries: int = 3) -> dict | None:
    """Calls ollama with retry logic and robust JSON extraction."""
    for attempt in range(1, retries + 1):
        try:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                options={"temperature": 0.3},   # lower temp = more consistent JSON
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


def scout_best_thread(threads_data: list, model: str = DEFAULT_MODEL):
    """
    Picks the single best thread for a viral YouTube Short.
    Returns (thread_id | None, reason: str, preview: str).
    """
    context = "\n".join(
        f"ID:{t['id']} REPLIES:{t['replies']}\n{t['text']}"
        for t in threads_data
    )

    prompt = f"""You are a YouTube Shorts producer. Pick ONE thread below that would make the most viral 30-60 second video.

THREADS:
{context}

VIRAL CRITERIA (score each internally, pick highest total):
- Strong hook: does the opening line grab attention instantly?
- Clear situation: is there an actual story, conflict, or scenario?
- Emotional reaction: funny, shocking, relatable, or cringe?
- Payoff: is there a satisfying punchline or twist?
- Broad appeal: would a general audience (not just 4chan users) get it?

REJECT if:
- No clear story or situation
- Requires niche knowledge to understand
- Hateful, political rant, or illegal content as the main focus
- Just a question with no drama or humor

Return ONLY valid JSON, no commentary:
{{
  "selected_thread_id": <integer id or null>,
  "reason": "<one sentence: why this will go viral>",
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


def curate_and_censor_thread(op_text: str, replies_data: list, model: str = DEFAULT_MODEL) -> dict | None:
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