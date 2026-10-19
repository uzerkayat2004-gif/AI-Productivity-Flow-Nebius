"""Optional Muse Image scene images for Video Flow (Meta Model API).

Off by default. It runs only when all of these hold:

* the user turned on "Scene images with Muse Image" on the Meta Model API
  provider page (setting ``meta_scene_images``),
* a Meta key is available (saved connection or ``MODEL_API_KEY``),
* external AI is allowed for this video (``allow_external_ai is True``).

For each scene (up to :data:`MAX_SCENE_IMAGES`) one image is generated with
``muse-image-1.0`` and laid behind the existing scene visuals:

* portable (``no-browser``) scenes: the ``visual`` tree is wrapped in a
  ``group`` whose first child is a full-frame ``image`` node; a solid hex
  background on the original tree is made translucent so the picture shows.
* browser (``hyperframes``) scenes: a decorative ``<img>`` is prepended to the
  scene body, absolutely positioned, faint, and behind the content.

The original production is never mutated. A scene whose image fails keeps its
current visuals; when nothing succeeds, or anything unexpected happens, the
original production is returned unchanged. The engine also re-renders with
the original production if a render with images fails.
"""

from __future__ import annotations

import copy
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)

MAX_SCENE_IMAGES = 12
MAX_WORKERS = 3
TOTAL_BUDGET_SECONDS = 300.0
PER_IMAGE_TIMEOUT_SECONDS = 120.0
ASSET_DIR = "assets/muse"
OVERLAY_ALPHA = 0.78

_SIZES = {"16:9": "1600x900", "9:16": "900x1600", "1:1": "1024x1024", "4:5": "1024x1280"}
_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")

ImageGenerator = Callable[[str, str, str], bytes]  # (api_key, prompt, size) -> bytes


def scene_images_requested(kwargs: Mapping[str, Any], settings_getter: Callable[[str, Any], Any] | None = None) -> bool:
    """Setting on, Meta key present and external AI allowed for this video."""
    if kwargs.get("allow_external_ai") is not True:
        return False
    from voice_flow import meta_provider

    if not meta_provider.scene_images_setting(settings_getter):
        return False
    return meta_provider.has_api_key()


def _image_size(production: Mapping[str, Any]) -> str:
    return _SIZES.get(str(production.get("size") or "16:9"), _SIZES["16:9"])


def _scene_prompt(scene: Mapping[str, Any], section: Mapping[str, Any] | None, visual_direction: str) -> str:
    section = section or {}
    title = str(scene.get("title") or section.get("title") or "").strip()
    lines = [str(line).strip() for line in (section.get("lecture_lines") or []) if str(line).strip()][:2]
    goal = str(scene.get("learning_goal") or section.get("learning_goal") or "").strip()
    parts = [f'Background illustration for one scene of an explainer video about "{title or "the topic"}".']
    if goal and goal != title:
        parts.append(f"The scene teaches: {goal}.")
    if lines:
        parts.append("Narration: " + " ".join(lines))
    if visual_direction.strip():
        parts.append(f"Visual direction: {visual_direction.strip()}.")
    parts.append(
        "Style: clean, modern, softly lit, uncluttered, with calm empty space where on-screen text will sit. "
        "Do not draw any text, letters, numbers, captions, logos or watermarks."
    )
    return " ".join(parts)[:1500]


def _translucent(background: Any) -> Any:
    if isinstance(background, str):
        match = _HEX.match(background.strip())
        if match:
            value = match.group(1)
            r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
            return f"rgba({r},{g},{b},{OVERLAY_ALPHA})"
    return background


def _with_visual_image(visual: dict[str, Any], src: str) -> dict[str, Any]:
    inner = copy.deepcopy(visual)
    style = dict(inner.get("style") or {})
    if "background" in style:
        style["background"] = _translucent(style["background"])
        inner["style"] = style
    return {
        "type": "group",
        "children": [
            {"type": "image", "src": src, "style": {"fit": "cover"}},
            inner,
        ],
    }


def _with_body_image(body: str, src: str) -> str:
    img = (
        f'<img class="vf-muse-scene-image" src="{escape(src, quote=True)}" alt="" aria-hidden="true" '
        'style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;'
        'opacity:0.28;z-index:-1;pointer-events:none">'
    )
    return img + body


