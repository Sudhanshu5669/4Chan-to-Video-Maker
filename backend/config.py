import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

def load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        os.environ[k.strip()] = v.strip(' "\'')

load_env()

DEFAULT_CONFIG = {
    "llm_model": "llama3.1:8b",
    "llm_temperature": 0.3,
    "tts_voice": "en-US-ChristopherNeural",
    "tts_rate": "+15%",
    "max_replies": 5,
    "video_fps": 30,
    "video_preset": "fast",
    "llm_provider": "ollama",
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "censor_mode": "beep",
    "ken_burns": False
}


def load_config():
    """Load config from disk, merged with defaults for any missing keys."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            return {**DEFAULT_CONFIG, **saved}
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Persist config to disk."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    return config


def update_config(updates: dict):
    """Merge updates into existing config and save."""
    config = load_config()
    config.update(updates)
    return save_config(config)
