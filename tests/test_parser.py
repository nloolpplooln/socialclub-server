"""解析层离线测试：不依赖网络与账号，用构造的 HTML 样本验证抽取逻辑。"""
from __future__ import annotations

from app.services import parser


SL_SAMPLE = """
<html><body>
<script>
    var settings = window.SCSettings;
    if (settings != undefined) {
        settings.VehiclesJson = /*<sl:translate_json>*/{"VehicleCollections":[{"grg":[{"Name":"Imponte Ruiner 2000","VehicleType":"CAR"}]}]}/*</sl:translate_json>*/;
        settings.nickname = 'restlessnarwhal';
    }
</script>
</body></html>
"""

NEXT_SAMPLE = """
<html><body>
<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"nickname":"foo","rockstarId":12345}}}</script>
</body></html>
"""

AUTH_BLOCKED = '<html><head></head><body><form id="signInForm"></form></body></html>'


def test_extract_sl_translate_json():
    embedded = parser.extract_embedded_json(SL_SAMPLE)
    assert "sl_translate" in embedded
    block = embedded["sl_translate"][0]
    assert block["VehicleCollections"][0]["grg"][0]["Name"] == "Imponte Ruiner 2000"


def test_extract_next_data():
    embedded = parser.extract_embedded_json(NEXT_SAMPLE)
    assert "next_data" in embedded
    assert embedded["next_data"]["props"]["pageProps"]["rockstarId"] == 12345


def test_auth_blocked_detection():
    assert parser.is_auth_blocked("", "https://socialclub.rockstargames.com/Blocker/AuthCheck")
    assert parser.is_auth_blocked(AUTH_BLOCKED, "")
    assert not parser.is_auth_blocked(SL_SAMPLE, "https://socialclub.rockstargames.com/member/x")


def test_map_player_never_raises_on_empty():
    result = parser.map_player({})
    assert result["nickname"] is None
    assert result["former_names"] == []
    assert result["raw_keys"] == []


def test_map_player_reports_hit_strategies():
    embedded = parser.extract_embedded_json(SL_SAMPLE)
    result = parser.map_player(embedded)
    assert "sl_translate" in result["raw_keys"]
