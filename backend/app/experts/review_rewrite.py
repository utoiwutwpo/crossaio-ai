"""
P0-4 跨平台差评回复改写专家（独有卖点首版）

流程：平台规则模板 → LLM 生成（公开回复 / 私信安抚）→ 规则自查 →
返回双输出 + rule_check + status（无任何自动发送动作，由卖家人工确认后复制/导出）。

规则模板存 system_settings["review_rules"]（JSON，AES-256 加密存储，可迭代）；
未配置时使用本模块内置默认规则。自查引擎为纯确定性逻辑（不依赖 LLM），
测试可在无 LLM Key 环境下稳定验证违禁词拦截与两平台模板选择。
"""
import json
import re

from ..llm import LLMClient

# ---------- 平台规则模板（内置默认；system_settings 可覆盖） ----------
DEFAULT_REVIEW_RULES = {
    "amazon": {
        "title": "Amazon 评价回复政策",
        "forbidden": [   # 违禁：以补偿/返现/折扣换取好评（Amazon 明确禁止）
            "返现", "现金返还", "补偿", "退款换好评", "折扣换好评", "好评返现",
            "cash back", "compensation", "refund.*in exchange",
            "discount.*(for|in exchange).*review", "in exchange for a review",
        ],
        "banned_patterns": [  # 违禁：站外联系方式 / 引流（评价回复禁止引导站外沟通）
            {"label": "站外联系方式引流",
             "pattern": r"(wechat|whatsapp|telegram|vk\.com|facebook\.com|instagram\.com|"
                        r"邮箱|e-?mail|@[a-z0-9.-]+\.[a-z]{2,}|点击.{0,6}(链接|link))"},
        ],
        "tone": (
            "公开回复：以官方卖家身份，冷静澄清事实、表达歉意与改进意愿，"
            "不争辩、不承诺赔偿；私信安抚：表达理解、引导通过平台官方渠道解决。"
        ),
        "note": "Amazon 评价政策：不得以补偿/返现/折扣换取评价，不得在评价回复中索取"
                "联系方式或引导站外沟通。",
    },
    "ebay": {
        "title": "eBay 消息与评价政策",
        "forbidden": [
            "返现", "现金返还", "补偿", "退款换好评", "折扣换好评", "好评返现",
            "cash back", "compensation", "refund.*in exchange",
            "discount.*(for|in exchange).*review", "in exchange for a review",
        ],
        "banned_patterns": [
            {"label": "站外交易/引流",
             "pattern": r"(wechat|whatsapp|telegram|vk\.com|facebook\.com|instagram\.com|"
                        r"邮箱|e-?mail|@[a-z0-9.-]+\.[a-z]{2,}|off[- ]site|站外)"},
        ],
        "tone": (
            "公开回复：中立客观，给出解决步骤，不指责买家；私信安抚：表达重视，"
            "引导通过 eBay 站内消息联系卖家完成售后。"
        ),
        "note": "eBay 政策：不得引导站外交易/站外联系，评价回复须中性、避免争议性表述。",
    },
}

# 输入差评的风险信号（勒索型差评：暗示给补偿/返现才改评价 → 标红并提示走官方流程）
EXTORTION_SIGNALS = [
    # 中文：给钱/补偿 → 才/否则 改删换
    r"(给|退|返|给点|提供).{0,10}(钱|款|现金|补偿|优惠|折扣).{0,12}(就|才|否则|不然|改|删|换)",
    # 中英：改/删评价 → 就/才/否则/unless/or/otherwise
    r"(改|删|remove|delete|change|update).{0,20}(评价|差评|review|feedback).{0,15}(就|才|如果|unless|or|otherwise)",
    r"unless you (refund|give|pay)",
    # 英：refund/pay me ... and ... change review
    r"(refund|pay|give).{0,20}(me|us|back).{0,15}(and|then).{0,15}(change|delete|remove|update|leave).{0,15}(review|feedback)",
    # 英：or I will leave/post/write bad review
    r"(or|otherwise).{0,15}(i|we).{0,10}(will|'ll|am going|are going).{0,15}(leave|post|write|report|spread).{0,15}(review|feedback|bad)",
]

# ---------- 确定性兜底模板（LLM 未配置/输出不可用时） ----------
FALLBACK_REPLIES = {
    "amazon": {
        "public": (
            "Thank you for your feedback. We're sorry to hear about this experience — "
            "we take it seriously and will review it with our team to keep improving. "
            "If you need assistance, please reach us through Amazon's official "
            "messaging and we'll be happy to help. / 感谢您的反馈。很抱歉给您带来"
            "不好的体验，我们会认真对待并持续改进。如需帮助，请通过亚马逊官方"
            "站内信联系我们。"
        ),
        "private": (
            "We're truly sorry this experience didn't meet your expectations. "
            "Your feedback has been escalated to our support team, and we'd like to "
            "help make things right through Amazon's official channel. "
            "Please send us a message from your order page so we can assist you directly. "
            "/ 非常抱歉这次体验未达您的预期。我们已将您的反馈转交支持团队，"
            "希望通过亚马逊官方渠道为您解决问题，请从订单页面给我们留言。"
        ),
    },
    "ebay": {
        "public": (
            "We're sorry for the inconvenience. We take your feedback seriously and "
            "will look into it. For direct assistance, please use eBay's messaging "
            "system so we can resolve the issue for you. / 给您带来不便我们深表歉意。"
            "我们重视您的反馈并将核实处理。如需帮助，请通过 eBay 站内消息联系我们。"
        ),
        "private": (
            "Thank you for letting us know — we understand your frustration and want "
            "to help. Please reach out through eBay's messaging system so we can sort "
            "this out for you quickly. / 感谢您的反馈，我们理解您的心情，并希望能"
            "尽快为您解决。请通过 eBay 站内消息与我们联系。"
        ),
    },
}


