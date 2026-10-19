"""Meta Model API provider: Muse Spark routing + Muse Image (all HTTP mocked).

No real key is used anywhere; the fake keys below only follow the documented
``LLM|{numeric_id}|{secret}`` shape.
"""

from __future__ import annotations

import base64
import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from voice_flow import meta_provider
from voice_flow.meta_provider import (
    MUSE_IMAGE,
    MUSE_SPARK_11,
    MUSE_SPARK_12,
    MUSE_SPARK_13,
    choose_model,
)

FAKE_KEY = "LLM|1234567890|fake-secret-for-tests"
SERVED = [MUSE_SPARK_13, MUSE_SPARK_12, MUSE_SPARK_11, "muse-spark-1.3-contributor", "muse-wonder-1.0", MUSE_IMAGE, "sam-3.1"]
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class FakeHTTP:
    """Records every request; answers /models, /chat/completions and /images/generations."""

    def __init__(
        self,
        models: list[str] | None = None,
        chat_content: str = "Polished text.",
        fail_models: int | None = None,
        image_body: dict[str, Any] | None = None,
        fail_images: int | None = None,
        download: bytes = PNG_BYTES,
    ):
        self.models = SERVED if models is None else models
        self.chat_content = chat_content
        self.fail_models = fail_models
        self.image_body = image_body if image_body is not None else {"created": 1, "data": [{"b64_json": PNG_B64}], "output_format": "png"}
        self.fail_images = fail_images
        self.download = download
        self.calls: list[dict[str, Any]] = []

    def __call__(self, request, timeout=None):
        url = request.full_url
        headers = {k.lower(): v for k, v in request.header_items()}
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        self.calls.append({"url": url, "headers": headers, "body": body, "method": request.get_method(), "timeout": timeout})
        if url.endswith("/models"):
            if self.fail_models:
                raise urllib.error.HTTPError(url, self.fail_models, "nope", {}, io.BytesIO(b'{"error":{"message":"bad key"}}'))
            return _Response(json.dumps({"object": "list", "data": [{"id": m, "object": "model"} for m in self.models]}).encode())
        if url.endswith("/chat/completions"):
            return _Response(json.dumps({"choices": [{"message": {"content": self.chat_content, "reasoning_content": ""}, "finish_reason": "stop"}]}).encode())
        if url.endswith("/images/generations"):
            if self.fail_images:
                raise urllib.error.HTTPError(url, self.fail_images, "nope", {}, io.BytesIO(b'{"error":{"message":"no"}}'))
            return _Response(json.dumps(self.image_body).encode())
        if url.startswith("https://cdn.example.test/"):
            return _Response(self.download)
        raise AssertionError(f"unexpected URL {url}")


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    meta_provider.clear_model_cache()
    yield
    meta_provider.clear_model_cache()


