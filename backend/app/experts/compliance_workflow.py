"""
面向平台卖家的「GPSR + EU AI Act Art.50」原生内嵌合规工作流（组合层 / 真正护城河）

为什么需要这一层：
- gpsr.py / safety_gate.py 解决 GPSR（当地语言安全警示、合规块、事故上报）
- ai_act.py 解决 EU AI Act Art.50（每条 AI 回复必须告知买家"正在与 AI 对话"）
- 但两者原本是**孤岛**：客服只接了 Art.50，GPSR 只作用在 Listing 侧。

本模块把两层合二为一，且**以 platform 为统一入口（marketplace-native）**：
同一个平台，既知道「要求哪些语言的安全警示」，也知道「AI 回复该用什么语言披露」。
任意单点（GPSR 或 Art.50）都有人做，但「组合 + 13 平台统一 + 平台原生」全欧零竞品。

零 LLM 依赖（确定性规则）。
"""
from typing import Dict, List, Optional

from . import gpsr
from . import safety_gate
from . import platform_rules
from .ai_act import wrap_reply, identity_text, supported_languages as _ai_act_langs


# 买家消息触及产品安全时，附在该平台「要求语言」下的简短安全提示（marketplace-native）。
# key 覆盖 gpsr.LANG_HEADER 的全部语言；缺省回落 en。
_SAFETY_NOTICE: Dict[str, str] = {
    "en": ("For your safety: use this product only as described in the included "
           "instructions. Report any safety concern to us and your EU Responsible "
           "Person immediately."),
    "de": ("Sicherheitshinweis: Nutzen Sie dieses Produkt nur gemäß der beiliegenden "
           "Anleitung. Melden Sie Sicherheitsbedenken umgehend an uns und Ihre "
           "EU-verantwortliche Person."),
    "fr": ("Avis de sécurité : utilisez ce produit conformément à la notice fournie. "
           "Signalez tout problème de sécurité à nous et à votre Personne Responsable UE."),
    "es": ("Aviso de seguridad: utilice este producto según las instrucciones incluidas. "
           "Informe cualquier problema de seguridad a nosotros y a su Persona Responsable de la UE."),
    "it": ("Avviso di sicurezza: utilizzi questo prodotto secondo le istruzioni fornite. "
           "Segnali qualsiasi problema di sicurezza a noi e alla sua Persona Responsabile UE."),
    "pl": ("Uwaga bezpieczeństwa: używaj tego produktu zgodnie z dołączoną instrukcją. "
           "Zgłoś wszelkie problemy bezpieczeństwa nam oraz swojej Osobie Odpowiedzialnej UE."),
    "ro": ("Avertisment de siguranță: utilizați acest produs conform instrucțiunilor incluse. "
           "Raportați orice problemă de siguranță nouă și Persoanei Responsabile UE."),
    "nl": ("Veiligheidsmelding: gebruik dit product volgens de bijgevoegde instructies. "
           "Meld veiligheidsproblemen direct aan ons en uw EU-verantwoordelijke persoon."),
    "sv": ("Säkerhetsmeddelande: använd endast denna produkt enligt medföljande instruktioner. "
           "Rapportera säkerhetsproblem till oss och din EU-ansvariga person omedelbart."),
    "cs": ("Bezpečnostní upozornění: tento výrobek používejte pouze dle přiložených pokynů. "
           "Bezpečnostní problémy nahlaste nám i své osobě odpovědné za EU."),
    "hu": ("Biztonsági figyelmeztetés: ezt a terméket csak a mellékelt útmutató szerint "
           "használja. A biztonsági problémákat azonnal jelezze nekünk és az Ön EU-s "
           "felelős személyének."),
    "bg": ("Предупреждение за безопасност: използвайте този продукт само според "
           "приложените инструкции. Съобщете за всякакви проблеми с безопасността "
           "на нас и на вашия отговорен представител в ЕС незабавно."),
}


