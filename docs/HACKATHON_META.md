# Meta Model API (Muse) notes

This file explains the optional Meta Model API provider added on the `feat/meta-muse` branch of the hackathon copy of AI Productivity Flow. It only describes what is in the code.

**Status: not tested against the live Meta Model API.** No Meta key existed when this was written. Every Meta HTTP call in the tests is mocked. The request and response fields follow Meta's public docs as read on Oct 19, 2026 (links below). Nothing on this branch is merged into `main` or released, and `main` is unchanged.

## What was added

- A **Meta Model API** provider (`src/voice_flow/meta_provider.py`). It is OpenAI-compatible: base URL `https://api.meta.ai/v1`, `POST /v1/chat/completions`, Bearer key. The key comes from a saved Video Flow connection first, then the `MODEL_API_KEY` environment variable.
- **Muse Spark text routing** with runtime checks against `GET /v1/models`, a 10-minute cache per key, graceful fallback, and a text-model override box on the provider page.
- **Optional Muse Image scene images** for Video Flow (`src/voice_flow/video_flow_engine/muse_scene_images.py`), behind a setting that is off by default.
- Registration in the same places as the Nebius provider: `video_flow_providers.py` (provider list, seeded models, **Test** button, provider page details), `video_flow_service.py` (planning endpoint and gateway), `voice_polish_bridge.py`, `audio_summary.py`, `polisher.py`, `provider_registry.py`, the settings endpoint in `gui/api_server.py`, and the provider page in `gui/video-flow.js` / `gui/app.js`.
- Tests: `tests/test_meta_provider.py` (48 tests, all HTTP mocked).

## Opt-in only

- **Nebius stays the default.** Meta is not added to any automatic provider chain. It runs only when you pick a Meta model.
- **No key, no calls.** With no saved Meta connection and no `MODEL_API_KEY`, no request goes to Meta and the app behaves exactly as before. The tests check this with a guard that fails on any network call.
- **Scene images are off by default**, and also need external AI to be allowed for that video.

## How to enable it