class ReviewRewriteExpert:
    name = "review_rewrite"
    description = "跨平台差评回复改写（规则自查 + 双输出）"

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    # ---------- 规则读取 ----------
    def rules_for(self, db, platform: str) -> dict:
        """从 system_settings 读平台规则（解密）；未配置则用内置默认。"""
        from ..database import SystemSetting
        from ..ebay_service import decrypt_secret
        try:
            row = db.query(SystemSetting).filter_by(key="review_rules").first()
            if row:
                raw = decrypt_secret(row.value)
                all_rules = json.loads(raw)
                if isinstance(all_rules, dict) and platform in all_rules:
                    return all_rules[platform]
        except Exception:
            pass
        return DEFAULT_REVIEW_RULES.get(platform, {})

    # ---------- 确定性自查引擎 ----------
    def scan(self, text: str, rules: dict) -> list:
        """返回命中的风险项 [{"rule": ..., "snippet": ...}]（空 = 通过）。"""
        low = (text or "").lower()
        hits = []
        for kw in rules.get("forbidden", []):
            if re.search(kw, low):
                hits.append({"rule": f"违禁表述：{kw}", "snippet": kw})
        for bp in rules.get("banned_patterns", []):
            m = re.search(bp["pattern"], low)
            if m:
                hits.append({"rule": bp["label"], "snippet": m.group(0)[:40]})
        return hits

    def scan_extortion(self, text: str) -> list:
        """输入差评的风险信号（勒索型差评暗示 → 标红）。"""
        low = (text or "").lower()
        return [{"rule": "差评原文含疑似『补偿换好评』信号",
                 "snippet": re.search(p, low).group(0)[:40]}
                for p in EXTORTION_SIGNALS if re.search(p, low)]

    # ---------- 生成 ----------
    def rewrite(self, db, platform: str, review_snippet: str,
                listing_ref: str = "", mode: str = "both") -> dict:
        rules = self.rules_for(db, platform)
        need_private = mode in ("private", "both")
        need_public = mode in ("public", "both")

        public_reply, private_message = self._generate(
            platform, rules, review_snippet, listing_ref, need_public, need_private)

        # 规则自查：输入风险（勒索信号）+ 输出风险（违禁/引流）
        input_risks = self.scan_extortion(review_snippet)
        output_risks = self.scan(public_reply + " " + private_message, rules)

        risk_hits = input_risks + output_risks
        status = "pending" if risk_hits else "approved"
        rule_check = {
            "platform": platform,
            "status": status,
            "passed": [
                "未命中违禁补偿/返现换好评表述",
                "未包含站外联系方式或引流",
            ] if not output_risks else [],
            "attention": [
                "差评原文含疑似『补偿/返现换好评』信号，回复已按平台规则不承诺任何补偿；"
                "建议通过平台官方流程处理" if input_risks else None,
            ],
            "risk": output_risks,
            "note": rules.get("note", ""),
        }
        rule_check["attention"] = [a for a in rule_check["attention"] if a]

        return {
            "platform": platform,
            "listing_ref": listing_ref,
            "review_snippet": review_snippet,
            "public_reply": public_reply,
            "private_message": private_message,
            "rule_check": rule_check,
            "status": status,
        }

    def _generate(self, platform, rules, review_snippet, listing_ref,
                  need_public: bool, need_private: bool) -> tuple:
        """LLM 生成；Mock/失败/输出不可用 → 确定性兜底模板。"""
        fb = FALLBACK_REPLIES.get(platform, FALLBACK_REPLIES["amazon"])
        public = fb["public"] if need_public else ""
        private = fb["private"] if need_private else ""

        prompt = self._build_prompt(platform, rules, review_snippet,
                                    listing_ref, need_public, need_private)
        try:
            out = self.llm.chat(prompt, temperature=0.3, max_tokens=900,
                                json_mode=True).strip()
            data = LLMClient.extract_json(out)
            if isinstance(data, dict):
                if need_public and isinstance(data.get("public_reply"), str) \
                        and data["public_reply"].strip():
                    public = data["public_reply"].strip()
                if need_private and isinstance(data.get("private_message"), str) \
                        and data["private_message"].strip():
                    private = data["private_message"].strip()
        except Exception:
            pass
        return public, private

    @staticmethod
    def _build_prompt(platform, rules, review_snippet, listing_ref,
                      need_public: bool, need_private: bool) -> str:
        tone = rules.get("tone", "")
        note = rules.get("note", "")
        mode_desc = []
        if need_public:
            mode_desc.append("public_reply：卖家身份公开回复该评价")
        if need_private:
            mode_desc.append("private_message：若该买家可私信联系，发出的安抚私信")
        return (
            "你是跨境平台差评回复改写专家。根据平台规则与差评原文，改写两段文案。\n"
            f"平台：{platform}（{rules.get('title','')}）\n"
            f"规则红线：{note}\n"
            f"风格要求：{tone}\n"
            f"差评原文：{review_snippet}\n"
            f"Listing 标识：{listing_ref or '（未提供）'}\n"
            f"输出要求：{ '；'.join(mode_desc) }\n"
            "硬性约束：绝对不得包含任何返现/补偿/折扣换好评表述，"
            "不得出现站外联系方式（微信/WhatsApp/邮箱/外链等）。\n"
            '只输出 JSON：{"public_reply": "...", "private_message": "..."}'
        )