# 人身伤害/就医类表述（原红线的 harm_claim 范畴，现升级为「合规优先回复」触发源）
_HARM_CLAIM_WORDS = [
    "injur", "hurt", "hospital", "wound", "bleed",
    "受伤", "烫伤", "割伤", "进了医院", "住院", "流血",
    "verletzt", "verletzt worden",            # 德（受伤）
    "blessé", "bléssé",                       # 法/西
    "ferito",                                 # 意
    "ranny", "poszkodowany",                  # 波
    "rănit",                                  # 罗
]


def _buyer_touches_safety(message: str) -> bool:
    """买家消息是否触及产品安全（命中安全词库或人身伤害词 → 视为触及）。"""
    low = (message or "").lower()
    if any(w in low for words in safety_gate.SAFETY_LEXICON.values() for w in words):
        return True
    return any(w in low for w in _HARM_CLAIM_WORDS)


# 安全事件回复引导语（中英双语，提示立即停用 + 欧代 + 15 天 Safety Gate）
_SAFETY_INCIDENT_LEAD = (
    "We take this safety concern very seriously. Please stop using the product "
    "immediately and keep it in a safe place. Contact our EU Responsible Person "
    "without delay, and if anyone was injured, report to your local market "
    "surveillance authority. Under GPSR (EU 2023/988 Art.35) we are assessing "
    "whether a Safety Gate notification is required within 15 days. / "
    "我们高度重视这一安全反馈。请立即停止使用该产品并妥善保管，尽快联系我们的"
    "欧盟授权代表（欧代）；如有人员受伤，请向当地市场监管机构报告。依据 GPSR "
    "(EU 2023/988) 第 35 条，我们正评估是否须在 15 天内经 EU Safety Gate 上报。"
)


def _gpsr_safety_lines(platform: str) -> List[str]:
    """返回该平台「要求语言」下的 GPSR 安全提示行（marketplace-native）。"""
    langs = gpsr.required_languages(platform) or ["en"]
    lines = []
    for lang in langs:
        notice = _SAFETY_NOTICE.get(lang) or _SAFETY_NOTICE["en"]
        header = gpsr.LANG_HEADER.get(lang, gpsr.LANG_HEADER["en"])
        lines.append(f"[{lang.upper()}] {header}: {notice}")
    return lines


