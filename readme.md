# 🎬 Auto-Chan Studio: Autonomous 4chan Video Producer

> An intelligent, fully-automated pipeline and Web GUI that turns 4chan threads into highly engaging, YouTube Shorts and TikTok-ready videos using local AI.

Auto-Chan isn't just a scraper; it's an **AI Agent**. It browses 4chan boards, scouts for entertaining threads, uses a local LLM to curate and censor the script, takes high-resolution mobile-formatted screenshots, generates AI voiceovers, and edits the final video together—all while you sit back and watch.

---

## ✨ Features

* 🕸️ **Modern Web GUI:** A premium React/Vite frontend for scouting threads, managing a paginated review workflow, and triggering renders.
* 🤖 **Local AI Curation:** Uses Ollama and a multi-pass LLM scouting algorithm to read threads, evaluate comedic/dank potential, and build a narrative script.
* 🛡️ **Smart Censorship:** Automatically detects profanity/slurs and censors them in text-to-speech *and* visually injects them into the HTML before screenshotting to keep your channel monetizable.
* 📱 **Mobile-Optimized Assets:** Uses Playwright to inject premium, dark-mode CSS and capture perfectly padded, 1080x1920 friendly screenshot cards.
* 🎙️ **High-Quality TTS:** Powered by `edge-tts` for natural-sounding, TikTok-style narration.
* 🎥 **Live Streaming Pipeline:** Real-time video rendering logs via Server-Sent Events (SSE) and progress bars in the GUI.
* 🌙 **Night-Shift Batch Rendering:** Robust asynchronous batch pipeline for rendering multiple videos automatically overnight.
* 🚀 **Auto YouTube Uploads:** Automatic video uploading to YouTube using OAuth 2.0.

---

## 🛠️ Prerequisites

Before you start, you need a few things installed on your machine:

1. **Python 3.8+**
2. **Node.js 18+** (For the frontend Web GUI)
3. **[Ollama](https://ollama.com/)** (For running the local AI model)
4. **A Background Video:** You will need some satisfying background footage (e.g., Minecraft Parkour, GTA V racing). It should be a 9:16 vertical video.

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/sudhanshu5669/4Chan-to-Video-Maker.git
cd 4Chan-to-Video-Maker
```

### 2. Set Up the Backend
It's best practice to keep your Python packages isolated.
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

Install the required libraries:
```bash
pip install -r requirements.txt
# (Optional) If you run into missing imports, you might also need: fastapi uvicorn pydantic python-multipart moviepy playwright edge-tts ollama google-api-python-client google-auth-oauthlib google-auth-httplib2
```

Install Playwright Browsers (needed to take perfectly styled screenshots):
```bash
playwright install chromium
```

### 3. Set Up the Frontend
Open a new terminal window, navigate to the `frontend` folder, and install NPM packages:
```bash
cd frontend
npm install
```

### 4. Download the Local LLM via Ollama
Ensure Ollama is running on your machine, then pull the model we use for scouting and script editing:
```bash
ollama pull blaifa/InternVL3_5:8b
# Or run whatever model is specified in your backend/config.py
```

### 5. Add Your Background Assets
Create a folder named `assets` in the `backend/` directory (if it doesn't already exist):
- Put your `.mp4` background gameplay videos inside `backend/assets/`.
- Put any background music files (`.mp3`) inside `backend/assets/music/`.

---

## 📺 YouTube Auto-Upload Setup

Auto-Chan Studio can automatically upload your rendered Shorts to YouTube via the YouTube Data API.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project and enable the **YouTube Data API v3**.
3. Create **OAuth 2.0 Client IDs** credentials (choose "Desktop app" or "Web application", allowing localhost).
4. Download the JSON file and save it as `client_secrets.json` inside the `backend/` directory.
5. The *first time* you upload a video (either through the GUI or CLI), a Google login window will open in your browser asking for permission.
6. Once authorized, it will save a `token.json` file in your `backend/` folder. From then on, uploads will be fully autonomous!

---

## 🕹️ How to Run Auto-Chan Studio

Auto-Chan Studio features two ways to run: the premium **Web GUI** or the classic **CLI**.

### Method A: Web GUI (Recommended)

1. Start the FastAPI backend server (from the inside backend folder):
```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

2. Start the Frontend dev server (from the frontend folder):
```bash
cd frontend
npm run dev
```

3. Open your browser and navigate to the local URL provided by Vite (usually `http://localhost:5173`).

### Method B: CLI Mode

If you prefer the classic terminal interface:
```bash
cd backend
python main.py
```
* **Manual Mode:** You paste the thread ID, it builds the video.
* **Auto Mode:** The AI acts as a solo agent, picks a thread, renders it, and optionally uploads.
* **Review Mode:** The AI suggests threads and allows you to curate the LLM script before rendering.

---

## 📂 Project Architecture

```text
auto-chan-producer/
├── backend/
│   ├── assets/              # Put your 'background.mp4' / 'music.mp3' here!
│   ├── temp/                # Temp audio files and playwright snapshots
│   ├── output/              # Your finished `.mp4` videos ready to go viral
│   ├── server.py            # FastAPI Web Server & SSE Streaming endpoints
│   ├── main.py              # CLI interactive alternative
│   ├── llm.py               # Mult-pass Scout AI & Censor/Editor AI
│   ├── batch.py             # Asynchronous offline batch rendering engine
│   ├── Uploader.py          # Google / YouTube Data APIs v3 Integration
│   ├── client_secrets.json  # (User provided) YouTube API credentials
│   ├── token.json           # (Auto generated) Session keys for YouTube
│   └── ...                  # Video/scraper/TTS logic
├── frontend/
│   ├── src/                 # React components (Studio interface, Review mode, Pipeline logs)
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite app config
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## ⚠️ Disclaimer & API Etiquette

* **Content Warning:** 4chan is unmoderated and unpredictable. While the LLM filters out extreme hate speech, AI is not perfect. **Always review your videos before uploading**.
* **Intended Use:** This tool is for educational purposes, Python/JS web-scraping practice, and automated video editing workflows. Ensure you respect 4chan's API limits (1 request per second max, built into the scraper).