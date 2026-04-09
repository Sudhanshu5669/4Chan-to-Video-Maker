Here is a comprehensive, visually appealing, and human-written `README.md` for your repository. You can copy and paste this directly into your GitHub repo.

***

# 🎬 Auto-Chan: Autonomous 4chan Video Producer

> An intelligent, fully-automated pipeline that turns 4chan threads into highly engaging, YouTube Shorts and TikTok-ready videos using local AI.

Auto-Chan isn't just a scraper; it's an **AI Agent**. It browses 4chan boards, scouts for entertaining threads, uses a local LLM to curate and censor the script, takes high-resolution mobile-formatted screenshots, generates AI voiceovers, and edits the final video together—all while you sit back and watch.

---

## ✨ Features

* 🤖 **Local AI Curation:** Uses Ollama to read threads, select the funniest/best replies, and build a narrative script.
* 🛡️ **Smart Censorship:** Automatically detects profanity/slurs and censors them in the text-to-speech *and* visually injects the censored text into the HTML before screenshotting to keep your channel monetizable.
* 📱 **Mobile-Optimized Assets:** Uses Playwright to inject premium, dark-mode CSS and capture perfectly padded, 1080x1920 friendly screenshot cards.
* 🎙️ **High-Quality TTS:** Powered by `edge-tts` for natural-sounding, TikTok-style narration.
* 🎛️ **Three Operating Modes:**
  1. **Manual:** You pick the thread, it does the rest.
  2. **Full Auto:** The AI scouts the board, picks the thread, and renders the video while you sleep.
  3. **Executive Producer (Review):** The AI scouts and builds the script, but asks for your final approval on every reply before rendering.

---

## 🛠️ Prerequisites

Before you start, you need a few things installed on your machine:

1. **Python 3.8+**
2. **[Ollama](https://ollama.com/)** (For running the local AI model)
3. **A Background Video:** You will need some satisfying background footage (e.g., Minecraft Parkour, GTA V racing). It should be a 9:16 vertical video.

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/auto-chan-producer.git
cd auto-chan-producer
```

### 2. Set Up a Virtual Environment (Recommended)
It's best practice to keep your Python packages isolated.
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Python Dependencies
Install the required libraries (Requests, BeautifulSoup, MoviePy, Playwright, etc.).
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
Playwright needs its own headless Chromium browser to take the screenshots.
```bash
playwright install chromium
```

### 5. Download the Local LLM via Ollama
Ensure Ollama is running on your machine, then pull the model we use for scouting and script editing.
```bash
ollama pull blaifa/InternVL3_5:8b
```
*(Note: If you want to use a different model like `llama3`, just update the `model=` parameter inside `llm.py`).*

### 6. Add Your Background Video
Create a folder named `assets` in the root directory (if it doesn't exist) and place your background gameplay video inside it.
**You must name the file exactly:** `background.mp4`.

---

## 🕹️ How to Use

Simply run the main script. The interactive terminal will guide you through the rest.

```bash
python main.py
```

### The 3 Modes Explained:
* **Mode 1 (Manual):** The script will print the live catalog of your chosen board. You type the Thread ID you want, and it generates the video.
* **Mode 2 (Auto):** Walk away from your keyboard. The AI will read the catalog, find a thread it deems "entertaining," filter out the garbage, and render the `.mp4`.
* **Mode 3 (Review):** The hybrid approach. The AI suggests a thread and shows you a preview. If you say yes, it builds a script and asks you to approve/reject the replies it chose to ensure perfect comedic pacing.

---

## 📂 Project Structure

```text
auto-chan-producer/
│
├── assets/                  # Put your 'background.mp4' here!
├── output/                  # Your finished, ready-to-upload videos appear here
├── temp/                    # Temporary audio files and raw screenshots 
│
├── main.py                  # The master script and interactive terminal UI
├── llm.py                   # The "AI Brain" - handles scouting and censoring via Ollama
├── scraper.py               # Handles the 4chan API, fetching boards, and cleaning raw HTML
├── screenshot.py            # Playwright engine: injects custom CSS, censors DOM, takes pics
├── tts.py                   # Handles text-to-speech generation via Edge TTS
├── video.py                 # MoviePy engine: stitches audio, images, and background together
│
└── requirements.txt         # Python dependencies
```

---

## 🧠 How It Works Under the Hood

1. **The Scout:** Uses the `4chan /catalog.json` API to pull the top active threads. It feeds these to the local LLM to evaluate for entertainment value and safety.
2. **The Editor:** Once a thread is picked, the API fetches the top 20 replies. The LLM acts as an editor, picking the 5 best replies, cutting out boring ones, and replacing profanity with safe alternatives (e.g., "fucking" becomes "f").
3. **The Prop Master:** `screenshot.py` visits the live 4chan thread in a hidden browser. It uses JavaScript to dynamically replace the text on the screen with the LLM's censored text, injects beautiful CSS, hides everything except the target post, and snaps a perfect PNG.
4. **The Assembly:** MoviePy dynamically resizes the screenshots to perfectly fit 85% of your background video's width, syncs the image durations to the TTS audio lengths, loops the background video if necessary, and renders the final `.mp4`.

---

## ⚠️ Disclaimer & API Etiquette

* **Rate Limiting:** This script is designed to respect the 4chan API guidelines (1 request per second). Do not aggressively loop the scraper without delays, or your IP will be temporarily banned by 4chan.
* **Content Warning:** 4chan is unmoderated and highly unpredictable. While the LLM is instructed to filter out hate speech and illegal content, AI is not perfect. **Always review your videos before uploading them to YouTube or TikTok.**
* **Intended Use:** This tool is for educational purposes, Python web-scraping practice, and automated video editing workflows.