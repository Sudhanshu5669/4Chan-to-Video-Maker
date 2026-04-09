import ollama
import json
import re

def scout_best_thread(threads_data, model="blaifa/InternVL3_5:8b"):
    context = ""
    for t in threads_data:
        context += f"Thread ID: {t['id']} | Replies: {t['replies']}\nText: {t['text']}\n{'-'*30}\n"
        
    prompt = f"""
You are a senior viral content strategist for a YouTube channel that turns internet threads into highly engaging story videos.

You are NOT just selecting "interesting" content — you are selecting content that can HOLD ATTENTION, GO VIRAL, and be turned into a compelling narrative.

You are given multiple 4chan thread previews:

{context}

━━━━━━━━━━━━━━━━━━━━━━━
🎯 CORE OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━
Select EXACTLY ONE thread that has the HIGHEST potential to become a viral YouTube video.

If none meet the quality bar → return null.

━━━━━━━━━━━━━━━━━━━━━━━
🧠 HOW TO THINK (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━
For EACH thread, internally evaluate:

1. HOOK (0–10): Does it immediately grab attention?
2. STORY (0–10): Is there a clear narrative (setup → conflict → payoff)?
3. ENTERTAINMENT (0–10): Is it funny, shocking, awkward, or dramatic?
4. CURIOSITY (0–10): Does it make people want to know what happens next?
5. ENGAGEMENT SIGNAL (0–10): Reply count + discussion potential

Then pick the thread with the BEST overall combination.

⚠️ Do NOT explain scores. Just use them to decide.

━━━━━━━━━━━━━━━━━━━━━━━
✅ STRONG POSITIVE SIGNALS
━━━━━━━━━━━━━━━━━━━━━━━
- Greentext-style storytelling
- Personal stories (bad dates, cringe moments, disasters, confessions)
- Escalating or chaotic situations
- Unexpected twists or reveals
- Socially relatable or absurd scenarios
- Threads where replies add humor or continuation

━━━━━━━━━━━━━━━━━━━━━━━
❌ HARD REJECTION RULES
━━━━━━━━━━━━━━━━━━━━━━━
IMMEDIATELY REJECT if the thread is:
- Primarily political, ideological, or agenda-driven
- Racist, hateful, or offensive without entertainment value
- Focused on illegal acts in a serious/non-entertaining way
- Low-effort ("rate this", "help me fix this", basic Q&A)
- Too short, vague, or lacking context
- No clear narrative or payoff
- Dead thread (very low replies unless EXTREMELY compelling)

━━━━━━━━━━━━━━━━━━━━━━━
⚖️ DECISION PRIORITY
━━━━━━━━━━━━━━━━━━━━━━━
1. STORY > everything else
2. ENTERTAINMENT > shock value alone
3. RELATABILITY > niche topics
4. HIGH REPLIES = bonus, not requirement

If a thread is funny BUT has no story → reject it.
If a thread has a story BUT weak hook → consider carefully.

━━━━━━━━━━━━━━━━━━━━━━━
🧾 OUTPUT RULES (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━
Respond ONLY in valid JSON.

If a strong thread exists:
{{ 
  "selected_thread_id": <thread_id>, 
  "reason": "<1-2 sentence explanation focusing on viral potential>",
  "full_preview": "<Rewrite the thread into a clean, engaging 2-4 sentence preview that sounds like a YouTube hook>"
}}

If none qualify:
{{ 
  "selected_thread_id": null, 
  "reason": "None of the threads meet the minimum viral storytelling quality.",
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