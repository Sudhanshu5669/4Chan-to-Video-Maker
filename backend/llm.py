import ollama
import json
import re

def scout_best_thread(threads_data, model="blaifa/InternVL3_5:8b"):
    """
    Acts as a scout. Reads a list of thread previews and picks the most entertaining one.
    Returns the thread ID, or None if they are all boring.
    """
    
    context = ""
    for t in threads_data:
        context += f"Thread ID: {t['id']} | Replies: {t['replies']}\nText: {t['text']}\n{'-'*30}\n"
        
    prompt = f"""
    You are a viral content scout for a YouTube channel. 
    Review these 4chan thread previews:
    
    {context}
    
    Your task:
    Select the ONE thread that would make the most entertaining, funny, or interesting video. 
    Look for engaging stories, funny questions, or high reply counts. 
    DO NOT select heavily political, racist, or illegal threads.
    
    If NONE of these threads are good enough to make a video, return null for the ID.
    
    You MUST respond ONLY in valid JSON format.
    Example if you find a good thread:
    {{ "selected_thread_id": 12345678, "reason": "This story about a bad date is hilarious." }}
    
    Example if they are all bad:
    {{ "selected_thread_id": null, "reason": "All of these are boring or overly offensive." }}
    """
    
    print("[LLM Scout] Scanning page for viral content...")
    response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}], format='json')
    
    raw_response = response['message']['content']
    raw_response = re.sub(r'```json\n?', '', raw_response)
    raw_response = re.sub(r'```\n?', '', raw_response)
    
    try:
        data = json.loads(raw_response.strip())
        return data.get("selected_thread_id"), data.get("reason")
    except json.JSONDecodeError:
        return None, "LLM failed to format output."

def curate_and_censor_thread(op_text, replies_data, model="blaifa/InternVL3_5:8b"):
    """Your existing Editor function."""
    replies_context = "\n".join([f"ID {r['id']}: {r['text']}" for r in replies_data])
    
    prompt = f"""
    You are an expert content director for a viral YouTube Shorts channel. 
    Here is the OP: "{op_text}"
    Here are the replies:
    {replies_context}
    
    1. Select 1 to 5 best replies to feature.
    2. Choose replies that are entertaining and build a narrative.
    3. CENSOR profanity and slurs using asterisks (e.g., f***).
    
    Respond ONLY in valid JSON:
    {{ "op_censored": "Clean text", "selected_replies": [ {{"id": 123, "censored_text": "clean reply"}} ] }}
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