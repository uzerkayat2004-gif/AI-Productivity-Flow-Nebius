<h1 align="center">🌊 AI Productivity Flow</h1>

<p align="center">
  <b>Turn documents into video, text into audio, and voice into polished text — without switching apps.</b><br>
  <i>A free, open-source desktop AI assistant for Windows and macOS designed to work seamlessly inside your existing workflow.</i>
</p>

<p align="center">
  <a href="https://github.com/uzerkayat2004-gif/AI-Productivity-Flow/releases/latest"><img src="https://img.shields.io/badge/Release-Version%201.0-orange.svg" alt="Release: Version 1.0"></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64%20%7C%20macOS%2014%20Sonoma%2B-0078D4.svg" alt="Platforms">
  <img src="https://img.shields.io/badge/Architecture-Local--first%20%2F%20BYOK-success.svg" alt="Local-first / BYOK">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache-2.0">
  <a href="https://aiproductivityflow.site/"><img src="https://img.shields.io/badge/Website-aiproductivityflow.site-emerald.svg" alt="Official Website"></a>
</p>

<p align="center">
  <img src="docs/assets/ai-productivity-flow-hero-banner.png" alt="AI Productivity Flow Interface Banner" width="920">
</p>

<p align="center">
  <b>🏆 Nebius x NVIDIA Global AI Hackathon edition — Best Apps and Agents track</b><br>
  <i>This repository is the hackathon copy of AI Productivity Flow. It runs the app's AI steps on NVIDIA Nemotron models through Nebius Token Factory. The main app lives at <a href="https://github.com/uzerkayat2004-gif/AI-Productivity-Flow">uzerkayat2004-gif/AI-Productivity-Flow</a>.</i>
</p>

## 🧑‍⚖️ For judges: start here

**What it is.** A desktop AI assistant for Windows and macOS with three tools that work inside any app: **Voice Flow** (speak, and polished text is typed where your cursor is), **Audio Flow** (select text and hear it read or summarised), and **Video Flow** (turn notes into a narrated explainer video).

**What this hackathon edition adds** (all new since Aug 26, 2026):

* **Nebius Token Factory provider.** Add your Token Factory key in the app and pick an NVIDIA Nemotron model. The app makes OpenAI-compatible calls to `https://api.tokenfactory.nebius.com/v1/`. A **Test** button checks the key against `/v1/models`.
* **Nemotron in all three flows.** Pick **Nemotron 3.5 Lightning** or **Nemotron 3 Super 120B** for Voice Flow cleanup and voice commands, Video Flow planning, and Audio Flow summaries. Any other Token Factory model id can be added with **Add Model**.
* **An all-NVIDIA voice pipeline.** Your voice → **Nemotron speech recognition on your own computer** → **Nemotron on Nebius** cleans it up → text typed into your app. The audio never leaves your computer.

**Try it** (Python 3.10 or newer, Windows 10/11 or macOS 14+ on Apple Silicon):

```bash
git clone https://github.com/uzerkayat2004-gif/AI-Productivity-Flow-Nebius.git
cd AI-Productivity-Flow-Nebius
python -m venv .venv
# Windows: .\.venv\Scripts\activate    macOS: source .venv/bin/activate
pip install -e .
voice-flow
```

Then open **Video Flow → API Providers → Nebius Token Factory**, click **Add**, paste your key and click **Test**. Now pick a Nebius Nemotron model in Voice Flow, Audio Flow or Video Flow. You can also install the latest release from the main app; it includes the same Nebius provider.

**More detail:** [docs/HACKATHON_NEBIUS.md](docs/HACKATHON_NEBIUS.md) covers what changed since Aug 26, exactly how Token Factory and Nemotron are used, and the known limits. Tests: `pytest tests/test_nebius_provider.py`.

**Demo video:** _coming soon (YouTube, under 3 minutes)._

---

## ⚡ What is AI Productivity Flow?