@pytest.fixture
def no_network(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("network must not be used without a key")

    monkeypatch.setattr("urllib.request.urlopen", _boom)


@pytest.fixture
def provider_service(tmp_path, monkeypatch):
    from voice_flow import video_flow_providers as providers_module

    service = providers_module.VideoFlowProviderService(str(tmp_path / "voice-flow.db"))
    monkeypatch.setattr(providers_module, "video_flow_provider_service", service)
    return service


# --- registration ----------------------------------------------------------


def test_meta_is_registered_like_other_openai_compatible_providers():
    from voice_flow import polisher, provider_registry, video_flow_providers, video_flow_service

    spec = provider_registry.get_provider_spec("meta_model_api")
    assert spec is not None and spec.transport.format == "openai" and spec.transport.auth_header == "bearer"
    assert spec.transport.base_url == "https://api.meta.ai/v1/chat/completions"
    assert spec.transport.validate_url == "https://api.meta.ai/v1/models"

    entry = video_flow_providers.PROVIDER_BY_ID["meta_model_api"]
    assert entry["category"] == "api_key" and entry["auth"] == "api_key" and entry["prefix"] == "meta_model_api"
    assert entry["env_key"] == "MODEL_API_KEY"
    seeded = {model for provider, model, _name, _caps in video_flow_providers.DEFAULT_MODELS if provider == "meta_model_api"}
    assert {MUSE_SPARK_13, MUSE_SPARK_12, MUSE_SPARK_11, "muse-auto"} <= seeded

    assert video_flow_service._PLANNING_ENDPOINTS["meta_model_api"] == "https://api.meta.ai/v1/chat/completions"
    assert polisher.OPENAI_COMPATIBLE_PROVIDERS["meta_model_api"] == ("https://api.meta.ai/v1/chat/completions", MUSE_SPARK_13)
    assert meta_provider.BASE_URL == "https://api.meta.ai/v1/"
    assert meta_provider.IMAGES_GENERATIONS_URL == "https://api.meta.ai/v1/images/generations"


def test_nebius_stays_the_default_and_meta_is_never_auto_picked():
    from voice_flow import nebius_provider, video_flow_service
    import inspect

    assert nebius_provider.PROVIDER_ID == "nebius"
    # Meta is not in any automatic fallback chain; it runs only when picked.
    source = inspect.getsource(video_flow_service.ProviderModelGateway.from_storage)
    assert "meta_model_api" not in source


def test_key_format_hint():
    assert meta_provider.looks_like_meta_key(FAKE_KEY)
    assert not meta_provider.looks_like_meta_key("sk-something")
    assert not meta_provider.looks_like_meta_key("")


# --- model list + routing --------------------------------------------------


def test_model_list_uses_bearer_auth_and_is_cached(monkeypatch):
    http = FakeHTTP()
    monkeypatch.setattr("urllib.request.urlopen", http)
    assert meta_provider.fetch_model_ids(FAKE_KEY) == SERVED
    assert meta_provider.fetch_model_ids(FAKE_KEY) == SERVED  # cached
    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["url"] == "https://api.meta.ai/v1/models"
    assert call["method"] == "GET"
    assert call["headers"]["authorization"] == f"Bearer {FAKE_KEY}"


def test_model_list_failure_is_graceful(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP(fail_models=503))
    assert meta_provider.fetch_model_ids(FAKE_KEY) is None
    assert meta_provider.resolve_model("", api_key=FAKE_KEY, settings_getter=lambda k, d=None: d) == MUSE_SPARK_13


def test_non_blocking_fetch_never_waits_on_cold_cache(monkeypatch):
    started = []
    monkeypatch.setattr(meta_provider, "warm_model_cache_async", lambda key, timeout=8.0: started.append(key))
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("blocked")))
    assert meta_provider.fetch_model_ids(FAKE_KEY, blocking=False) is None
    assert started == [FAKE_KEY]


@pytest.mark.parametrize(
    "available, preferred, expected",
    [
        (SERVED, [], MUSE_SPARK_13),
        ([MUSE_SPARK_12, MUSE_SPARK_11], [], MUSE_SPARK_12),  # 1.3 not served
        ([MUSE_SPARK_11, MUSE_IMAGE], [], MUSE_SPARK_11),  # only 1.1 served
        (SERVED, [MUSE_SPARK_11], MUSE_SPARK_11),  # user override honoured
        (SERVED, ["muse-spark-9.9"], MUSE_SPARK_13),  # bad override falls back
        (None, [], MUSE_SPARK_13),  # list unknown
        (None, ["my-custom-muse"], "my-custom-muse"),
        (["MUSE-SPARK-1.3"], [], "MUSE-SPARK-1.3"),  # case-insensitive
        (["muse-spark-1.4", "muse-spark-1.3-contributor"], [], "muse-spark-1.4"),  # renamed id, newest Standard
        (["muse-spark-1.3-contributor", MUSE_IMAGE], [], MUSE_SPARK_13),  # never auto-pick Contributor mode
        (["muse-wonder-1.0", MUSE_IMAGE], [], MUSE_SPARK_13),  # never auto-pick another model line
        (SERVED, ["muse-spark-1.3-contributor"], "muse-spark-1.3-contributor"),  # explicit pick honoured
    ],
)
def test_choose_model(available, preferred, expected):
    assert choose_model(available, preferred) == expected


def test_aliases_and_explicit_models():
    assert meta_provider.split_requested_model("muse-auto") == ""
    assert meta_provider.split_requested_model("") == ""
    assert meta_provider.split_requested_model("meta_model_api/" + MUSE_SPARK_12) == MUSE_SPARK_12
    assert meta_provider.split_requested_model(MUSE_SPARK_11) == MUSE_SPARK_11