class MarketplaceComplianceWorkflow:
    """GPSR + AI Act Art.50 的组合工作流，以 platform 为统一入口。"""

    # ---------- Listing 侧（GPSR 合规块） ----------
    def listing_compliance_block(self, platform: str, product_name: str,
                                 keywords: List[str],
                                 eu_rep_line: str = "") -> Dict:
        """生成可粘贴进 listing 的 GPSR 合规块。

        「平台原生」优先：allegro/emag/cdiscount/otto/kaufland/bol/miravia
        有平台原生规则（当地语言政策名+监管机构+平台特有规则）时，
        用 platform_rules.native_compliance_block 生成平台原生措辞的块；
        其余平台回落通用 gpsr.gpsr_block_text。
        """
        check = gpsr.check(product_name, keywords, platform, eu_rep_line=eu_rep_line)
        categories = gpsr.detect_categories(product_name, keywords)
        languages = check.get("required_languages") or gpsr.required_languages(platform)

        native_used = False
        if platform_rules.has_native_rules(platform):
            # 解析 eu_rep_line 回传的欧代信息（"Name, Address, Email" 形式）
            rep = None
            if eu_rep_line and "、" not in eu_rep_line and "," in eu_rep_line:
                parts = [p.strip() for p in eu_rep_line.split(",", 2)]
                if len(parts) == 3:
                    rep = {"company_name": parts[0], "address": parts[1],
                           "email": parts[2]}
            nb = platform_rules.native_compliance_block(
                platform, product_name, keywords, eu_rep=rep)
            block, native_used, native_meta = nb["block"], True, {
                "policy_name": nb.get("policy_name"),
            }
        else:
            block = gpsr.gpsr_block_text(
                platform, categories, languages, product_name, eu_rep_line=eu_rep_line)
            native_meta = None

        return {
            "platform": platform,
            "risk_level": check["risk_level"],
            "ce_required": check["ce_required"],
            "required_languages": languages,
            "block": block,
            "native_rules": native_used,
            "native_meta": native_meta,
        }

    # ---------- 客服侧（组合层核心） ----------
    def augment_customer_reply(self, reply: str, platform: str, lang: str,
                               buyer_message: str, enabled: bool = True) -> str:
        """把 GPSR（条件触发）+ Art.50（默认）合并注入一条 AI 客服回复。

        - 买家消息触及安全 → 附该平台要求语言的 GPSR 安全提示
        - 始终（enabled）→ 末尾追加 Art.50 AI 身份告知
        返回最终可发送文本。
        """
        out = reply
        if _buyer_touches_safety(buyer_message):
            extra = "\n\n".join(_gpsr_safety_lines(platform))
            out = f"{reply}\n\n{extra}"
        return wrap_reply(out, lang, enabled)

    # ---------- 统一组合视图（给前端的单入口） ----------
    def compliance_summary(self, platform: str, product_name: str, keywords: List[str],
                           lang: str, buyer_message: str,
                           enabled: bool = True) -> Dict:
        """一次调用返回 GPSR + Art.50 两层状态，供工作台单卡片展示。"""
        g = self.listing_compliance_block(platform, product_name, keywords)
        touch = _buyer_touches_safety(buyer_message)
        return {
            "platform": platform,
            "gpsr": {
                "risk_level": g["risk_level"],
                "ce_required": g["ce_required"],
                "required_languages": g["required_languages"],
                "buyer_message_touches_safety": touch,
            },
            "ai_act": {
                "enabled": enabled,
                "identity_text": identity_text(lang) if enabled else None,
                "supported_languages_count": len(_ai_act_langs()),
            },
        }

    # ---------- 发送前 GPSR 扫描 ----------
    def is_safety_incident(self, message: str) -> bool:
        """买家消息是否构成 GPSR 产品安全事件（命中安全词库 → 合规优先回复）。"""
        return _buyer_touches_safety(message)

    # ---------- 合规优先回复（安全事件专用） ----------
    def compliance_priority_reply(self, platform: str, lang: str,
                                  buyer_message: str, enabled: bool = True) -> str:
        """GPSR 安全事件回复：安全指引 + 平台要求语言警示 + 15 天上报提示 + Art.50。

        区别于普通红线（只安抚不承诺）：本回复在「不承认责任、强制转人工」基础上，
        额外给出平台要求语言的 GPSR 安全指引与 Safety Gate 上报提示——竞品零做。
        """
        lines = _gpsr_safety_lines(platform)
        body = _SAFETY_INCIDENT_LEAD + "\n\n" + "\n\n".join(lines)
        return wrap_reply(body, lang, enabled)


# 模块级便捷函数（供 customer_service 等直接调用，无需实例化）
_default_workflow = MarketplaceComplianceWorkflow()


def augment_customer_reply(reply: str, platform: str, lang: str,
                           buyer_message: str, enabled: bool = True) -> str:
    return _default_workflow.augment_customer_reply(reply, platform, lang, buyer_message, enabled)


def listing_compliance_block(platform: str, product_name: str, keywords: List[str],
                             eu_rep_line: str = "") -> Dict:
    return _default_workflow.listing_compliance_block(
        platform, product_name, keywords, eu_rep_line=eu_rep_line)


def is_safety_incident(message: str) -> bool:
    return _default_workflow.is_safety_incident(message)


def compliance_priority_reply(platform: str, lang: str, buyer_message: str,
                              enabled: bool = True) -> str:
    return _default_workflow.compliance_priority_reply(platform, lang, buyer_message, enabled)


def compliance_summary(platform: str, product_name: str, keywords: List[str],
                        lang: str, buyer_message: str, enabled: bool = True) -> Dict:
    return _default_workflow.compliance_summary(platform, product_name, keywords, lang, buyer_message, enabled)
