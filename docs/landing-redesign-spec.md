# CrossAIO 落地页重设计规范（en/de/fr × 32 页 = 96 页）

> 本文档是所有改造子任务的**唯一共享规范**。设计语言、代码块、页面骨架、转化规则、硬约束、验证清单都以此为准。
> **种子范本**：`backend/app/static/en/home.html`（已重设计完毕，本地 http://127.0.0.1:9000/en/ 渲染验证通过）。
> **只做本地文件修改，严禁 git push / 部署 Render / 修改远端。** 服务为本地 uvicorn（127.0.0.1:9000），静态 HTML 改完即时生效；改 `.py` 模板后需重启服务（由总控负责，子任务无需重启）。

---

## 0. 任务所有权（文件互斥，勿越界）

| 子任务 | 文件范围 | 影响的页面 |
|---|---|---|
| A 功能模板 | `backend/app/routers/feature_pages.py`（含 `_CSS`、`_page/_page_i18n`、`_index_lang`、`_switcher_feature`、mockup 相关） | /{lang}/features 总览 + 9 详情 × en/de/fr = 30 页 |
| B GPSR 模板 | `backend/app/routers/gpsr_pages.py`（`_shell`、`_home/_features/_platforms/_compare/_pricing/_faq`、`_GPSR_CSS`、`_gnav`、`_switcher`） | /{lang}/gpsr-check + 5 子页 × 3 = 18 页 |
| C 规则模板 | `backend/app/routers/rule_pages.py`（`_page/_page_i18n`、`_CSS`、`_switcher_rules`） | /{lang}/rules/{allegro,emag,cdiscount,otto,kaufland,bol} × 3 = 18 页 |
| D en 静态 | `backend/app/static/en/` 下除 home.html 外的 10 个文件：pricing, privacy, terms, skills, rules, signin, signup, compliance-check, gpsr-check, index.html | en 10 页 |
| E de 静态 | `backend/app/static/de/` 全部 11 个文件（含 home.html——需按 en 范本模式重做德文版） | de 11 页 |
| F fr 静态 | `backend/app/static/fr/` 全部 11 个文件（含 home.html——需按 en 范本模式重做法文版） | fr 11 页 |

- **index.html（工作台 app）**：功能性应用外壳（76KB JS 逻辑）。只允许做「页头视觉一致性」的轻微修饰（如品牌区/顶栏配色对齐），**严禁改动任何应用逻辑、表单、JS 函数、ID、action**；拿不准就完全不动。路由必须仍返回 200。
- **site_nav.py / effects.css / effects.js**：已经由总控处理好（导航注入切换器、gap:3px），**不要修改**。
- zh 静态页与 zh 动态页**不在本次重设计范围**，不得修改。

---

## 1. 设计语言（必须遵守的设计令牌）

### 1.1 色彩
```
--navy:#0b1030; --ink:#0f172a; --muted:#64748b; --border:#e2e8f0; --bg:#ffffff; --soft:#f8fafc;
--blue:#2563eb; --blue-light:#3b82f6; --blue-dark:#1d4ed8; --purple:#8b5cf6; --violet:#7c3aed;
--ok:#059669; --err:#dc2626
```
- 深色区块（hero/CTA/合规带/页头）统一用 `linear-gradient(115deg,#0a0f2e 0%,#141040 48%,#3b1a86 100%)`（可加径向紫蓝辉光 `radial-gradient(...rgba(124,58,237,.4~.5)...)`）。
- 渐变按钮：`linear-gradient(90deg,var(--blue-light),var(--violet))`。
- 渐变数字/标题强调：`linear-gradient(90deg,#93c5fd,#c4b5fd)`（深底）或 `linear-gradient(90deg,var(--blue),var(--purple),var(--blue))`（浅底 shimmer）。

### 1.2 玻璃态 / 卡片
```
玻璃卡片: background:rgba(255,255,255,.82); backdrop-filter:blur(10px); border:1px solid var(--border); border-radius:18px;
深底玻璃: background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.14); backdrop-filter:blur(8px);
hover 提升: transform:translateY(-4~5px); box-shadow:0 16~20px 40~46px rgba(15,23,42,.12); border-color:#bfdbfe;
```

