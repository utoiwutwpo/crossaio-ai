# -*- coding: utf-8 -*-
import os, re, sys, io

os.chdir(r"D:\Claude\crossbot-ai\backend")
sys.path.insert(0, r"D:\Claude\crossbot-ai\backend")

from app.routers import rule_pages as rp
from app.experts import platform_rules

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_out")
os.makedirs(out_dir, exist_ok=True)

cases = [("en", "allegro"), ("fr", "otto"), ("de", "bol")]
cjk = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

for lang, plat in cases:
    html = rp._page_i18n(plat, lang)
    fp = os.path.join(out_dir, f"{lang}_{plat}.html")
    with io.open(fp, "w", encoding="utf-8") as f:
        f.write(html)

    # 1. no CJK residual
    bad = cjk.findall(html)
    # 2. switcher inside <nav>
    nav_open = html.find("<nav")
    nav_close = html.find("</nav>")
    sw = html.find('class="lang-switch"')
    sw_in_nav = (nav_open != -1 and sw != -1 and nav_open < sw < nav_close)
    # 3. gap:3px present in switcher inline style
    gap3 = 'gap:3px' in html
    # 4. platform data unchanged (raw card; & may be HTML-escaped)
    import html as _html
    card = platform_rules.platform_rules_card(plat)
    data_ok = (
        str(card["rule_count"]) in html
        and str(card["warning_language_count"]) in html
        and (_html.escape(card["policy_name"]) in html or card["policy_name"] in html)
    )
    # 5. new shell markers present
    markers = all(m in html for m in ('class="page-head"', 'class="ph-glow"', 'class="gh-code"', 'class="cta-band"', 'compliance-check'))

    print(f"[{lang}/{plat}] bytes={len(html)} cjk={len(bad)} switcher_in_nav={sw_in_nav} gap3={gap3} data_ok={data_ok} shell={markers}")
    if bad:
        # show context of first few CJK hits
        for m in list(cjk.finditer(html))[:5]:
            s = max(0, m.start()-30)
            print("   CJK CTX:", repr(html[s:m.start()+10]))
    print("   ->", fp)

print("DONE")