def apply_scene_images(
    production: dict[str, Any],
    storyboard: Mapping[str, Any] | None,
    kwargs: Mapping[str, Any],
    project_dir: Path,
    *,
    report: Callable[..., Any] | None = None,
    generator: ImageGenerator | None = None,
    api_key: str | None = None,
    settings_getter: Callable[[str, Any], Any] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return ``(production, manifest)``; ``production`` is unchanged on any miss."""
    try:
        if not scene_images_requested(kwargs, settings_getter):
            return production, []
        from voice_flow import meta_provider
        from voice_flow.video_flow_contracts import validate_no_executable_code

        key = api_key or meta_provider.resolve_api_key()
        if not key:
            return production, []
        scenes = production.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            return production, []
        renderer = str(production.get("renderer") or "no-browser")
        sections = list((storyboard or {}).get("sections") or [])
        visual_direction = str(kwargs.get("visual_direction") or "")
        size = _image_size(production)
        gen = generator or (
            lambda k, p, s: meta_provider.generate_image(k, p, size=s, timeout=PER_IMAGE_TIMEOUT_SECONDS)
        )

        targets: list[tuple[int, str]] = []
        for index, scene in enumerate(scenes[:MAX_SCENE_IMAGES]):
            if not isinstance(scene, dict):
                continue
            usable = isinstance(scene.get("visual"), dict) if renderer != "hyperframes" else isinstance(scene.get("body"), str)
            if not usable:
                continue
            section = sections[index] if index < len(sections) and isinstance(sections[index], dict) else None
            targets.append((index, _scene_prompt(scene, section, visual_direction)))
        if not targets:
            return production, []

        if report is not None:
            report(43, "Creating scene images with Muse Image", "directing")
        narova_dir = Path(project_dir) / "narova"
        asset_dir = narova_dir / ASSET_DIR
        asset_dir.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + TOTAL_BUDGET_SECONDS

        def work(item: tuple[int, str]) -> tuple[int, str, bytes | None, str]:
            index, prompt = item
            if time.monotonic() > deadline or (is_cancelled is not None and is_cancelled()):
                return index, prompt, None, "skipped"
            try:
                return index, prompt, gen(key, prompt, size), ""
            except Exception as exc:  # one scene failing never fails the video
                return index, prompt, None, exc.__class__.__name__

        with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="muse-image") as pool:
            results = list(pool.map(work, targets))

        updated = copy.deepcopy(production)
        manifest: list[dict[str, Any]] = []
        for index, prompt, data, error in results:
            entry: dict[str, Any] = {"scene_index": index + 1, "model": meta_provider.MUSE_IMAGE, "prompt": prompt}
            if not data:
                entry["status"] = "fallback"
                entry["reason"] = error or "no_image"
                manifest.append(entry)
                continue
            rel = f"{ASSET_DIR}/scene-{index + 1:02d}.png"
            try:
                (narova_dir / rel).write_bytes(data)
            except OSError as exc:
                entry.update(status="fallback", reason=exc.__class__.__name__)
                manifest.append(entry)
                continue
            scene = updated["scenes"][index]
            if renderer == "hyperframes":
                scene["body"] = _with_body_image(scene["body"], rel)
            else:
                scene["visual"] = _with_visual_image(scene["visual"], rel)
            entry.update(status="used", file=f"narova/{rel}")
            manifest.append(entry)

        try:
            plan_dir = Path(project_dir) / "plan"
            plan_dir.mkdir(parents=True, exist_ok=True)
            (plan_dir / "muse_scene_images.json").write_text(
                json.dumps({"provider": meta_provider.PROVIDER_ID, "images": manifest}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

        if not any(item.get("status") == "used" for item in manifest):
            return production, manifest
        validate_no_executable_code({"scenes": updated["scenes"]})
        return updated, manifest
    except Exception as exc:
        logger.warning("Muse Image scene images skipped (%s)", exc.__class__.__name__)
        return production, []


__all__ = ["MAX_SCENE_IMAGES", "apply_scene_images", "scene_images_requested"]
