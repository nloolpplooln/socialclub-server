"""[已废弃] 网页路径数据源探测 —— 被 `python -m app.cli probe <nick>` 取代。

网页路径已证明走不通（跳 OAuth 授权页）。现用 scapi + token 刷新,凭证注入与探测见
app/cli.py（setck / refresh / profile / probe）。本脚本保留仅作历史参考。

--- 原说明 ---
阶段0：数据源可行性验证。

用法：
    1. 先把浏览器登录 socialclub 后的 Cookie 填进 .env 的 RSC_COOKIE
    2. python scripts/probe_login.py <玩家昵称>

作用：带 Cookie 抓取该玩家的 Social Club 页面，判断：
    - 登录态是否有效（是否被挡在 /Blocker/AuthCheck）
    - 页面里能否抽出嵌入 JSON
并把原始 HTML 存到 samples/ 供分析、把抽到的 JSON 打印出来，
用于校准 parser.map_player() 的字段映射。

这是整个项目的地基：跑通 = 数据源可用；跑不通 = 先在这里止损。
"""
from __future__ import annotations

import json
import os
import sys

# 允许直接 `python scripts/probe_login.py` 运行时找到 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.services import collector, parser  # noqa: E402

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


def main(nickname: str) -> int:
    s = get_settings()
    if not s.rsc_cookie:
        print("✗ 未配置 RSC_COOKIE。请先在 .env 填入登录后的 Cookie。")
        return 2

    os.makedirs(SAMPLES_DIR, exist_ok=True)

    for tpl in collector.MEMBER_PATHS:
        path = tpl.format(nick=nickname)
        print(f"\n=== 请求 {collector.BASE}{path} ===")
        try:
            res = collector.fetch(path)
        except collector.AuthExpiredError as exc:
            print(f"✗ 登录态失效：{exc}")
            print("  → 请重新在浏览器登录并更新 .env 里的 RSC_COOKIE")
            return 3
        except collector.CollectError as exc:
            print(f"✗ 采集失败：{exc}")
            continue

        # 保存原始 HTML 供分析
        safe = "".join(c if c.isalnum() else "_" for c in nickname)
        fname = os.path.join(SAMPLES_DIR, f"{safe}{path.replace('/', '_')}.html")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(res.html)
        print(f"  HTTP {res.status_code}  final={res.final_url}")
        print(f"  原始 HTML 已存：{fname}  ({len(res.html)} bytes)")

        embedded = parser.extract_embedded_json(res.html)
        if not embedded:
            print("  ⚠ 未抽到嵌入 JSON（页面结构可能已变，需查看上面保存的 HTML）")
            continue

        print(f"  ✓ 命中策略：{sorted(embedded.keys())}")
        print("  ---- 抽取到的 JSON（截断预览）----")
        preview = json.dumps(embedded, ensure_ascii=False, indent=2)
        print(preview[:2000] + ("\n  ...(截断)" if len(preview) > 2000 else ""))
        print("\n  ---- map_player 映射结果 ----")
        print(json.dumps(parser.map_player(embedded), ensure_ascii=False, indent=2))
        return 0

    print("\n✗ 所有候选路径都没拿到可解析数据。")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/probe_login.py <玩家昵称>")
        sys.exit(64)
    sys.exit(main(sys.argv[1]))
