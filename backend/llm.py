import ollama
import json
import re

def scout_best_thread(threads_data, model="blaifa/InternVL3_5:8b"):
    context = ""
    for t in threads_data:
        context += f"Thread ID: {t['id']} | Replies: {t['replies']}\nText: {t['text']}\n{'-'*30}\n"
        
    prompt = f"""
You are an ELITE viral content strategist for a YouTube Shorts channel.

Your job is NOT to find "good" threads.
Your job is to find threads that people will STOP SCROLLING for.

You are selecting content that maximizes:
👉 Attention
👉 Retention
👉 Shareability

━━━━━━━━━━━━━━━━━━━━━━━
📥 THREADS
━━━━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━━━━
🎯 CORE OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━
Select EXACTLY ONE thread that has the HIGHEST chance of going viral.

If none are strong → return null.

━━━━━━━━━━━━━━━━━━━━━━━
🧠 VIRAL THINKING MODEL (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━
For EACH thread, internally evaluate:

1. SCROLL-STOPPING HOOK (0–10)
   - Would this make someone pause instantly?

2. ENTERTAINMENT / FUN (0–10)
   - Is it funny, chaotic, awkward, or shocking?

3. RELATABILITY (0–10)
   - Can a wide audience connect to this?

4. CURIOSITY LOOP (0–10)
   - Does it create “what happens next?” energy?

5. PAYOFF STRENGTH (0–10) ⚠️ CRITICAL
   - Is there a satisfying, funny, or surprising outcome?

6. MEME POTENTIAL (0–10)
   - Could this become a clip people share?

7. LENGTH QUALITY (0–10)
   - Is it concise but still meaningful?

Pick the thread with the BEST COMBINATION.

⚠️ Do NOT explain scoring.

━━━━━━━━━━━━━━━━━━━━━━━
🔥 VIRAL PRIORITY RULES
━━━━━━━━━━━━━━━━━━━━━━━
You are optimizing for:

1. “Would I watch this till the end?”
2. “Would I send this to a friend?”
3. “Would this work as a 30–60 sec video?”

If the answer is NO → reject it.

━━━━━━━━━━━━━━━━━━━━━━━
💥 WHAT MAKES CONTENT VIRAL
━━━━━━━━━━━━━━━━━━━━━━━
Strong candidates usually include:

- Awkward/cringe real-life situations
- Relationship drama or misunderstandings
- Socially relatable problems
- Unexpected twists or reveals
- Chaotic or escalating stories
- Absurd or stupidly funny situations
- Confessions or “I messed up” moments

BONUS:
- Replies that make it funnier

━━━━━━━━━━━━━━━━━━━━━━━
📏 LENGTH LOGIC (OPTIMIZED)
━━━━━━━━━━━━━━━━━━━━━━━
- IDEAL: Medium-length (enough story, not overwhelming)
- OK: Slightly longer IF very engaging
- BAD:
  • Too short → no substance
  • Too long → kills retention

Golden Rule:
👉 “Short ≠ good. Entertaining = good.”

━━━━━━━━━━━━━━━━━━━━━━━
❌ HARD REJECTION RULES
━━━━━━━━━━━━━━━━━━━━━━━
REJECT if:
- Boring, even if short
- No clear situation or story
- Just a plain question
- No payoff or punchline
- Political / hateful / illegal focus
- Requires too much context to understand

━━━━━━━━━━━━━━━━━━━━━━━
⚖️ FINAL DECISION
━━━━━━━━━━━━━━━━━━━━━━━
Pick the thread that:
- Is MOST entertaining
- Has a CLEAR situation
- Has a STRONG payoff
- Feels like a complete short-form story

━━━━━━━━━━━━━━━━━━━━━━━
🧾 OUTPUT RULES (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━
Respond ONLY in valid JSON.

If a strong thread exists:
{{ 
  "selected_thread_id": <thread_id>, 
  "reason": "<Explain why this would go viral (hook + relatability + payoff)>",
  "full_preview": "<Rewrite into a HIGH-HOOK 2-4 sentence script intro that grabs attention instantly>"
}}

If none qualify:
{{ 
  "selected_thread_id": null, 
  "reason": "None of the threads are engaging enough to go viral.",
  "full_preview": "" 
}}
"""
    
    print("[LLM Scout] Scanning for high-quality content...")
    try:
        response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}], format='json')
        data = json.loads(re.sub(r'```json\n?|```\n?', '', response['message']['content']).strip())
        return data.get("selected_thread_id"), data.get("reason"), data.get("full_preview")
    except:
        return None, "Error in LLM response", ""