AI Productivity Flow is a desktop AI system engineered to operate seamlessly alongside the apps you already use. Instead of copying and pasting text into separate browser windows or siloed AI chat services, Flow stays quietly accessible across your entire operating system.

Select any text, notes, or documentation on screen, or tap a global shortcut to speak naturally:

1. **🎬 Video Flow** — Generate visual explainer videos with narration and synchronized motion graphics.
2. **🎧 Audio Flow** — Read text aloud or listen to structured multi-depth audio summaries.
3. **🎙️ Voice Flow** — Dictate directly into any focused application with instant text injection.

---

## 📥 Downloads & Installation

### Windows 10 & 11 (64-bit)

* **Direct Installer**: Download the standalone installer **[`AI-Productivity-Flow-Setup-x64.exe`](https://github.com/uzerkayat2004-gif/AI-Productivity-Flow/releases/latest/download/AI-Productivity-Flow-Setup-x64.exe)** from the latest stable release.
* **Checksum**: [`AI-Productivity-Flow-Setup-x64.exe.sha256`](https://github.com/uzerkayat2004-gif/AI-Productivity-Flow/releases/latest/download/AI-Productivity-Flow-Setup-x64.exe.sha256)
* **Terminal Install** (PowerShell, per-user, no admin required):
  ```powershell
  irm https://raw.githubusercontent.com/uzerkayat2004-gif/AI-Productivity-Flow/main/scripts/install.ps1 | iex
  ```
* **SmartScreen**: Windows may say it protected your PC. Choose **More info**, then **Run anyway**.
* **Size**: the Windows installer is about **546 MB**. Installed size is about **1.5 GB**.

### macOS 14 Sonoma or later (Apple Silicon only, M1 or newer)

The Mac disk image is about **271 MB**. The zip archive is about **287 MB**.

* **DMG Installer**: Download the drag-to-Applications installer **[`AI-Productivity-Flow-macOS.dmg`](https://github.com/uzerkayat2004-gif/AI-Productivity-Flow/releases/latest/download/AI-Productivity-Flow-macOS.dmg)**.
* **Checksum**: [`AI-Productivity-Flow-macOS.dmg.sha256`](https://github.com/uzerkayat2004-gif/AI-Productivity-Flow/releases/latest/download/AI-Productivity-Flow-macOS.dmg.sha256)
* **Secondary Archive**: [`AI-Productivity-Flow-macOS.zip`](https://github.com/uzerkayat2004-gif/AI-Productivity-Flow/releases/latest/download/AI-Productivity-Flow-macOS.zip) ([SHA-256](https://github.com/uzerkayat2004-gif/AI-Productivity-Flow/releases/latest/download/AI-Productivity-Flow-macOS.zip.sha256))
* **Terminal Install** (Bash / Zsh):
  ```bash
  curl -fsSL https://raw.githubusercontent.com/uzerkayat2004-gif/AI-Productivity-Flow/main/scripts/install.sh | bash
  ```

#### Installing on Mac

The Mac build is Apple Silicon only (M1 or newer); it does not run on Intel Macs. Download links above stay on the latest stable release. On Mac you get all three: Video Flow, Audio Flow and Voice Flow.

1. Open the DMG and drag the app to Applications.
2. The app is not signed yet, so the first time you open it macOS blocks it. On macOS 15 and later, right-click → Open no longer gets past this. Instead:
   1. Open the app once. When macOS says it can't verify the developer, click **Done**.
   2. Go to System Settings → **Privacy & Security** and scroll down to the message about AI Productivity Flow.
   3. Click **Open Anyway**, then confirm (enter your password if asked).
3. Allow **Microphone** when asked.
4. For hotkeys and auto-paste, turn on the app in System Settings → Privacy & Security → **Accessibility** and **Input Monitoring**, then reopen the app.
5. The default dictation shortcut on Mac is **Cmd + Option**.

**After updating on Mac:** when you install a new version, macOS may quietly stop honouring the permissions you gave the old one, so hotkeys or auto-paste stop working. Go to System Settings → Privacy & Security → **Accessibility**, select AI Productivity Flow, remove it with the **minus (−)** button, then add it again with **+** (or switch it off and on). Do the same under **Input Monitoring**, then restart the app.

---

## 🌟 The Three Pillars of Flow

### 1. 🎬 Video Flow — Turn Selected Text into Visual Explainer Videos

Video Flow transforms dense articles, technical notes, or documentation into structured, animated MP4 explainer videos with synchronized voiceover narration.

> **Platform note:** Video Flow works on Windows and macOS (Apple Silicon).

<p align="center">
  <video src="https://github.com/user-attachments/assets/61afd3f3-d75b-4cff-8010-6a7f0d8657a9" controls width="100%"></video>
  <br>
  <sub>🎬 <b><a href="https://aiproductivityflow.site/assets/video/videoflow_demo.mp4">Watch or download Video Flow demo (MP4)</a></b></sub>
</p>

```
Source Text / Notes
       │
       ▼
AI Planning & Concept Extraction (Gemini / OpenAI / Claude / Local)
       │
       ▼
Creative Director & Scene Authoring (Key ideas, visual hierarchy, layout)
       │
       ▼
Controlled Rendering Pipeline (Kinetic typography, diagrammatic cards, transitions)
       │
       ▼
Finished Explainer Video (.mp4 saved to Downloads + in-app player)
```

* **Multi-Engine Rendering Pipeline**: AI understands and plans scene intent; Flow's Creative Director shapes pacing, layout, and visual rhythm; controlled local rendering compiles the final video.
* **Google NotebookLM Integration**: Directly connect NotebookLM research notebooks for audio and visual synthesis.
* **Visual Styles & Themes**: Choose between distinct visual presentations (Dark Editorial, Minimal Technical, Kinetic Modern).
* **Deterministic Fallback**: Local deterministic visual layout engine ensures rendering completes reliably even if external APIs experience rate limits.
* **Export & Control**: Export high-definition MP4 videos directly to your system Downloads folder with playback controls and job management.

### 2. 🎧 Audio Flow — Spoken Readers & Multi-Depth Audio Summaries

Audio Flow gives you two dedicated ways to absorb written content without eye strain:

<p align="center">
  <video src="https://github.com/user-attachments/assets/d1bc3228-548b-43a0-882d-d81665ee20a3" controls width="100%"></video>
  <br>
  <sub>🎧 <b><a href="https://aiproductivityflow.site/assets/video/audioflow_demo.mp4">Watch or download Audio Flow demo (MP4)</a></b></sub>
</p>

* **How to start it**: select text with the mouse in any app, then click the small Listen button that appears next to it (or the floating bar) and pick Read or Summary. On Mac you can also press **Control+Option+L** to read the current selection aloud; press it again to stop. On Mac, reading your selection needs the Accessibility permission.
* **Read Mode (Spoken Explainer)**: An intelligent reader designed to articulate selected paragraphs, articles, or documentation naturally. Rather than robotic text playback, it speaks with natural human cadence, clear phrasing, and synchronized playback.
* **Summary Mode (Multi-Depth Audio Summaries)**:
  * **Short**: Fast high-level briefs for quick updates.
  * **Balanced**: Structured conceptual overviews capturing key arguments and takeaways.
  * **Deep Dive**: Thorough breakdown analyzing context, evidence, and implications for long documents.
* **Integrated Audio Player**: Mini on-screen and full-window player with playback rate controls (0.75x to 2.0x), waveform progress scrubbing, and instant MP3 download.
* **Voice Ecosystem**: The default voice is Microsoft Edge's online text-to-speech (free, no account required). It runs online, so the text being read is sent to Microsoft. You can also connect Cartesia, ElevenLabs, OpenAI TTS, or Google Cloud TTS, or use local system speech.

### 3. 🎙️ Voice Flow — System-Wide Voice Dictation & Text Injection

Voice Flow lets you speak naturally and injects clean, formatted text directly into whatever application is currently focused—Slack, Word, VS Code, Notion, browser inputs, or terminal windows.

* **Local-First Dictation**: Bundled local **Faster-Whisper** engine runs completely on-device across CPU or GPU without requiring internet access.
* **Downloadable Streaming Models**: Optional download of **NVIDIA Nemotron Speech Streaming English 0.6B** and **Nemotron 3.5 ASR Streaming 0.6B** for real-time streaming speech recognition.
* **Cloud STT Providers**: Connect Deepgram, Groq Whisper, OpenAI Whisper, or Gemini STT for instant cloud-accelerated transcription.
* **On-Device & Cloud AI Polish**:
  * Downloadable on-device polish models (**S1-mini by Superwhisper**, **Liquid LFM 2.5 350M**) via llama.cpp for private text cleanup.
  * Windows AI Text Rewriter where supported by hardware.
  * Optional cloud LLMs (Gemini, Claude, OpenAI, Groq, Nebius Token Factory, Ollama) for smart cleanup, conversational rewriting, and prompt formulation.
* **Voice Commands**: Commands such as "make this an email" or "summarize this" need a cloud polish model (for example Gemini with your own API key). Local polish (S1-mini, LFM) cleans up your dictation but does not run commands.
* **"Hey Voice Flow"**: This works inside a normal dictation, not as an always-on listener. Press your dictation hotkey, then say something like "Hey Voice Flow, make this an email..." The app only listens while you are dictating.
* **Personal Dictionary & Snippets**: Add custom acronyms, jargon, and snippet abbreviations that expand automatically with cross-process memory.

---

## 🟢 Nebius Token Factory + NVIDIA Nemotron

You can run the app's AI steps on NVIDIA Nemotron models hosted by [Nebius Token Factory](https://tokenfactory.nebius.com/). It is optional and only used when you pick a Nebius model. Without a Nebius key the app makes no Nebius calls and everything works as before, including the offline fallbacks.

### Setup

1. Create an API key in Nebius Token Factory.
2. Open **Video Flow → API Providers → Nebius Token Factory**, click **Add**, and paste the key. The key is stored on your computer like every other provider key.
3. Click **Test**. It calls `GET https://api.tokenfactory.nebius.com/v1/models` with your key. Once the test passes, the Nebius models appear in the model pickers.
4. Pick a Nebius model wherever you pick a model: Voice Flow cleanup, Audio Flow summaries, or Video Flow planning.

Token Factory is OpenAI-compatible, so the app uses the same Chat Completions requests it already sends to OpenAI and Groq, with base URL `https://api.tokenfactory.nebius.com/v1/` and a Bearer key.

### Models

| Model | Id | Good for |
| --- | --- | --- |
| Nemotron 3.5 Lightning | `nvidia/Nemotron-3_5-Lightning` | Fast jobs: Voice Flow cleanup and voice commands, Audio Flow summaries, quick video plans |
| Nemotron 3 Super 120B | `nvidia/nemotron-3-super-120b-a12b` | Longer, structured jobs such as Video Flow planning |
| DeepSeek V4 Flash | `deepseek-ai/DeepSeek-V4-Flash-0731` | Non-NVIDIA option |
| Qwen3 235B Instruct | `Qwen/Qwen3-235B-A22B-Instruct-2507` | Non-NVIDIA option |

* The list was checked against the public Token Factory model catalog. Any other model id (for example `nvidia/Nemotron-3-Ultra-550b-a55b`) can be added with **Add Model**.
* Nemotron can return its reasoning in a `<think>` block. The app removes it from Nebius answers before using them.

### The full voice pipeline

With the downloadable Nemotron speech model and a Nebius Nemotron model picked for cleanup, a dictation goes: your voice → **NVIDIA Nemotron speech recognition on your device** (Nemotron Speech Streaming English 0.6B or Nemotron 3.5 ASR Streaming 0.6B, Q8_0 GGUF) → **Nemotron on Nebius** for cleanup or the voice command → text typed into your app. The audio stays on your computer; only the transcript goes to Nebius.

### Audio Flow voices

Token Factory has no speech models, so Audio Flow's spoken audio uses the app's own voice engines (Microsoft Edge Neural by default). A Nebius Nemotron model can write the Audio Flow summary that is then read aloud.

---

## 🔒 Privacy & Security Architecture

* **Local-First by Design**: Voice Flow speech recognition (Faster-Whisper, Nemotron) and local polish (S1-mini, LFM) run on your device, and that audio and text never leave your computer.
* **When the cloud is used**: only for cloud polish or cloud speech providers you set up with your own key, online text-to-speech voices (including the default Microsoft Edge voice for Audio Flow and Video Flow, which sends the text being read to Microsoft), and NotebookLM features.
* **Explicit Cloud Routing (BYOK)**: When you select a cloud provider, only the text or audio required for that specific request is transmitted to that provider. No central tracking intermediary is used.
* **Local Storage**: Dictation history, audio recordings, and provider credentials reside locally in SQLite databases inside `~/.voice_flow/`.
* **Encrypted Backups**: The `.flowvault` export/import format secures account profiles, preferences, and custom dictionaries using **AES-256-GCM** encryption.
* **Loopback Desktop API**: The internal GUI HTTP and WebSocket server binds strictly to `127.0.0.1:8991` with Origin, Host, and port verification to prevent cross-origin browser access.

### Telemetry & Crash Reporting

AI Productivity Flow is strictly privacy-first:
* **On by default, with an opt-out**: Crash reports are on for every install, including existing users who never changed the setting. Open **Settings → System → About & Updates → Privacy** and choose **Turn off**. That takes effect immediately, with no restart. An explicit opt-out stays off.
* **Zero Audio / Transcript Exposure**: Crash reports never contain microphone audio, speech transcripts, dictation text, clipboard contents, or request payloads.
* **Strict Privacy Scrubbing**: Stack traces and error messages pass through a local privacy scrubber before leaving your machine:
  * Personal username paths (e.g. `/Users/<username>/...` and `C:\Users\<username>\...`) are scrubbed and replaced with `[REDACTED]`.
  * API keys and secrets (`OPENAI_*`, `ANTHROPIC_*`, `GROQ_*`, `GEMINI_*`, `DEEPGRAM_*`, `SENTRY_*`, `AWS_*`, etc.) are stripped.
  * Performance tracing and user profiling are completely disabled (0% sample rate).
* **How to Verify or Change**: The Privacy row under **Settings → System → About & Updates** turns crash reports off or back on. You can also run `voice-flow --test-crash-reporting` to test your current preference.

---

## ⌨️ Global Shortcuts

| Platform | Default Shortcut | Action |
|:---|:---|:---|
| **Windows** | `Ctrl + Win` | Start / Stop voice dictation into active input |
| **Windows** | `Alt + Space` (Optional) | Configurable secondary dictation trigger |
| **Windows** | `Middle Mouse Click` (Optional) | Push-to-talk with mouse button |
| **macOS** | `Cmd + Option` | Start / Stop voice dictation into active input |

---

## 🛠️ Development & Building from Source

To set up a local development environment or contribute:

```bash
# Clone the repository
git clone https://github.com/uzerkayat2004-gif/AI-Productivity-Flow-Nebius.git
cd AI-Productivity-Flow-Nebius

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install editable package with test dependencies
pip install -e .
pip install pytest pytest-asyncio pytest-timeout cryptography

# Run the test suite
pytest tests/test_platform_layer.py tests/test_runtime_compatibility.py tests/test_version_consistency.py
```

For full details on project architecture, code conventions, and packaging pipelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📄 License

AI Productivity Flow is open-source software licensed under the [Apache-2.0 License](LICENSE).
Third-party component notices and licenses are documented in [release/THIRD_PARTY_NOTICES.txt](release/THIRD_PARTY_NOTICES.txt).
