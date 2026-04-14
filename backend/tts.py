import os
import re
import subprocess
from config import load_config

def generate_tts(text: str, output_path: str, voice: str = "en-US-ChristopherNeural", rate: str = "+15%"):
    config = load_config()
    censor_mode = config.get("censor_mode", "mute") # fallback
    
    # Standard fallback: remove inner censor content for audio (e.g. s<censor>hit</censor> -> s)
    clean_text = re.sub(r'<censor>(.*?)</censor>', r'', text)
    clean_text = re.sub(r'<pause=.*?s>', '', clean_text)
    
    command = [
        "edge-tts",
        "--voice", voice,
        "--rate", rate,
        "--text", clean_text,
        "--write-media", output_path,
    ]
    subprocess.run(command, check=False, capture_output=True)