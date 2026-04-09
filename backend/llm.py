import ollama
import json

def curate_and_censor_thread(op_text, replies_data, model="blaifa/InternVL3_5:8b"):
    """
    Feeds the OP and replies to Ollama, asking it to pick the best ones and censor them.
    replies_data should be a list of dicts: [{"id": 123, "text": "..."}]
    """
    
    # We construct a numbered list of replies for the LLM to read
    replies_context = "\n".join([f"ID {r['id']}: {r['text']}" for r in replies_data])
    
    prompt = f"""
    You are a content curator for a YouTube Shorts channel. 
    Here is the Original Post (OP) of a 4chan thread:
    "{op_text}"
    
    Here are the top replies:
    {replies_context}
    
    Task:
    1. Select the 2 to 3 most entertaining, relevant, or funny replies.
    2. Completely CENSOR any profanity, slurs, or highly offensive words using asterisks (e.g., f***, s***). 
    3. Censor the OP text as well if needed.
    
    You MUST respond ONLY in valid JSON format. Do not include markdown code blocks, just the JSON.
    The JSON must be an object with two keys: "op_censored" (string) and "selected_replies" (array of objects).
    Each object in the array must have "id" (integer) and "censored_text" (string).
    
    Example output:
    {{
        "op_censored": "This is a clean post.",
        "selected_replies": [
            {{"id": 12345, "censored_text": "That is a crazy story, what the f***!"}}
        ]
    }}
    """
    
    print("\n[LLM] Thinking... (Evaluating and censoring content)")
    
    response = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        format='json' # This forces Ollama to return a JSON string
    )
    
    raw_response = response['message']['content']
    
    try:
        curated_data = json.loads(raw_response)
        return curated_data
    except json.JSONDecodeError:
        print("Error: The LLM failed to output valid JSON. Try a different model or run it again.")
        print("Raw Output:", raw_response)
        return None