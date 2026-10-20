# Nebius x NVIDIA hackathon notes

This file explains what changed in AI Productivity Flow during the hackathon window and how the app uses Nebius Token Factory and NVIDIA Nemotron. It only describes what is in the code.

## What changed since Aug 26, 2026

Source: `git log --since=2026-08-26` on this repository. On Aug 26 the newest commit was `01017d8` (Aug 22, "docs: realign AI Productivity Flow public identity and documentation"). There were no commits between Aug 22 and Sep 9.

From Sep 9 to Oct 19 (before this branch) there were 322 commits, 276 of them not merges. `src/voice_flow` changed in 269 files, and the number of test files went from 52 to 333. The main pieces of work:

- **Releases.** The app went from a Windows beta to Version 1.0. The v1.0.0 baseline landed on Oct 5, v1.0.2 on Oct 16, and internal builds 1.0.3 to 1.0.13 followed between Oct 16 and Oct 19 (installer, first launch, splash fixes, in-app updates, then silent auto-updates).
- **macOS.** A platform layer and a native Apple Silicon app bundle (Sep 15 onwards), with bundled Python, llama-server and NeMo-Speech, a real Quit, menu bar items, and many paste and Audio Flow fixes for macOS 14. Video Flow came to macOS on Oct 20.
- **Voice Flow.** Local NVIDIA Nemotron speech recognition (Nemotron Speech Streaming English 0.6B and Nemotron 3.5 ASR Streaming 0.6B, run in their own worker and kept warm), S1-mini by Superwhisper as an offline polish model with a factual safety gate, a rebuilt dictionary (Words and Replacements), safer voice commands, and speed work on dictation and polish.
- **Audio Flow.** Read and Summary modes, NotebookLM audio, a hardened player (including a stored XSS fix in the summary player history), and Mac support for selection, hotkey and playback.
- **Video Flow.** NotebookLM durable sign-in and recovery, a retry when NotebookLM refuses a video and a local fallback after that, Cinematic limited to Google AI Ultra accounts, and since Oct 19 a missing AI planning key never fails a video.
- **Onboarding and Settings.** Guided tours for all three flows, simpler Settings, and opt-out crash reports that never include user text.
- **Security.** Cross-site GETs to the local API are refused, the data folder is private on macOS, only web URLs are opened from the app, and loopback calls skip proxies.
- **Model work.** VF-1 training and evaluation work happened in this repo between Oct 12 and Oct 15, then moved to a separate private repository on Oct 16.

Before this work, Nemotron *language* models could already be picked through the NVIDIA NIM and OpenRouter catalog entries. There was no Nebius provider.

### Added on Oct 20, 2026 (build 1.0.14)

- A **Nebius Token Factory** provider (OpenAI-compatible, `https://api.tokenfactory.nebius.com/v1/`, Bearer key saved in the app), listed in the Video Flow API Providers grid with an add-key form, a Get API Key link, and a **Test** button that calls `/v1/models`.
- Curated models, checked against `tokenfactory.nebius.com/model-catalog.md`: Nemotron 3.5 Lightning, Nemotron 3 Super 120B, DeepSeek V4 Flash (0731), Qwen3 235B Instruct 2507. Other ids via **Add Model**.
- Nebius works in Voice Flow cleanup and voice commands, Video Flow planning, and Audio Flow summaries and explanations.
- Unit tests in `tests/test_nebius_provider.py`, with every HTTP call mocked.

The same provider is in the main app repository (PR #62). This repository mirrors the main app plus these hackathon notes.

## How Token Factory and Nemotron are used

### Provider

- Code: `src/voice_flow/nebius_provider.py` (base URL, model list URL, `<think>` cleanup), plus the `nebius` entries in `video_flow_providers.py` (provider card, curated models, Test), `video_flow_service.py` (planning endpoint), `voice_polish_bridge.py` (Voice Flow cleanup), `audio_summary.py` (Audio Flow summaries), `polisher.py` and `provider_registry.py` (key check).
- Requests are standard Chat Completions calls to `https://api.tokenfactory.nebius.com/v1/chat/completions`, the same shape the app already sends to OpenAI and Groq.
- Nebius is used only when the user adds a key and picks a Nebius model. It is never picked automatically and is not in any automatic fallback list.

### Which model for which job

| Job | Suggested model | Why |
| --- | --- | --- |
| Voice Flow cleanup and voice commands | `nvidia/Nemotron-3_5-Lightning` | Dictation cleanup has to land in a few seconds |
| Audio Flow summaries | `nvidia/Nemotron-3_5-Lightning` | Short text, fast answer |
| Video Flow planning | `nvidia/Nemotron-3_5-Lightning` or `nvidia/nemotron-3-super-120b-a12b` | A video plan is a longer structured job |

Nemotron can return its reasoning in a `<think>` block. The app removes that block from Nebius answers before using them.

### The all-NVIDIA voice pipeline

The app already ships local NVIDIA Nemotron speech recognition (`src/voice_flow/nemotron_engine.py`, models listed in `downloadable_models.py`): Nemotron Speech Streaming English 0.6B or Nemotron 3.5 ASR Streaming 0.6B as Q8_0 GGUF files, run through the NeMo-Speech native library. They are one-click downloads; fresh installs are offered the download, and Whisper base.en stays as the bundled fallback.

With that model downloaded and a Nebius Nemotron model picked for cleanup, a dictation runs:

voice → Nemotron speech recognition on the device → Nemotron on Nebius (cleanup or voice command) → text typed into the focused app.

The audio never leaves the computer. Only the transcript is sent to Nebius.

### Audio Flow

Token Factory has no speech-to-text or text-to-speech models, so Audio Flow's spoken audio uses the app's own voice engines (Microsoft Edge Neural by default, or ElevenLabs, Cartesia, OpenAI, Google Cloud TTS). Nebius is not used to make the audio itself.

## Not done yet / limits

- Unit tests mock every HTTP call; live use is shown in the demo video.
- No special "reasoning off" request flag is sent to Nemotron, because the exact Token Factory parameter was not verified.
- Saved keys show their models in the pickers after **Test** passes, like every other provider.

## Feedback for Nebius (draft)

TODO: write about 150 words of honest feedback after using Token Factory live. Points to cover: how setup and key creation felt, whether the `/v1/models` list matched the docs and models.dev, latency of Nemotron 3.5 Lightning for short dictation cleanup, quality of Nemotron 3 Ultra for long JSON video plans, rate limits or errors hit, pricing clarity, and one thing that would make Token Factory easier for a small desktop app.