### 1.3 科技背景层（hero / 深色带内）
按 en 范本复制以下三层（全部 `position:absolute; inset:0; pointer-events:none`，z 序在内容之下）：
1. **网格层 `.hero-grid`**：`background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px), linear-gradient(90deg,...)`，`background-size:44px 44px`，径向 mask 淡出。
2. **辉光层 `.hero-glow`**：2 个 blur(70px) 的紫/蓝 radial blob，`glowpulse` 呼吸动画（9s）。
3. **粒子层 `.particles`**：12~14 个 3~6px 圆点（#93c5fd/#c4b5fd/#a5b4fc），`ptw` 上升动画（7~11s，错开 delay）。位置用 inline style `left/top` 百分比散布。
4. **轨道环 `.orbits`**（hero 右侧）：3 个同心圆环 + 自转光点（rot 动画，30s/20s 反向/14s，绿/蓝/紫光点）。窄屏隐藏。

### 1.4 动效清单（克制，不喧宾夺主）
- 滚动入场：给 section/卡片容器加 `class="reveal"`（effects.js 已支持，加载时渐入）；批次卡片可加 `reveal-delay`/`reveal-delay2`。
- 数字统计：`.count-up`（effects.js 支持，从 0 计数）。
- 按钮：主 CTA 加光扫 `::after + shine` 动画；hover 上浮 2px + 光晕加深。
- SVG 配图：`mk-float`（上下漂浮 6s）、`mk-scan`（扫描线 4.5s）、`mk-dot`（脉冲）、`mk-chip`（呼吸）——keyframes 按 en 范本定义。
- 平台横幅：`.pm-track` marquee 32s 无限滚动，hover 暂停，左右 mask 淡出。
- `@media (prefers-reduced-motion: reduce)` 关闭所有装饰动画。

### 1.5 导航与语言切换器（硬性代码块，逐字使用）
- **导航**：结构、层级、链接与各语言首页完全一致（各语言首页已有完整下拉：Product/Capabilities 10 条 + Platforms 7 条 + Free tools 4 条 + Pricing solo + 右侧 切换器/登录/注册）。静态页改造时**直接复制本语言 home.html 里的 `<nav>...</nav>` 整块**（含 active 高亮按需微调，无则不加）。
- **切换器**（🌐 与语言名**恰好一个空格**，不能太远）：
```html
<div class="lang-switch" role="navigation" aria-label="Language" style="display:inline-flex;gap:3px;align-items:center;padding:5px 12px;border:1px solid #cbd5e1;border-radius:999px;background:#fff;color:#0f172a;font-size:13px">
  🌐<select onchange="location.href=this.value" style="border:none;background:transparent;font-size:13px;color:#0f172a;outline:none;cursor:pointer;font-weight:700">
    <option value="/en/..." data-lang="en" selected>English</option>
    <option value="/de/..." data-lang="de">Deutsch</option>
    <option value="/fr/..." data-lang="fr">Français</option>
    <option value="/..." data-lang="zh">中文</option>
  </select>
</div>
```
（英文第一、中文最后、selected=当前语言、保持当前页面路径不丢；gap:3px 已由总控统一，**保持 3px 不得再改**。）
- 动态模板（A/B/C）的切换器已由总控移入 `nav .right` 内部——**保持原位，不要再放到 `</nav>` 之后**。
- 桌面/移动端形态一致；`.menu` 在 ≤980px 隐藏（保持）。

---

## 2. 页面骨架规范（按页型）

所有页面统一尾部结构：`<footer>`（各语言现有页脚链接/版权行保留原文）→ `<script src="/effects.js">`（静态页）→ lang 偏好脚本（动态页已有 `{_LANG_SCRIPT}`）。

