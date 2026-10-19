"""Meta Model API provider (Muse Spark text, Muse Image scene images).

Meta Model API speaks the OpenAI Chat Completions protocol at
``https://api.meta.ai/v1``, so text requests ride the same adapters as the
other OpenAI-compatible providers (the same shape as Nebius Token Factory in
``voice_flow.nebius_provider``). This module only owns the parts that are
specific to Meta:

* where the key comes from (a saved Video Flow connection, else the
  ``MODEL_API_KEY`` environment variable),
* which Muse Spark model serves a request (``muse-spark-1.3``, then
  ``muse-spark-1.2``, then ``muse-spark-1.1``), checked against
  ``GET /v1/models`` at runtime with a cache, falling back gracefully when an
  id is not served by the account,
* the optional Muse Image call (``POST /v1/images/generations``) used for
  Video Flow scene images, which is off unless the user turns it on.

Meta is opt-in. It is never picked automatically, and no key means no
network call: every function that would talk to Meta returns early when it
has no key.

Not yet tested against the live API (no key existed when this was written);
all tests mock HTTP. See docs/HACKATHON_META.md.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Iterable

log = logging.getLogger(__name__)

PROVIDER_ID = "meta_model_api"
PROVIDER_NAME = "Meta Model API"
BASE_URL = "https://api.meta.ai/v1/"
CHAT_COMPLETIONS_URL = BASE_URL + "chat/completions"
MODELS_URL = BASE_URL + "models"
IMAGES_GENERATIONS_URL = BASE_URL + "images/generations"
ENV_KEY = "MODEL_API_KEY"
API_KEY_URL = "https://dev.meta.ai/"

# Muse Spark versions as listed on https://dev.meta.ai/docs/models (checked
# 2026-10-19). Only defaults: every request validates them against the
# account's own /v1/models list first.
MUSE_SPARK_13 = "muse-spark-1.3"
MUSE_SPARK_12 = "muse-spark-1.2"
MUSE_SPARK_11 = "muse-spark-1.1"
DEFAULT_TEXT_MODELS: tuple[str, ...] = (MUSE_SPARK_13, MUSE_SPARK_12, MUSE_SPARK_11)

MUSE_IMAGE = "muse-image-1.0"

# Picker entries that mean "let the router choose".
TEXT_MODEL_ALIASES = frozenset({"", "auto", "muse-auto", "muse-spark-auto"})

SETTING_TEXT_MODEL = "meta_model_text"
SETTING_SCENE_IMAGES = "meta_scene_images"

# Key format documented by Meta: LLM|{numeric_id}|{secret}. Only used for a
# friendly hint; a key in another format is still sent unchanged.
_KEY_FORMAT_RE = re.compile(r"^LLM\|\d+\|\S+$")

MODEL_CACHE_TTL_SECONDS = 600.0
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9@._:/-]{1,200}$")

_cache_lock = threading.Lock()
_model_cache: dict[str, tuple[float, list[str]]] = {}
_warming: set[str] = set()


def _cache_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:24]


def clear_model_cache() -> None:
    with _cache_lock:
        _model_cache.clear()
        _warming.clear()


def _provider_service():
    from voice_flow.video_flow_providers import video_flow_provider_service

    return video_flow_provider_service


def looks_like_meta_key(api_key: str | None) -> bool:
    return bool(_KEY_FORMAT_RE.fullmatch(str(api_key or "").strip()))


def env_api_key() -> str:
    return str(os.environ.get(ENV_KEY) or "").strip()


def resolve_api_key(service: Any = None) -> str:
    """Return the first healthy saved Meta key, else ``MODEL_API_KEY``."""
    try:
        svc = service or _provider_service()
        for connection in svc.active_connections(PROVIDER_ID):
            if not svc.connection_is_healthy(connection):
                continue
            secret = svc.resolve_connection_secret(connection)
            if secret:
                return str(secret).strip()
    except Exception:
        pass
    return env_api_key()


def has_api_key(service: Any = None) -> bool:
    return bool(resolve_api_key(service))


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json", "User-Agent": "VoiceFlow/2.0"}


def _parse_model_ids(body: Any) -> list[str]:
    items: Iterable[Any] = []
    if isinstance(body, dict):
        items = body.get("data") or body.get("models") or []
    elif isinstance(body, list):
        items = body
    ids: list[str] = []
    for item in items:
        mid = item.get("id") if isinstance(item, dict) else item
        if isinstance(mid, str) and mid.strip():
            ids.append(mid.strip())
    return ids


def request_model_ids(api_key: str, *, timeout: float = 8.0) -> list[str]:
    """``GET /v1/models``. Raises ``urllib.error`` exceptions on failure."""
    request = urllib.request.Request(MODELS_URL, headers=_auth_headers(api_key), method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError("Meta Model API returned an unreadable model list") from exc
    ids = _parse_model_ids(body)
    with _cache_lock:
        _model_cache[_cache_key(api_key)] = (time.monotonic(), ids)
    return ids


def cached_model_ids(api_key: str) -> list[str] | None:
    if not api_key:
        return None
    with _cache_lock:
        hit = _model_cache.get(_cache_key(api_key))
    if not hit:
        return None
    stamp, ids = hit
    if time.monotonic() - stamp > MODEL_CACHE_TTL_SECONDS:
        return None
    return list(ids)


def fetch_model_ids(api_key: str, *, timeout: float = 8.0, blocking: bool = True) -> list[str] | None:
    """Return the account's served model ids, or ``None`` when unknown.

    ``blocking=False`` never waits on the network: it returns the cached list
    (or ``None``) and refreshes the cache in the background, so voice
    polishing never pays for a cold cache.
    """
    if not api_key:
        return None
    cached = cached_model_ids(api_key)
    if cached is not None:
        return cached
    if not blocking:
        warm_model_cache_async(api_key, timeout=timeout)
        return None
    try:
        return request_model_ids(api_key, timeout=timeout)
    except Exception as exc:
        log.info("Meta model list unavailable (%s); using configured Muse ids as-is", exc.__class__.__name__)
        return None


def warm_model_cache_async(api_key: str, *, timeout: float = 8.0) -> None:
    if not api_key:
        return
    key = _cache_key(api_key)
    with _cache_lock:
        if key in _warming:
            return
        _warming.add(key)

    def worker() -> None:
        try:
            request_model_ids(api_key, timeout=timeout)
        except Exception:
            pass
        finally:
            with _cache_lock:
                _warming.discard(key)

    threading.Thread(target=worker, name="meta-models-warm", daemon=True).start()


def _clean_override(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower().startswith(PROVIDER_ID + "/"):
        text = text[len(PROVIDER_ID) + 1:]
    return text if _MODEL_ID_RE.fullmatch(text or "") else ""


def text_model_override(settings_getter: Callable[[str, Any], Any] | None = None) -> str:
    """The user's text model override, if one is saved."""
    try:
        getter = settings_getter or _provider_service().get_setting
        return _clean_override(getter(SETTING_TEXT_MODEL, ""))
    except Exception:
        return ""


