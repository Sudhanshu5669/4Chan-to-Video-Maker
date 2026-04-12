import os
import re
import subprocess
from config import load_config
import numpy as np

# Try importing moviepy for audio post-processing
try:
    from moviepy.editor import concatenate_audioclips, AudioFileClip, AudioClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False


def make_beep_clip(duration, vol=0.5, freq=1000):
    def make_frame(t):
        # t can be a scalar or an array
        t_arr = np.array(t)
        val = np.sin(2 * np.pi * freq * t_arr) * vol
        if t_arr.ndim == 0:
            return np.array([val, val])
        else:
            return np.vstack([val, val]).T
    return AudioClip(make_frame, duration=duration, fps=44100)

def make_silence_clip(duration):
    def make_frame(t):
        t_arr = np.array(t)
        val = np.zeros_like(t_arr)
        if t_arr.ndim == 0:
            return np.array([val, val])
        else:
            return np.vstack([val, val]).T
    return AudioClip(make_frame, duration=duration, fps=44100)


def generate_tts(text: str, output_path: str, voice: str = "en-US-ChristopherNeural", rate: str = "+15%"):
    config = load_config()
    censor_mode = config.get("censor_mode", "beep") # "beep" or "mute"
    
    # Parse text for <censor>...</censor> and <pause=Xs>
    # Group 1 captures the entire match.
    pattern = r'(<censor>.*?</censor>|<pause=[0-9.]+s>)'
    parts = re.split(pattern, text)
    
    # If no tags or moviepy unavailable, just clean and do it the standard way
    if not np.any([re.search(pattern, p) for p in parts]) or not MOVIEPY_AVAILABLE:
        # Fallback: remove tags
        clean_text = re.sub(r'<censor>(.*?)</censor>', r'', text)
        clean_text = re.sub(r'<pause=.*?s>', '', clean_text)
        command = [
            "edge-tts",
            "--voice", voice,
            "--rate", rate,
            "--text", clean_text,
            "--write-media", output_path,
        ]
        subprocess.run(command, check=True, capture_output=True)
        return

    audioclips_to_concat = []
    temp_files = []
    
    for i, part in enumerate(parts):
        if not part.strip():
            continue
            
        if part.startswith('<censor>'):
            # Replace with beep or mute (0.4s default duration for a curse word)
            dur = 0.4
            if censor_mode == "beep":
                audioclips_to_concat.append(make_beep_clip(dur))
            else:
                audioclips_to_concat.append(make_silence_clip(dur))
                
        elif part.startswith('<pause='):
            # Parse pause duration
            try:
                dur_str = part.replace('<pause=', '').replace('s>', '')
                dur = float(dur_str)
                audioclips_to_concat.append(make_silence_clip(dur))
            except Exception:
                pass
                
        else:
            # Normal text fragment
            temp_path = output_path.replace(".mp3", f"_part{i}.mp3")
            temp_files.append(temp_path)
            # Edge-tts throws error if text is empty or just punctuation
            cleaned = re.sub(r'[^a-zA-Z0-9]+', '', part)
            if not cleaned: 
                continue
            command = [
                "edge-tts",
                "--voice", voice,
                "--rate", rate,
                "--text", part,
                "--write-media", temp_path,
            ]
            subprocess.run(command, check=True, capture_output=True)
            
            if os.path.exists(temp_path):
                audioclips_to_concat.append(AudioFileClip(temp_path))

    if audioclips_to_concat:
        final_audio = concatenate_audioclips(audioclips_to_concat)
        final_audio.write_audiofile(output_path, logger=None)
        
        # Cleanup
        for clip in audioclips_to_concat:
            clip.close()
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
    else:
        # Fallback if somehow empty
        command = [
            "edge-tts", "--voice", voice, "--rate", rate,
            "--text", "error", "--write-media", output_path,
        ]
        subprocess.run(command, capture_output=True)