import ollama
import json
import re

def curate_and_censor_thread(op_text, replies_data, model="blaifa/InternVL3_5:8b"):
    """
    Feeds the OP and ALL top replies to Ollama, asking it to act as an autonomous editor.
    """
    
    # Construct a numbered list of replies for the LLM to read
    replies_context = "\n".join([f"ID {r['id']}: {r['text']}" for r in replies_data])
    
    prompt = f"""
    You are an expert content director for a viral YouTube Shorts channel. 
    Here is the Original Post (OP) of a 4chan thread:
    "{op_text}"
    
    Here are the replies to that thread:
    {replies_context}
    
    Your exact tasks:
    1. AUTONOMOUSLY SELECT the best replies to feature in the video. You must pick between 1 and 5 replies (MAXIMUM 5).
    2. Choose replies that make the thread entertaining, highly relevant, and build a fun or engaging narrative as the video goes on.
    3. DO NOT select any replies that are hateful, racist, or promote illegal acts.
    4. CENSOR any profanity, slurs, or heavily flagged words (e.g., f***, s***, b****) using asterisks to ensure the video is safe for YouTube monetization. Do this for both the OP text and the selected replies.
    
    You MUST respond ONLY in valid JSON format. Do not include markdown formatting (like ```json), conversational text, or explanations. Just output the raw JSON object.
    
    The JSON must be an object with two keys: "op_censored" (string) and "selected_replies" (array of objects).
    Each object in the array must have "id" (integer) and "censored_text" (string).
    
    Example output format:
    {{
        "op_censored": "This is a clean post about my day.",
        "selected_replies": [
            {{"id": 12345, "censored_text": "That is a crazy story, what the h***!"}},
            {{"id": 12346, "censored_text": "Bro you really messed up this time."}}
        ]
    }}
    """
    
    print("\n[LLM] Analyzing thread and building the script... (This might take a moment)")
    
    response = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        format='json' 
    )
    
    raw_response = response['message']['content']
    
    # Strip markdown code blocks if the LLM stubbornly includes them
    raw_response = re.sub(r'```json\n?', '', raw_response)
    raw_response = re.sub(r'```\n?', '', raw_response)
    
    try:
        curated_data = json.loads(raw_response.strip())
        
        # Failsafe: Ensure it didn't grab more than 5 replies
        if len(curated_data.get("selected_replies", [])) > 5:
            curated_data["selected_replies"] = curated_data["selected_replies"][:5]
            
        return curated_data
    except json.JSONDecodeError:
        print("Error: The LLM failed to output valid JSON.")
        print("Raw Output:", raw_response)
        return None