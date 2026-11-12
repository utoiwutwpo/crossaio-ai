"""2026 Agentic 商品 feed：把成稿转成买家高频问题 → 可直接喂给平台 AI 的 Q&A。

Amazon Rufus / iZi、eBay 语义搜索等会以买家自然语言问题检索 listing，
listing 里没有明确答案就会被跳过。本模块把成稿转成问题-答案对，供卖家
贴进 A+ / 属性 / FAQ 字段。
"""
import json
import re

from ..llm import LLMClient


def _points(rec):
    return [(b.get("heading") or "", b.get("content") or "")
            for b in (rec.bullet_points or []) if isinstance(b, dict)]


def build_qa(rec, platform="amazon", language="en", n=8):
    client = LLMClient()
    pts = _points(rec)
    prompt = """产品：%s
平台：%s
语言：%s
标题：%s
五点：%s
详情：%s

请只依据以上信息，生成 %d 组买家真实会问的问题与答案（JSON）：
{"qa":[{"question":"...","answer":"..."}],"coverage":{"price":"有/无","size":"有/无","material":"有/无","shipping":"有/无","warranty":"有/无"}}
要求：答案不得编造参数；信息不足时 answer 写 "listing 未提供，需补充"。
""" % (rec.product_name or "", platform, language, rec.title or "",
       " | ".join(h + " " + c for h, c in pts), (rec.description or "")[:1500], n)

    raw = ""
    try:
        raw = client.chat(prompt, system="你是跨境电商 listing 语义优化专家，只输出 JSON。",
                          temperature=0.3, max_tokens=1200, json_mode=True)
        raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
        m = re.search(r"\{.*\}", raw, flags=re.S)
        data = json.loads(m.group(0)) if m else {}
    except Exception:
        data = {}

    qa = []
    for key in ("qa", "QA", "问答", "问答对", "questions", "items", "pairs"):
        v = data.get(key)
        if isinstance(v, list) and v:
            qa = v
            break
    if not qa:
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                qa = v
                break

    norm = []
    for it in qa:
        if not isinstance(it, dict):
            continue
        q = it.get("question") or it.get("q") or it.get("问") or it.get("Q") or ""
        a = it.get("answer") or it.get("a") or it.get("答") or it.get("A") or ""
        if str(q).strip():
            norm.append({"question": str(q), "answer": str(a)})
    return {
        "platform": platform, "language": language,
        "engine": "mock" if getattr(client, "mock", False) else "llm",
        "qa": norm[:n],
        "coverage": data.get("coverage") or {},
        "note": "答案仅来自当前成稿；缺参数的项标为需补充，不做推测",
    }