def set_text_model_override(model_id: str, service: Any = None) -> str:
    raw = str(model_id or "").strip()
    clean = _clean_override(raw)
    if raw and not clean:
        raise ValueError("Enter only the model ID, for example muse-spark-1.3.")
    (service or _provider_service()).set_setting(SETTING_TEXT_MODEL, clean)
    return clean


def _spark_version(model_id: str) -> tuple[int, ...]:
    match = re.search(r"muse-spark-(\d+(?:\.\d+)*)", model_id.casefold())
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def choose_model(available: list[str] | None, preferred: Iterable[str] = ()) -> str:
    """Pick the Muse model id for a text request.

    Candidates are tried in order: ``preferred`` (an explicit pick, then the
    saved override), then ``muse-spark-1.3`` → ``1.2`` → ``1.1``. When the
    served list is unknown the first candidate is used unchanged. When none is
    served, the newest served Standard-mode Muse Spark is used. Contributor
    variants (whose content Meta may train on) and other model lines are
    never picked automatically; with nothing suitable the first candidate is
    sent unchanged so the API reports the problem.
    """
    candidates: list[str] = []
    for item in [*preferred, *DEFAULT_TEXT_MODELS]:
        clean = _clean_override(item)
        if clean and clean not in candidates:
            candidates.append(clean)
    if not available:
        return candidates[0]
    exact = set(available)
    folded = {mid.casefold(): mid for mid in available}
    for candidate in candidates:
        if candidate in exact:
            return candidate
        if candidate.casefold() in folded:
            return folded[candidate.casefold()]
    sparks = [
        mid for mid in available
        if _spark_version(mid) and "contributor" not in mid.casefold()
    ]
    if sparks:
        best = max(sparks, key=_spark_version)
        log.warning("Meta: %s not served; using %s", candidates[0], best)
        return best
    log.warning("Meta: no Muse Spark model served; sending %s unchanged", candidates[0])
    return candidates[0]


