"""P0-2 合规×运营一体化：合规体检结论 → AI 生成强制上下文（内部服务层）。

输入：user_id +（可选）platform / product_name；
输出：结构化合规提示块，供描述生成 / 客服话术 / 差评改写共用。

判定规则（诚实边界）：
- 无审计记录 → found=False，调用方降级为普通模式（不报错、不注入）。
- 最近一次审计 risk_level ∈ {medium, high} → 视为"有未通过项"，注入待补缺口清单。
- 最近一次审计 risk_level == low → 视为"已通过"，不注入。
- 注入口径禁止 AI 虚构合规状态（未核实不得写"已认证/已合规"）。
"""
from typing import Dict, Optional

from sqlalchemy.orm import Session

from ..database import ComplianceAudit

MAX_GAPS = 6


def latest_unpassed_audit(db: Session, user_id: str, *,
                          platform: Optional[str] = None,
                          product_name: Optional[str] = None) -> Optional[ComplianceAudit]:
    """取该用户最近一次"未通过"审计；支持按平台/产品名收窄匹配。

    - 传 platform：仅在同平台审计内找（优先）。
    - 传 product_name：先精确匹配，再模糊包含匹配。
    - 无匹配 → None。
    """
    q = (db.query(ComplianceAudit)
         .filter(ComplianceAudit.user_id == user_id,
                 ComplianceAudit.risk_level.in_(["medium", "high"]))
         .order_by(ComplianceAudit.created_at.desc()))

    rows = q.filter(ComplianceAudit.platform == platform).all() if platform else q.all()
    if not rows:
        return None

    pn = (product_name or "").strip()
    if pn:
        for r in rows:
            if (r.product_name or "").strip() == pn:
                return r
        for r in rows:
            if pn.lower() in (r.product_name or "").lower():
                return r
    return rows[0]


def _gaps_from_audit(audit: ComplianceAudit) -> list:
    """从体检报告 checklist 提取 required=True 的待补项名称（最多 MAX_GAPS 项）。"""
    report = audit.report or {}
    gaps: list = []
    for item in report.get("checklist") or []:
        if item.get("required") and item.get("name"):
            gaps.append(item["name"])
        if len(gaps) >= MAX_GAPS:
            break
    return gaps


def build_compliance_context(db: Session, user_id: str, *,
                             platform: Optional[str] = None,
                             product_name: Optional[str] = None) -> Dict:
    """组装合规提示块。返回：
    {
      found: bool,
      audit_id: str | None,
      risk_level: str | None,
      gaps: list[str],
      prompt_block: str,     # 注入 LLM 的文本块（未命中时为 ""）
      display_block: dict|None,  # 前端展示块（未命中时为 None）
    }
    """
    audit = latest_unpassed_audit(db, user_id,
                                  platform=platform, product_name=product_name)
    if audit is None:
        return {"found": False, "audit_id": None, "risk_level": None,
                "gaps": [], "prompt_block": "", "display_block": None}

    gaps = _gaps_from_audit(audit)
    gaps_text = "、".join(gaps) if gaps else "详见体检报告"
    prompt_block = (
        "【合规上下文】该产品最近一次合规体检未通过（风险等级: {risk}）。"
        "生成内容必须对照以下待补合规项：{gaps}。"
        "严禁虚构合规状态：未核实前不得写\"已获 CE / 已认证 / 欧盟授权代表已就绪\""
        "等表述；如产品确需这些合规文件，请在文案中引导补齐，不得宣称已满足。"
    ).format(risk=audit.risk_level, gaps=gaps_text)
    display_block = {
        "audit_id": audit.id,
        "risk_level": audit.risk_level,
        "gaps": gaps,
        "text": (f"⚠️ 最近一次合规体检未通过（{audit.risk_level}），"
                 f"待补项：{gaps_text}。AI 输出已按未通过口径生成，不虚构合规状态。"),
    }
    return {"found": True, "audit_id": audit.id, "risk_level": audit.risk_level,
            "gaps": gaps, "prompt_block": prompt_block,
            "display_block": display_block}