def test_text_override_is_saved_and_used(provider_service, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP())
    meta_provider.set_text_model_override("meta_model_api/" + MUSE_SPARK_12, provider_service)
    assert provider_service.get_setting("meta_model_text") == MUSE_SPARK_12
    assert meta_provider.resolve_model("muse-auto", api_key=FAKE_KEY, settings_getter=provider_service.get_setting) == MUSE_SPARK_12
    meta_provider.set_text_model_override("", provider_service)
    assert meta_provider.resolve_model("muse-auto", api_key=FAKE_KEY, settings_getter=provider_service.get_setting) == MUSE_SPARK_13
    with pytest.raises(ValueError):
        meta_provider.set_text_model_override("bad model id!", provider_service)


def test_strip_reasoning_is_defensive():
    assert meta_provider.strip_reasoning("<think>plan</think>\nHello.") == "Hello."
    assert meta_provider.strip_reasoning("Plain answer") == "Plain answer"


def test_scene_images_setting_is_off_by_default(provider_service):
    assert meta_provider.scene_images_setting(provider_service.get_setting) is False
    meta_provider.set_scene_images(True, provider_service)
    assert meta_provider.scene_images_setting(provider_service.get_setting) is True
    meta_provider.set_scene_images("false", provider_service)
    assert meta_provider.scene_images_setting(provider_service.get_setting) is False


# --- keys: saved connection, env var, or nothing ---------------------------


def test_no_key_means_no_calls(provider_service, no_network):
    from voice_flow.video_flow_service import ProviderModelGateway
    from voice_flow.voice_polish_bridge import can_execute_model

    assert meta_provider.resolve_api_key(provider_service) == ""
    assert ProviderModelGateway._from_video_provider_service("meta_model_api", "") is None
    assert can_execute_model("meta_model_api/muse-auto") is False
    public = provider_service._public_provider(provider_service.provider("meta_model_api"))
    assert public["status"] == "disconnected"
    summary = meta_provider.routing_summary(service=provider_service)
    assert summary["has_key"] is False and summary["scene_images"]["enabled"] is False


def test_env_key_is_used_when_nothing_is_saved(provider_service, monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", FAKE_KEY)
    assert meta_provider.resolve_api_key(provider_service) == FAKE_KEY
    public = provider_service._public_provider(provider_service.provider("meta_model_api"))
    assert public["status"] == "connected" and public.get("env_key_in_use") is True


def test_saved_connection_wins_over_env(provider_service, monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "LLM|1|env")
    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    assert meta_provider.resolve_api_key(provider_service) == FAKE_KEY


# --- Settings "Test" button -----------------------------------------------


def test_settings_test_button_calls_v1_models(provider_service, monkeypatch):
    http = FakeHTTP()
    monkeypatch.setattr("urllib.request.urlopen", http)
    conn = provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    result = provider_service.test_connection(conn["id"])
    assert result["success"] is True and result["status"] == "connected"
    assert result["routing"] == {"text": MUSE_SPARK_13}
    assert result["image_model_served"] is True and result["key_format_ok"] is True
    assert http.calls[0]["url"] == "https://api.meta.ai/v1/models"
    assert http.calls[0]["headers"]["authorization"] == f"Bearer {FAKE_KEY}"
    assert provider_service.get_connection(conn["id"])["status"] == "connected"
    details = provider_service.provider_details("meta_model_api")
    assert details["meta_routing"]["validated"] is True
    assert details["meta_routing"]["text"]["resolved"] == MUSE_SPARK_13
    assert details["meta_routing"]["scene_images"]["served"] is True


def test_settings_test_button_reports_bad_key(provider_service, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP(fail_models=401))
    conn = provider_service.add_connection("meta_model_api", name="Main", secret="bad")
    result = provider_service.test_connection(conn["id"])
    assert result["success"] is False and "401" in result["error"]
    assert provider_service.get_connection(conn["id"])["status"] == "error"


# --- the three flows -------------------------------------------------------


def test_video_flow_gateway_uses_muse_spark(provider_service, monkeypatch):
    from voice_flow.video_flow_service import ProviderModelGateway

    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP())
    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    gateway = ProviderModelGateway._from_video_provider_service("meta_model_api", "")
    assert gateway is not None
    assert gateway._model_id == MUSE_SPARK_13
    assert gateway._endpoint == "https://api.meta.ai/v1/chat/completions"
    assert gateway._api_key == FAKE_KEY

    gateway = ProviderModelGateway._from_video_provider_service("meta_model_api", "muse-retired-model")
    assert gateway._model_id == MUSE_SPARK_13

    class _Storage:
        def get_setting(self, key, default=None):
            return default

        def get_provider_connections(self, provider):
            return []

    gateway = ProviderModelGateway.from_storage(_Storage(), "meta_model_api/muse-auto")
    assert gateway._provider == "meta_model_api" and gateway._model_id == MUSE_SPARK_13