def split_requested_model(model_id: str | None) -> str:
    """Return the explicit model for a picker id ("" for the auto entry)."""
    raw = str(model_id or "").strip()
    if raw.lower().startswith(PROVIDER_ID + "/"):
        raw = raw[len(PROVIDER_ID) + 1:]
    return "" if raw.lower() in TEXT_MODEL_ALIASES else raw


def resolve_model(
    model_id: str | None,
    *,
    api_key: str,
    settings_getter: Callable[[str, Any], Any] | None = None,
    blocking: bool = True,
    timeout: float = 8.0,
) -> str:
    """Resolve the model id a Meta request should actually send."""
    explicit = split_requested_model(model_id)
    preferred = [explicit, text_model_override(settings_getter)]
    available = fetch_model_ids(api_key, timeout=timeout, blocking=blocking) if api_key else None
    return choose_model(available, preferred)


def scene_images_setting(settings_getter: Callable[[str, Any], Any] | None = None) -> bool:
    """Whether the user turned on Muse Image scene images (off by default)."""
    try:
        getter = settings_getter or _provider_service().get_setting
        value = getter(SETTING_SCENE_IMAGES, False)
    except Exception:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return value is True or value == 1


def set_scene_images(enabled: Any, service: Any = None) -> bool:
    if isinstance(enabled, str):
        flag = enabled.strip().lower() in {"1", "true", "yes", "on"}
    else:
        flag = bool(enabled)
    (service or _provider_service()).set_setting(SETTING_SCENE_IMAGES, flag)
    return flag


def routing_summary(api_key: str | None = None, *, service: Any = None) -> dict[str, Any]:
    """Secret-free summary for the provider page (never calls the network)."""
    key = api_key if api_key is not None else resolve_api_key(service)
    getter = (service.get_setting if service is not None else None)
    available = cached_model_ids(key) if key else None
    override = text_model_override(getter)
    return {
        "has_key": bool(key),
        "env_key": bool(env_api_key()),
        "key_format_ok": looks_like_meta_key(key) if key else None,
        "validated": available is not None,
        "served_muse_models": sorted(m for m in (available or []) if m.casefold().startswith("muse-")),
        "text": {
            "override": override,
            "defaults": list(DEFAULT_TEXT_MODELS),
            "resolved": choose_model(available, [override]),
        },
        "scene_images": {
            "enabled": scene_images_setting(getter),
            "model": MUSE_IMAGE,
            "served": (MUSE_IMAGE in available) if available is not None else None,
        },
    }


def strip_reasoning(text: str | None) -> str | None:
    """Drop a ``<think>…</think>`` block if one ever appears in content.

    Meta documents that Muse reasoning stays private on Chat Completions, so
    this is a defensive no-op in the normal case.
    """
    from voice_flow.nebius_provider import strip_reasoning as _strip

    return _strip(text)


def check_connection(api_key: str, *, timeout: float = 15.0) -> dict[str, Any]:
    """Settings "Test" button: ``GET /v1/models`` and report the routing."""
    if not api_key:
        return {"success": False, "status": "error", "error": "No Meta Model API key saved."}
    started = time.monotonic()
    ids = request_model_ids(api_key, timeout=timeout)
    latency_ms = int((time.monotonic() - started) * 1000)
    return {
        "success": True,
        "status": "connected",
        "latency_ms": latency_ms,
        "model_count": len(ids),
        "muse_models": sorted(m for m in ids if m.casefold().startswith("muse-")),
        "routing": {"text": choose_model(ids, [text_model_override()])},
        "image_model_served": MUSE_IMAGE in ids,
        "key_format_ok": looks_like_meta_key(api_key),
    }


