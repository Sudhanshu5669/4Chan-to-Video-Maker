import subprocess

def generate_tts(text, output_path, voice="en-US-ChristopherNeural"):
    # Using subprocess to call edge-tts CLI (easiest way to handle it synchronously)
    # Christopher is a popular, natural-sounding male narrator voice.
    command = [
        "edge-tts", 
        "--voice", voice, 
        "--text", text, 
        "--write-media", output_path
    ]
    subprocess.run(command, check=True)