1. Create a key on [dev.meta.ai](https://dev.meta.ai/). Meta documents the format as `LLM|{numeric_id}|{secret}`. The provider page warns if a saved key does not look like that, but still sends it as entered.
2. Open **Video Flow → Providers → Meta Model API**, click **Add**, and paste the key. Or set `MODEL_API_KEY` (PowerShell: `$env:MODEL_API_KEY="LLM|..."`). A saved key is used before the environment variable.
3. Click **Test**. It calls `GET https://api.meta.ai/v1/models` and shows the Muse Spark model that will be used and whether `muse-image-1.0` is served.
4. Pick a Meta model wherever you pick a model:
   - **Voice Flow** cleanup and voice commands,
   - **Audio Flow** summaries and explanations,
   - **Video Flow** planning, creative direction and scene authoring.
   `Muse Spark auto` lets the app choose.
5. Optional: on the same provider page, tick **Scene images with Muse Image** and press **Save**.

Never put a real key in the repository. The app stores keys in its own data folder, not in the code.

## Models

### Text

| Order | Model | Notes |
| --- | --- | --- |
| 1 | `muse-spark-1.3` | Default. Meta's recommended version for new work. |
| 2 | `muse-spark-1.2` | Used if 1.3 is not served. |
| 3 | `muse-spark-1.1` | Used if 1.3 and 1.2 are not served. |

How a model is chosen for a request:

1. The model picked in the app, if it is a concrete id (`muse-auto` means "let the app decide").
2. The text-model override saved on the Meta provider page.
3. `muse-spark-1.3` → `1.2` → `1.1`.
4. If none of those is in the account's `/v1/models` list: the newest served Standard-mode Muse Spark. **Contributor-mode** ids (`*-contributor`, where Meta may train on your content) and other model lines such as Muse Wonder are never picked automatically. If nothing suitable is served, the first choice is sent unchanged and the API reports the problem.

Video Flow waits for the model list (8 second limit). Voice polishing never waits: it uses the cached list and refreshes it in the background. If the list cannot be loaded, the configured id is sent unchanged.

Meta says Muse Spark's reasoning stays private on Chat Completions (`reasoning_content` comes back empty for external keys). The app still strips any `<think>…</think>` block, the same way it does for Nemotron, in case one ever appears.

### Images

- Model `muse-image-1.0`, `POST https://api.meta.ai/v1/images/generations`. Meta says this endpoint mirrors the OpenAI Images API.
- Request sent: `model`, `prompt`, `n: 1`, `size` (`1600x900` for 16:9 videos, `900x1600` for 9:16, `1024x1024` for 1:1), `response_format: "b64_json"`, `output_format: "png"`, `reasoning_strength: "low"`.
- Response read: `data[0].b64_json` (the documented default). Only if that is missing, `data[0].url` is downloaded (https only, without sending the API key). The bytes must be a real PNG, JPEG or WebP, or the image is dropped.
- About $0.01 per image according to Meta. At most 12 scenes get an image per video, 3 at a time, with a 5-minute total budget.

## How scene images work

They run only when the setting is on, a Meta key is available, and external AI is allowed for that video. Then, after the scene plan is built and before rendering:

1. One prompt per scene is built from the scene title, its learning goal, the first narration lines and the visual direction. It asks for no text, letters or logos, because the scene already draws its own text.
2. Images are saved under the job's `narova/assets/muse/scene-NN.png`, and a list of what was used is written to `plan/muse_scene_images.json`.
3. Portable (no-browser) scenes: the scene's visual tree is wrapped in a group with a full-frame image behind it, and a solid background colour is made see-through so the picture shows.
4. Browser (HyperFrames) scenes: a faint decorative `<img>` is put behind the scene content.

Fallbacks:

- A scene whose image fails keeps its normal visuals.
- If no image works, or anything unexpected happens, the video is made exactly as before.
- If a render with images fails, the app renders once more with the normal visuals before any other fallback.

## Not done yet / unsure

- **Untested live.** Everything above is checked only with mocked HTTP until a key exists.
- **Image layout is unverified.** How the backdrop looks in the real renderers, especially the browser (HyperFrames) path, has not been seen on screen. The render-failure fallback protects the video, not the look.
- `reasoning_effort` is not sent yet. Muse Spark does not accept `"none"`; if voice cleanup is slow, sending `"minimal"` or `"low"` is the first thing to try.
- The app sends `max_tokens`, which Meta marks as deprecated in favour of `max_completion_tokens` but still lists. Reasoning tokens count toward that limit.
- Whether `size`, `output_format: "png"` and `reasoning_strength` are all accepted together on `/v1/images/generations` is taken from the schema page, not from a real call.
- **Availability by country.** Meta's Jul 8, 2026 Muse Spark post says the API opened as a public preview for developers in the US, and the models page points to a Geographic Use Policy. Whether a key can be created and used from India was not checked.
- `muse-spark-1.3` audio input is noted by Meta as not fully supported. The app only sends text, so this does not affect it.

## Sources

- API reference (base URL, Bearer auth, `MODEL_API_KEY`): https://dev.meta.ai/docs/api-reference
- Models (Muse Spark 1.3 / 1.2 / 1.1, Contributor mode, Muse Image): https://dev.meta.ai/docs/models
- Chat Completions schema: https://dev.meta.ai/docs/api-reference/chat-completions/schemas
- Reasoning (private reasoning, `reasoning_effort` values): https://dev.meta.ai/docs/reasoning
- Image generation endpoint and schema (`b64_json` default, `url` option, `output_format`, `reasoning_strength`): https://dev.meta.ai/docs/api-reference/images/create-image and https://dev.meta.ai/docs/api-reference/images/schemas
- Muse Image blog post: https://dev.meta.ai/resources/blog/build-with-muse-Image
- Muse Spark blog post: https://dev.meta.ai/resources/blog/build-with-muse-spark