def test_video_flow_falls_back_to_1_2_then_1_1(provider_service, monkeypatch):
    from voice_flow.video_flow_service import ProviderModelGateway

    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP(models=[MUSE_SPARK_12, MUSE_SPARK_11]))
    assert ProviderModelGateway._from_video_provider_service("meta_model_api", "")._model_id == MUSE_SPARK_12
    meta_provider.clear_model_cache()
    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP(models=[MUSE_SPARK_11]))
    assert ProviderModelGateway._from_video_provider_service("meta_model_api", "")._model_id == MUSE_SPARK_11


def test_voice_polish_uses_meta(provider_service, monkeypatch):
    from voice_flow import voice_polish_bridge
    from voice_flow import voice_provider_transport

    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP())
    meta_provider.fetch_model_ids(FAKE_KEY)

    sent = {}

    def fake_request_chat(**kwargs):
        sent.update(kwargs)
        return "Hello, world.", "ok"

    monkeypatch.setattr(voice_provider_transport, "request_chat", fake_request_chat)
    assert voice_polish_bridge.can_execute_model("meta_model_api/muse-auto") is True
    out = voice_polish_bridge.request_polish("meta_model_api/muse-auto", "hello world", timeout_seconds=3.0)
    assert out == "Hello, world."
    assert sent["model"] == MUSE_SPARK_13
    assert sent["endpoint"] == "https://api.meta.ai/v1/chat/completions"
    assert sent["api_key"] == FAKE_KEY


def test_voice_polish_cold_cache_does_not_block(provider_service, monkeypatch):
    from voice_flow import voice_polish_bridge
    from voice_flow import voice_provider_transport

    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    monkeypatch.setattr(meta_provider, "warm_model_cache_async", lambda *a, **k: None)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("blocked on /models")))
    sent = {}
    monkeypatch.setattr(voice_provider_transport, "request_chat", lambda **kw: (sent.update(kw) or ("Hi.", "ok")))
    assert voice_polish_bridge.request_polish("meta_model_api/muse-auto", "hi", timeout_seconds=2.0) == "Hi."
    assert sent["model"] == MUSE_SPARK_13


def test_audio_flow_summary_uses_meta(provider_service, monkeypatch):
    from voice_flow import audio_summary

    monkeypatch.setattr(audio_summary, "video_flow_provider_service", provider_service)
    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    http = FakeHTTP(chat_content="A short spoken summary.")
    monkeypatch.setattr("urllib.request.urlopen", http)
    service = audio_summary.AudioSummaryService()
    text = service._dispatch_llm_prompt("Summarise this.", "meta_model_api/muse-auto", service_label="Audio Summary")
    assert text == "A short spoken summary."
    chat = [c for c in http.calls if c["url"].endswith("/chat/completions")][0]
    assert chat["url"] == "https://api.meta.ai/v1/chat/completions"
    assert chat["body"]["model"] == MUSE_SPARK_13
    assert chat["headers"]["authorization"] == f"Bearer {FAKE_KEY}"


def test_audio_flow_without_key_raises_clear_error(provider_service, monkeypatch, no_network):
    from voice_flow import audio_summary

    monkeypatch.setattr(audio_summary, "video_flow_provider_service", provider_service)
    with pytest.raises(audio_summary.AudioSummaryError):
        audio_summary.AudioSummaryService()._dispatch_llm_prompt("x", "meta_model_api/muse-auto")


# --- Muse Image ------------------------------------------------------------


def test_generate_image_request_shape_and_b64_response(monkeypatch):
    http = FakeHTTP()
    monkeypatch.setattr("urllib.request.urlopen", http)
    data = meta_provider.generate_image(FAKE_KEY, "a calm lake", size="1600x900")
    assert data == PNG_BYTES
    call = http.calls[0]
    assert call["url"] == "https://api.meta.ai/v1/images/generations" and call["method"] == "POST"
    assert call["headers"]["authorization"] == f"Bearer {FAKE_KEY}"
    assert call["body"]["model"] == MUSE_IMAGE
    assert call["body"]["prompt"] == "a calm lake"
    assert call["body"]["n"] == 1 and call["body"]["size"] == "1600x900"
    assert call["body"]["response_format"] == "b64_json" and call["body"]["output_format"] == "png"