# --- Muse Image ------------------------------------------------------------


class MuseImageError(RuntimeError):
    """Any failure to get a usable image back from Muse Image."""


MAX_IMAGE_BYTES = 25 * 1024 * 1024


def _image_kind(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return ""


def generate_image(
    api_key: str,
    prompt: str,
    *,
    size: str = "1600x900",
    output_format: str = "png",
    timeout: float = 120.0,
) -> bytes:
    """One Muse Image generation; returns the image bytes.

    Request fields follow https://dev.meta.ai/docs/api-reference/images/schemas
    (CreateImageRequest): ``model``, ``prompt``, ``n``, ``size`` (aspect ratio
    only), ``response_format`` (``b64_json`` is the default) and
    ``output_format`` (``webp`` by default; PNG is asked for here because the
    renderers decode it everywhere). ``reasoning_strength="low"`` skips the
    self-refinement passes to keep video render time reasonable.

    The response is an ``ImagesResponse``: ``data[0].b64_json`` is used, and
    ``data[0].url`` is followed only when no base64 payload is present.
    Raises :class:`MuseImageError` on anything unexpected.
    """
    if not api_key:
        raise MuseImageError("No Meta Model API key saved.")
    text = str(prompt or "").strip()
    if not text:
        raise MuseImageError("Empty image prompt.")
    payload = {
        "model": MUSE_IMAGE,
        "prompt": text[:4000],
        "n": 1,
        "size": size,
        "response_format": "b64_json",
        "output_format": output_format,
        "reasoning_strength": "low",
    }
    headers = {**_auth_headers(api_key), "Content-Type": "application/json"}
    request = urllib.request.Request(
        IMAGES_GENERATIONS_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_IMAGE_BYTES * 2)
    except urllib.error.HTTPError as exc:
        raise MuseImageError(f"Muse Image HTTP {exc.code}") from exc
    except Exception as exc:
        raise MuseImageError(f"Muse Image request failed ({exc.__class__.__name__})") from exc
    try:
        body = json.loads(raw.decode("utf-8"))
        item = (body.get("data") or [])[0]
    except Exception as exc:
        raise MuseImageError("Muse Image returned an unreadable response") from exc
    if not isinstance(item, dict):
        raise MuseImageError("Muse Image returned no image")
    data: bytes = b""
    b64 = item.get("b64_json")
    if isinstance(b64, str) and b64.strip():
        try:
            data = base64.b64decode(b64, validate=False)
        except Exception as exc:
            raise MuseImageError("Muse Image returned invalid base64") from exc
    else:
        url = str(item.get("url") or "")
        if not url.startswith("https://"):
            raise MuseImageError("Muse Image returned no image data")
        try:
            # Hosted result URLs are expected to be pre-signed; the API key is
            # never forwarded to another host.
            with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as response:
                data = response.read(MAX_IMAGE_BYTES + 1)
        except Exception as exc:
            raise MuseImageError(f"Muse Image download failed ({exc.__class__.__name__})") from exc
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise MuseImageError("Muse Image returned an empty or oversized image")
    if not _image_kind(data):
        raise MuseImageError("Muse Image returned an unrecognised image format")
    return data


__all__ = [
    "API_KEY_URL",
    "BASE_URL",
    "CHAT_COMPLETIONS_URL",
    "DEFAULT_TEXT_MODELS",
    "ENV_KEY",
    "IMAGES_GENERATIONS_URL",
    "MODELS_URL",
    "MUSE_IMAGE",
    "MUSE_SPARK_11",
    "MUSE_SPARK_12",
    "MUSE_SPARK_13",
    "MuseImageError",
    "PROVIDER_ID",
    "PROVIDER_NAME",
    "SETTING_SCENE_IMAGES",
    "SETTING_TEXT_MODEL",
    "cached_model_ids",
    "check_connection",
    "choose_model",
    "clear_model_cache",
    "fetch_model_ids",
    "generate_image",
    "has_api_key",
    "looks_like_meta_key",
    "resolve_api_key",
    "resolve_model",
    "routing_summary",
    "scene_images_setting",
    "set_scene_images",
    "set_text_model_override",
    "split_requested_model",
    "strip_reasoning",
    "text_model_override",
]
