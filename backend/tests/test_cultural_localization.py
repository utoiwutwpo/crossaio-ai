"""文化本地化层：市场画像 / prompt 注入 / 确定性适配评分 / 生成链路集成。"""
from tests.conftest import register_and_login

from app.experts.cultural_localization import (
    MARKET_PROFILES, profile_for, cultural_prompt_block, score_cultural_fit,
)


# ---------- 纯单元：画像与评分 ----------
def test_profile_for_platform_language_fallback():
    # otto 默认德语 → 德国画像
    p = profile_for("otto", None)
    assert p["market"].startswith("德国")
    # allegro 默认波兰语
    assert profile_for("allegro", None)["market"].startswith("波兰")
    # 显式语言覆盖平台默认
    assert profile_for("amazon", "fr")["market"].startswith("法国")
    # 无画像语言 → None
    assert profile_for("amazon", "ar") is None
    # 未知平台 + 未指定语言 → None（不抛异常）
    assert profile_for("nope", None) is None
    # 未知平台但显式合法语言 → 仍按语言生效
    assert profile_for("nope", "de")["market"].startswith("德国")


def test_cultural_prompt_block_contains_market_rules():
    block = cultural_prompt_block(MARKET_PROFILES["de"])
    assert "文化本地化" in block
    assert "德国" in block
    assert "TÜV" in block          # 信任信号进 prompt
    assert "Loi Toubon" in cultural_prompt_block(MARKET_PROFILES["fr"])
    assert "Allegro Smart" in cultural_prompt_block(MARKET_PROFILES["pl"])


def test_score_cultural_fit_penalizes_avoid_words_and_rewards_signals():
    de = MARKET_PROFILES["de"]
    # 命中信任信号 + 参数 → 高分；含禁用词 → gaps 提示
    good = score_cultural_fit(
        "Kopfhörer mit CE und TÜV, 40mm Treiber",
        ["Akku 30 Std.", "2 Jahre Garantie", "Recycling-fähig"],
        "Schadstoffgeprüft, präzise Technik.", de)
    bad = score_cultural_fit(
        "Beste Kopfhörer!!! Weltbeste Wunder",
        ["super mega", "no signal"], "absolut 100% sicher!!!", de)
    assert good["score"] > bad["score"]
    assert any("禁用" in g or "禁用" in g for g in bad["gaps"]) or bad["gaps"]
    assert good["hits"]


# ---------- API：画像端点（免费营销信息） ----------
def test_cultural_profiles_endpoint(client):
    r = client.get("/api/v1/products/descriptions/cultural-profiles")
    assert r.status_code == 200, r.text
    profiles = r.json()["profiles"]
    langs = {p["lang"] for p in profiles}
    assert {"de", "fr", "it", "pl", "nl", "ro"} <= langs
    de = next(p for p in profiles if p["lang"] == "de")
    assert de["buyer_priorities"][0] == "认证与安全背书"


def test_cultural_profile_single_platform(client):
    r = client.get("/api/v1/products/descriptions/cultural-profile/otto")
    assert r.status_code == 200
    assert r.json()["market"].startswith("德国")
    # 覆盖语言
    r2 = client.get("/api/v1/products/descriptions/cultural-profile/amazon?language=it")
    assert r2.status_code == 200
    assert r2.json()["market"].startswith("意大利")
    # 未知平台
    assert client.get(
        "/api/v1/products/descriptions/cultural-profile/nope").status_code == 404


# ---------- 生成链路集成（Mock LLM） ----------
def test_generate_includes_cultural_fields(client):
    headers = register_and_login(client, "cult1@test.com")
    r = client.post("/api/v1/products/descriptions/generate", headers=headers, json={
        "product_name": "Wireless Noise Cancelling Headphones",
        "keywords": ["wireless", "bluetooth"],
        "platform": "otto",   # 默认德语 → 应带德国画像
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["cultural_market"] == "德国 (DE/AT)"
    assert d["cultural_score"] is not None
    assert isinstance(d["cultural_gaps"], list)
    assert 0 <= d["cultural_score"] <= 100


def test_generate_cultural_disabled(client):
    headers = register_and_login(client, "cult2@test.com")
    r = client.post("/api/v1/products/descriptions/generate", headers=headers, json={
        "product_name": "Wireless Noise Cancelling Headphones",
        "keywords": ["wireless", "bluetooth"],
        "platform": "otto",
        "cultural_adaptation": False,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["cultural_market"] is None
    assert d["cultural_score"] is None
