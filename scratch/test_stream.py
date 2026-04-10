import ollama

def stream_test():
    prompt = "Reply with a simple JSON object having properties a and b."
    response = ollama.chat(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": prompt}],
        format="json",
        stream=True
    )
    for chunk in response:
        print(chunk['message']['content'], end='', flush=True)

if __name__ == "__main__":
    stream_test()