### 2.1 首页（en 已成品；de/fr 照做）
直接以 `backend/app/static/en/home.html` 为蓝本做逐段翻译替换（文案取本语言现有 home 的原文），保留：topbar（GPSR 强制横幅）、完整导航、深色 hero（网格+辉光+粒子+轨道+SVG 工作台配图）、trust 行、4 统计条（count-up）、6 功能卡（可链接到对应功能页）、合规双栏 spotlight（GPSR + EU AI Act Art.50）、13 平台 marquee、4 步流程、定价预览、FAQ、CTA 带、页脚。
- **价格事实按本语言**：en=Free €0 / Starter €29（50/day·1000/month，年付 €23/mo）/ Pro €49（200/day·3 平台矩阵）/ Business €149（1000/day）；de=Free €0 / Starter €29 / Growth €99；fr=Gratuit €0 / Grow €29 / Scale €99。**只准出现本语言定价页已有的数字。**
- 合规 spotlight 事实（各语言自己的原文表述，逐字保留）：
  - GPSR：EU 2023/988 已强制执行；缺 EU Rep / 警示语 = 下架 + Safety Gate 上报；EU Rep 登记、当地语言警示语、EC 符合性声明模板、15 天事故上报提醒。
  - AI Act：Art.50 自 **2026-08-02** 生效；每条 AI 客服回复必须告知「you are chatting with an AI / Sie chatten mit einer KI / vous discutez avec une IA」（16 语言）；罚款最高 **€15M 或全球营收 3%**（de/fr 页已有此表述才用）。
  - **不得把其他语言的表述/数字搬进本语言页面**。

### 2.2 定价页
保留：现有套餐卡片全部数据（名称/价格/次数/年付省额/权益清单）、月/年切换器、对比表、FAQ、CTA。升级：
- 深色 `page-head`（科技层+发光 H1）+ 套餐卡玻璃态/hover 提升/热销徽章发光。
- 对比表关键行高亮（合规引擎、Art.50、矩阵）。
- 页尾 CTA 带（免费开始 + 免费体检双按钮）。
- **不改任何价格与权益文字。**

### 2.3 隐私/条款
法律文本**逐字保留**，只做版式：深色页头 + 白色文档容器（max-width ~860px，标题层级清晰）+ 页内锚点目录（可选）+ 标准页脚。不做转化 CTA 堆砌（信任优先）。

### 2.4 Skills 页
保留技能数据（GPSR 检查器 + 欧洲平台规则库，MIT 等事实）。升级：深色 hero + 2 张玻璃功能卡（含 `gh-code` 代码窗口展示）+ 特性清单 + CTA（到 /signup 或 /skills 现有外链，**保持现有链接目标**）。

### 2.5 规则速查页（静态 rules.html）
保留全部平台数据行（字符限制/语言/GPSR 要点）。升级：深色页头 + 13 平台卡/表（悬停高亮）+ 顶部 3 条关键提示（字数/语言/GPSR）+ CTA 到 `/{lang}/gpsr-check`。**数据来源平台注册表，勿改数字。**

### 2.6 登录/注册页
保留表单全部字段、action、JS、OAuth 按钮（**一处都不能动**）。升级为左右分栏：左=品牌价值区（深色科技层 + 要点 + trust 徽章），右=玻璃表单卡；输入框聚焦发光、按钮渐变；页面整体统一视觉。

### 2.7 合规体检页（静态 compliance-check.html）
保留表单/体检逻辑（**JS、ID、action 不动**）。升级：深色 hero（价值主张前置）+ 表单玻璃卡 + 步骤条（体检→欧代→技术文件→回填）+ 对比表/信任区 + CTA。

### 2.8 GPSR 体检页（静态 gpsr-check.html 与动态 /{lang}/gpsr-check/*）
静态 gpsr-check.html：同上，保留表单逻辑。动态（B 子任务）：`_shell` 已含 topbar/导航/切换器/`_gnav` 分页胶囊条/`_aiact_banner`。升级 `_GPSR_CSS` 与各页 body：深色 hero（轨道+粒子，保留 30 秒免费体检表单）、`danger-band` 保留、统计条、对比表、定价卡、FAQ、CTA 带。**`_gnav` 结构保留。**

### 2.9 功能页（A 子任务）
`_CSS` 整体升级 + 各 section 增强（结构不要变，动效/视觉升级）：
- hero：深色科技层 + 右侧 mockup（已存在，加强玻璃框/光晕/扫描线）。
- `danger-band`（痛点）保留原文，视觉升级为警示玻璃卡。
- `capgroups`：分组玻璃卡 + hover。
- steps + `_flow_svg`：保持。
- stats（count-up + shimmer）、marquee：保持。
- `tier` 提示条：渐变发光。
- FAQ、`cta-band`、`x-links`：视觉升级 + 主 CTA 发光。
- `_index_lang`（features 总览）：当前太薄，**必须新增**：深色 hero（一句话定位 + 主 CTA + trust 行）+ 9 能力卡（玻璃卡+图标+箭头）+ CTA 带，再保留 9 卡网格。zh 版 `features_index` 不在范围（不得改）。

