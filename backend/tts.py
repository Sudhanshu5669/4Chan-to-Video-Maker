import subprocess


def generate_tts(text: str, output_path: str, voice: str = "en-US-ChristopherNeural"):
    """
    Generates TTS using edge-tts CLI.
    Christopher = natural-sounding male narrator, good for short-form content.
    Other good options: en-US-GuyNeural, en-GB-RyanNeural
    """
    command = [
        "edge-tts",
        "--voice", voice,
        "--text", text,
        "--write-media", output_path,
    ]
    subprocess.run(command, check=True, capture_output=True)