def test_generate_image_follows_url_without_forwarding_the_key(monkeypatch):
    http = FakeHTTP(image_body={"created": 1, "data": [{"url": "https://cdn.example.test/img.png"}]})
    monkeypatch.setattr("urllib.request.urlopen", http)
    assert meta_provider.generate_image(FAKE_KEY, "x") == PNG_BYTES
    download = http.calls[1]
    assert download["url"] == "https://cdn.example.test/img.png"
    assert "authorization" not in download["headers"]


@pytest.mark.parametrize(
    "http",
    [
        FakeHTTP(fail_images=429),
        FakeHTTP(image_body={"created": 1, "data": []}),
        FakeHTTP(image_body={"created": 1, "data": [{"b64_json": base64.b64encode(b"not an image").decode()}]}),
        FakeHTTP(image_body={"created": 1, "data": [{"url": "http://insecure.example.test/x.png"}]}),
    ],
)
def test_generate_image_errors_are_muse_image_errors(monkeypatch, http):
    monkeypatch.setattr("urllib.request.urlopen", http)
    with pytest.raises(meta_provider.MuseImageError):
        meta_provider.generate_image(FAKE_KEY, "x")


def test_generate_image_without_key_makes_no_call(no_network):
    with pytest.raises(meta_provider.MuseImageError):
        meta_provider.generate_image("", "x")


# --- Video Flow scene images ----------------------------------------------


def _legacy_production() -> tuple[dict[str, Any], dict[str, Any]]:
    from voice_flow.video_flow_engine.bridge import build_narova_production

    storyboard = {
        "topic": "Photosynthesis",
        "sections": [
            {"id": "s1", "title": "Light in", "lecture_lines": ["Leaves catch sunlight.", "Chlorophyll absorbs it."]},
            {"id": "s2", "title": "Sugar out", "lecture_lines": ["The plant makes glucose."]},
        ],
    }
    return build_narova_production(storyboard, title="Photosynthesis"), storyboard


@pytest.fixture
def scene_images_on(provider_service, monkeypatch):
    meta_provider.set_scene_images(True, provider_service)
    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    return provider_service


def test_scene_images_off_by_default_makes_no_call(provider_service, tmp_path, no_network):
    from voice_flow.video_flow_engine.muse_scene_images import apply_scene_images

    provider_service.add_connection("meta_model_api", name="Main", secret=FAKE_KEY)
    production, storyboard = _legacy_production()
    out, manifest = apply_scene_images(production, storyboard, {"allow_external_ai": True}, tmp_path)
    assert out is production and manifest == []


def test_scene_images_need_external_ai_consent(scene_images_on, tmp_path, no_network):
    from voice_flow.video_flow_engine.muse_scene_images import apply_scene_images

    production, storyboard = _legacy_production()
    out, _ = apply_scene_images(production, storyboard, {"allow_external_ai": False}, tmp_path)
    assert out is production


def test_scene_images_without_key_make_no_call(provider_service, tmp_path, no_network):
    from voice_flow.video_flow_engine.muse_scene_images import apply_scene_images

    meta_provider.set_scene_images(True, provider_service)
    production, storyboard = _legacy_production()
    out, _ = apply_scene_images(production, storyboard, {"allow_external_ai": True}, tmp_path)
    assert out is production


def test_scene_images_are_layered_behind_portable_visuals(scene_images_on, tmp_path, monkeypatch):
    from voice_flow.video_flow_engine.muse_scene_images import apply_scene_images

    http = FakeHTTP()
    monkeypatch.setattr("urllib.request.urlopen", http)
    production, storyboard = _legacy_production()
    before = json.dumps(production, sort_keys=True)
    out, manifest = apply_scene_images(production, storyboard, {"allow_external_ai": True, "visual_direction": "warm"}, tmp_path)

    assert json.dumps(production, sort_keys=True) == before  # original untouched
    assert [m["status"] for m in manifest] == ["used", "used"]
    for index, scene in enumerate(out["scenes"], start=1):
        visual = scene["visual"]
        assert visual["type"] == "group"
        image, inner = visual["children"]
        assert image == {"type": "image", "src": f"assets/muse/scene-{index:02d}.png", "style": {"fit": "cover"}}
        assert inner["style"]["background"].startswith("rgba(11,16,32,")
        assert (tmp_path / "narova" / "assets" / "muse" / f"scene-{index:02d}.png").read_bytes() == PNG_BYTES
    prompts = [c["body"]["prompt"] for c in http.calls if c["url"].endswith("/images/generations")]
    assert len(prompts) == 2 and all("Do not draw any text" in p for p in prompts)
    assert any("Light in" in p for p in prompts)
    saved = json.loads((tmp_path / "plan" / "muse_scene_images.json").read_text(encoding="utf-8"))
    assert saved["provider"] == "meta_model_api" and len(saved["images"]) == 2