### 2.10 规则页（C 子任务）
结构保留（政策/违规代价/警示语样例/backfill 位置/FAQ），升级 `_CSS` + 页面外壳：深色页头（平台旗 + 国名 + 监管机构徽章）、内容卡玻璃化、警示语样例代码窗（gh-code）、合规 CTA 带（到 /{lang}/gpsr-check 与 /{lang}/compliance-check）。**平台数据（字符数、语言、监管机构）逐字保留。**

---

## 3. 转化布局规则（每页必检）

1. **价值主张前置**：H1 3 秒内说清「给谁、解决什么」。副标题点出「合规第一」。
2. **首屏双 CTA**：主（免费开始/注册）+ 次（免费体检）。主 CTA 渐变发光、hover 上浮。
3. **信任元素**：hero 下 trust 行（No credit card / 无需注册 / 5 次/天 等本页已有事实）；合规/监管徽章（EU 2023/988、Art.50、13 平台）。
4. **风险紧迫感**：合规 spotlight / danger band（缺欧代=下架、罚款 €15M）——用事实，不夸大、不编造。
5. **清晰下一步**：页中 tier/卡片与页尾 CTA 带都给出明确动作（注册 / 免费体检 / 查看定价）。
6. **禁止编造**：不得添加任何页面原有内容之外的事实、数据、客户证言、Logo、价格、日期。所有数字必须能在本语言现有页面中找到出处。
7. **配图**：每页至少一张内联 SVG 功能示意图（console 工作台 / 流程 / 清单面板 / 平台分布），复用 en 范本的 keyframes；**不引用外部图片 URL、不依赖网络资源**（本地 9000 离线可渲染）。
8. **本地化**：en/de/fr 页面禁止出现中文残留（导航/文案/alt 全部本语言）；专有名词（CrossAIO、GPSR、Art.50、eBay、UOKiK、ANPC、ProdSG、Loi Toubon、ACM、MIT、平台名）不翻译。

---

## 4. 工程约束

- 编码 UTF-8；文件内联 CSS/JS；不要新建外部 css/js 文件（effects.css/effects.js 已全局引用）。
- 模板文件（A/B/C）用 Python f-string 语法：模板内 `{`/`}` 需转义为 `{{`/`}}`；改完**必须** `python -m py_compile <file>` 通过。
- 静态页（D/E/F）：保留 `<head>` 的 title/meta/hreflang；`<html lang="...">` 正确；保留 `effects.css`/`effects.js` 引用与 lang 偏好脚本。
- 每完成一个文件：本地 `http://127.0.0.1:9000` 对应路由 200 + 无 JS 报错（可在浏览器/无头 Chrome 验证）。
- 工作目录：`D:\Claude\crossbot-ai`。**禁止** `git add/commit/push`、禁止修改 `site_nav.py`、`effects.*`、任何 zh 文件、`backend/app/static/gpsr-check-pl.html`、`gpsr-check-ro.html`。

## 5. 交付与自查（返回时逐条报告）

1. 列出改动的文件绝对路径 + 每个文件的改动摘要（一段话）。
2. 模板任务：`py_compile` 结果；静态任务：抽查 3 个路由的 200 + 首页渲染描述。
3. 自查清单逐项打勾：
   - [ ] 96 页语言纯净（无中文残留）
   - [ ] 价格/套餐数字未变（en €29/€49/€149；de €29/€99；fr €29/€99）
   - [ ] GPSR 2026-08-02 / EU 2023/988 / 13 平台 / Art.50 表述未变
   - [ ] 导航 10+7+4+Pricing 下拉完整、切换器在 nav 内、gap:3px
   - [ ] 每页至少 1 张内联 SVG 配图
   - [ ] 转化要素齐备（首屏 CTA + trust + 页尾 CTA 带）
   - [ ] 未触碰范围外文件
