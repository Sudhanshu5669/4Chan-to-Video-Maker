import ollama
import json
import re

def scout_best_thread(threads_data, model="blaifa/InternVL3_5:8b"):
    context = ""
    for t in threads_data:
        context += f"Thread ID: {t['id']} | Replies: {t['replies']}\nText: {t['text']}\n{'-'*30}\n"
        
    prompt = f"""
    You are a viral content scout for a high-quality YouTube channel. 
    Review these 4chan thread previews:
    {context}
    
    STRICT QUALITY PROTOCOL:
    1. REJECT any threads involving racism, hate speech, illegal acts, or extreme political toxicity.
    2. REJECT "boring" threads like tech support questions or simple "rate my setup" posts.
    3. LOOK FOR: Funny anecdotes, "Greentext" style storytelling, interesting "What if" scenarios, or high-effort hobbyist discussions.
    
    If NONE of these are high quality, return null.
    
    Respond ONLY in JSON:
    {{ "selected_thread_id": 12345, "reason": "Why this is good", "full_preview": "A longer summary of the thread for the user to review" }}
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
    You are an expert content director for a viral YouTube Shorts channel. 
    Here is the OP: "{op_text}"
    Here are the replies:
    {replies_context}
    
    Your exact tasks:
    1. Select 1 to 5 best replies to feature that are entertaining and build a narrative.
    2. DO NOT select any replies that are hateful, racist, or promote illegal acts.
    3. CENSOR profanity, slurs, and highly flagged words in both the OP and replies.
    
    CRITICAL CENSORING RULES:
    - You must catch ALL variations of bad words (e.g., censor "fucked", "fucking", "shit", "bitch", etc.).
    - Replace the bad word with JUST ITS FIRST LETTER (e.g., replace "fucking" with "f", replace "shit" with "s").
    - DO NOT USE ASTERISKS (*). If you use asterisks, the text-to-speech AI will literally say the word "asterisk" out loud, which ruins the video.
    
    Respond ONLY in valid JSON:
    {{ "op_censored": "Clean text", "selected_replies": [ {{"id": 123, "censored_text": "What the f are you talking about?"}} ] }}
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