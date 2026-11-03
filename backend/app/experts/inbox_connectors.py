"""
统一收件箱平台连接器（Connector 骨架）— 补齐「规模瓶颈」的第一步。

诚实边界（与 inbox.py 顶部声明一致）：
- 本模块提供「连接器状态 + 手动批量导入」的真实能力：卖家可以把 Allegro /
  OTTO / Kaufland 卖家中心后台的买家消息按模板粘贴导入，统一进入收件箱，
  出站回复自动过组合工作流（GPSR + Art.50 + 平台语言）。
- 各平台「实时 API 同步」需要正式的合作伙伴接入（Allegro REST API + OAuth2、
  OTTO Partner Programme、Kaufland Seller API），凭证就绪前导入模式固定为
  manual —— 本模块绝不虚报「已对接」。

设计：eBay 是已接入的参照系（ebay.py OAuth 全流程）；本骨架让欧洲本地三大
增长平台（Kaufland 国际业务同比 +124%）先获得「导入 → 统一回复」的闭环。
"""
import os
from typing import Callable, Dict, List, Optional

from .platform_registry import platform_config

# 各平台连接器定义。credentials 环境变量名与真实平台开发者后台一一对应，
# 便于凭证到位后零改动升级为 API 同步。
CONNECTORS: Dict[str, Dict] = {
    "allegro": {
        "display": "Allegro",
        "api_basis": "Allegro REST API (developer.allegro.pl) + OAuth2 device flow",
        "sync_mode": "manual",          # manual → api（凭证就绪后切换）
        "credentials": ["CROSSBOT_CRED_ALLEGRO_CLIENT_ID",
                        "CROSSBOT_CRED_ALLEGRO_CLIENT_SECRET"],
        "credential_setup": "developer.allegro.pl 创建应用 → 获取 Client ID/Secret → "
                            "OAuth2 device flow 授权",
        "growth_note": "中东欧头部平台（PL/CZ/HU/SK），波兰买家 88% 以配送速度为下单参考",
        "import_template": {
            "buyer_id": "allegro_klient_01",
            "subject": "Return question / Pytanie o zwrot",
            "messages": ["Witam, czy mogę zwrócić towar w ciągu 14 dni?"],
        },
    },
    "otto": {
        "display": "Otto",
        "api_basis": "Otto Market Partner API (partner.otto.market) + OAuth2",
        "sync_mode": "manual",
        "credentials": ["CROSSBOT_CRED_OTTO_CLIENT_ID",
                        "CROSSBOT_CRED_OTTO_CLIENT_SECRET"],
        "credential_setup": "partner.otto.market 申请 Partner 账号 → "
                            "创建 API 客户端凭据",
        "growth_note": "德国品牌型渠道，2025/26 财年平台成交额约 75 亿欧元（+6%）",
        "import_template": {
            "buyer_id": "otto_kunde_01",
            "subject": "Lieferung / Wann wird geliefert?",
            "messages": ["Wann wird mein Paket geliefert?"],
        },
    },
    "kaufland": {
        "display": "Kaufland Global",
        "api_basis": "Kaufland Seller API (sellerapi.kaufland.com) + Token auth",
        "sync_mode": "manual",
        "credentials": ["CROSSBOT_CRED_KAUFLAND_CLIENT_KEY",
                        "CROSSBOT_CRED_KAUFLAND_SECRET_KEY"],
        "credential_setup": "Kaufland Seller Portal → Settings → API access → "
                            "生成 Client Key / Secret Key",
        "growth_note": "国际业务同比增长 124%（9 国站点），德/奥/捷/斯/波/法/意/西/荷",
        "import_template": {
            "buyer_id": "kaufland_kunde_01",
            "subject": "Frage zum Artikel",
            "messages": ["Hallo, ist der Artikel auch in Größe M verfügbar?"],
        },
    },
}


def list_connectors() -> List[Dict]:
    """连接器状态列表（用于前端展示与凭证就绪检测）。"""
    out = []
    for key, c in CONNECTORS.items():
        env_ready = all(os.environ.get(name) for name in c["credentials"])
        out.append({
            "platform": key,
            "display": c["display"],
            "api_basis": c["api_basis"],
            "sync_mode": c["sync_mode"] if not env_ready else "api_ready",
            "credentials_ready": env_ready,
            "required_env": c["credentials"],
            "credential_setup": c["credential_setup"],
            "growth_note": c["growth_note"],
            "import_template": c["import_template"],
            "default_language": platform_config(key)["language"],
            "countries": platform_config(key)["countries"],
        })
    return out


def parse_import(platform: str, items: List[dict]) -> List[dict]:
    """校验并规范化手动导入的数据（不落库；落库由路由完成）。

    每项：{buyer_id?, subject?, messages: [str, ...]}（messages 必填，1-50 条）。
    返回规范化后的列表；格式非法的条目抛 ValueError（由路由转 422）。
    """
    cfg = platform_config(platform)  # KeyError → 未知平台
    normalized = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"第 {i + 1} 条不是对象")
        messages = [str(m).strip() for m in (item.get("messages") or [])
                    if str(m).strip()]
        if not messages:
            raise ValueError(f"第 {i + 1} 条缺少 messages（买家消息，至少 1 条）")
        if len(messages) > 50:
            raise ValueError(f"第 {i + 1} 条消息数超过 50 条上限")
        normalized.append({
            "buyer_id": str(item.get("buyer_id") or
                            f"{platform}_buyer_{i + 1}"),
            "subject": (str(item.get("subject") or "").strip()
                        or messages[0][:60]),
            "messages": messages[:50],
            "language": str(item.get("language") or cfg["language"]),
        })
    if not normalized:
        raise ValueError("没有可导入的会话")
    if len(normalized) > 200:
        raise ValueError("单次最多导入 200 条会话")
    return normalized