def test_scene_images_on_browser_scenes_prepend_a_backdrop(scene_images_on, tmp_path):
    from voice_flow.video_flow_engine.muse_scene_images import apply_scene_images

    production = {
        "renderer": "hyperframes",
        "size": "9:16",
        "scenes": [{"id": "s1", "title": "One", "body": "<section>Hi</section>"}],
    }
    sizes = []
    out, manifest = apply_scene_images(
        production, {"sections": []}, {"allow_external_ai": True}, tmp_path,
        generator=lambda key, prompt, size: (sizes.append(size) or PNG_BYTES),
    )
    assert sizes == ["900x1600"]
    body = out["scenes"][0]["body"]
    assert body.startswith('<img class="vf-muse-scene-image" src="assets/muse/scene-01.png"')
    assert body.endswith("<section>Hi</section>")
    assert manifest[0]["status"] == "used"


def test_one_failed_scene_keeps_its_visuals(scene_images_on, tmp_path):
    from voice_flow.video_flow_engine.muse_scene_images import apply_scene_images

    production, storyboard = _legacy_production()

    def gen(key, prompt, size):
        if "Sugar out" in prompt:
            raise meta_provider.MuseImageError("HTTP 500")
        return PNG_BYTES

    out, manifest = apply_scene_images(production, storyboard, {"allow_external_ai": True}, tmp_path, generator=gen)
    assert out["scenes"][0]["visual"]["type"] == "group"
    assert out["scenes"][1]["visual"] == production["scenes"][1]["visual"]
    assert [m["status"] for m in manifest] == ["used", "fallback"]


def test_all_failed_returns_original_production(scene_images_on, tmp_path, monkeypatch):
    from voice_flow.video_flow_engine.muse_scene_images import apply_scene_images

    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP(fail_images=500))
    production, storyboard = _legacy_production()
    out, manifest = apply_scene_images(production, storyboard, {"allow_external_ai": True}, tmp_path)
    assert out is production
    assert manifest and all(m["status"] == "fallback" for m in manifest)


def test_engine_rerenders_with_standard_visuals_if_image_render_fails(scene_images_on, tmp_path, monkeypatch):
    from voice_flow.video_flow_engine.engine import VideoFlowEngine
    from voice_flow.video_flow_engine.sandbox import EngineError

    monkeypatch.setattr("urllib.request.urlopen", FakeHTTP())
    _production, storyboard = _legacy_production()

    class Planner:
        def plan(self, source_text, **_kwargs):
            return storyboard

    class Renderer:
        def __init__(self):
            self.productions = []

        def render(self, production, project_dir, **_kwargs):
            self.productions.append(production)
            if any(scene["visual"].get("type") == "group" for scene in production["scenes"]):
                raise EngineError("render_failed", "image decode failed")
            path = Path(project_dir) / "video.mp4"
            path.write_bytes(b"video")
            return path

    renderer = Renderer()
    engine = VideoFlowEngine(planner=Planner(), renderer=renderer)
    monkeypatch.setattr(VideoFlowEngine, "_build_production", lambda self, sb, kw, pd, rp, **k: self._legacy_production(sb, kw))
    result = engine.run(
        "vf-meta-test",
        source_text="Photosynthesis turns light into sugar.",
        projects_root=str(tmp_path),
        allow_external_ai=False,
        duration_seconds=30,
        format="short",
    )
    # allow_external_ai False: images are never requested, one plain render.
    assert result["state"] == "complete" and len(renderer.productions) == 1

    renderer.productions.clear()
    result = engine.run(
        "vf-meta-test-2",
        source_text="Photosynthesis turns light into sugar.",
        projects_root=str(tmp_path),
        allow_external_ai=True,
        duration_seconds=30,
        format="short",
    )
    assert result["state"] == "complete"
    assert len(renderer.productions) == 2
    assert renderer.productions[0]["scenes"][0]["visual"]["type"] == "group"
    assert renderer.productions[1]["scenes"][0]["visual"]["type"] == "stack"
    assert (tmp_path / "vf-meta-test-2" / "plan" / "muse_scene_images.json").is_file()