# (Keep your curate_and_censor_thread function here as well)

def curate_and_censor_thread(op_text, replies_data, model="blaifa/InternVL3_5:8b"):
    """Your existing Editor function."""
    replies_context = "\n".join([f"ID {r['id']}: {r['text']}" for r in replies_data])
    
    prompt = f"""
You are a senior content director and script editor for a viral YouTube Shorts channel.

Your job is to transform a raw 4chan thread into a CLEAN, ENGAGING, and NARRATIVE-DRIVEN short-form video script.

━━━━━━━━━━━━━━━━━━━━━━━
📥 INPUT
━━━━━━━━━━━━━━━━━━━━━━━
ORIGINAL POST (OP):
"{op_text}"

REPLIES:
{replies_context}

━━━━━━━━━━━━━━━━━━━━━━━
🎯 OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━
Create a SHORT, ENTERTAINING STORY using the OP and the BEST replies.

━━━━━━━━━━━━━━━━━━━━━━━
🧠 SELECTION STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━
- Select 1 to 5 replies MAX
- Replies MUST:
  • Add humor, escalation, or payoff
  • Build on the OP (not random comments)
  • Improve storytelling flow

Preferred reply types:
- Funny reactions
- Unexpected twists
- Smart comebacks
- Continuations of the story

Avoid:
- Repetitive replies
- Low-effort responses ("lol", "this", etc.)
- Anything confusing without context

━━━━━━━━━━━━━━━━━━━━━━━
🚫 STRICT CONTENT FILTER
━━━━━━━━━━━━━━━━━━━━━━━
DO NOT include:
- Racism, hate speech, or slurs
- Encouragement of illegal acts
- Extreme toxicity without entertainment value

If a reply is good BUT contains bad content → CLEAN IT via censorship

━━━━━━━━━━━━━━━━━━━━━━━
✂️ CENSORING RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━
You MUST aggressively censor ALL profanity and flagged words.

Rules:
- Replace the ENTIRE offensive word with ONLY its FIRST LETTER
  Examples:
  "fucking" → "f"
  "shit" → "s"
  "bitch" → "b"
  "asshole" → "a"

- DO NOT use asterisks (*) under ANY circumstance
- DO NOT partially censor (e.g., "f***" is WRONG)
- Catch ALL variations (tense, plural, slang, etc.)

━━━━━━━━━━━━━━━━━━━━━━━
🎬 OUTPUT STYLE
━━━━━━━━━━━━━━━━━━━━━━━
- Keep text natural and conversational
- Slightly clean grammar if needed (but DO NOT rewrite heavily)
- Preserve original humor and tone
- Make it flow like a short story when read top-to-bottom

━━━━━━━━━━━━━━━━━━━━━━━
🧾 OUTPUT FORMAT (STRICT JSON)
━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON:

{{
  "op_censored": "<cleaned OP text>",
  "selected_replies": [
    {{
      "id": <reply_id>,
      "censored_text": "<cleaned reply text>"
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ FINAL RULES
━━━━━━━━━━━━━━━━━━━━━━━
- MAX 5 replies (hard limit)
- Ensure the final sequence feels like a cohesive mini-story
- If no good replies exist, return an empty list for selected_replies
- DO NOT include anything outside JSON
"""
    
    print("\n[LLM Editor] Building script and censoring bad words...")
    response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}], format='json')
    
    raw_response = response['message']['content']
    raw_response = re.sub(r'```json\n?', '', raw_response)
    raw_response = re.sub(r'```\n?', '', raw_response)
    
    try:
        curated_data = json.loads(raw_response.strip())
        if len(curated_data.get("selected_replies", [])) > 5:
            curated_data["selected_replies"] = curated_data["selected_replies"][:5]
        return curated_data
    except json.JSONDecodeError:
        return None