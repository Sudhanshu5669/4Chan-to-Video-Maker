import subprocess


def generate_tts(text: str, output_path: str, voice: str = "en-US-ChristopherNeural", rate: str = "+15%"):
    """
    Generates TTS using edge-tts CLI.
    Christopher = natural-sounding male narrator, good for short-form content.
    Other good options: en-US-GuyNeural, en-GB-RyanNeural

    Rate controls narration speed:
      '+20%' = 20% faster, '-10%' = 10% slower, '+0%' = default speed.
    Default is +15% to avoid the sluggish default pace.
    """
    command = [
        "edge-tts",
        "--voice", voice,
        "--rate", rate,
        "--text", text,
        "--write-media", output_path,
    ]
    subprocess.run(command, check=True, capture_output=True)