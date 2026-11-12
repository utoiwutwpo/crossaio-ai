"""
API 请求/响应模型（Pydantic v2）
"""
from typing import List, Optional, Dict, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

PlanType = Literal["free", "starter", "pro", "business"]
PlatformType = Literal[
    "amazon", "tiktok", "ebay", "walmart",
    "cdiscount", "otto", "allegro", "emag", "fruugo", "kaufland", "zalando", "bol",
]
LanguageType = Literal[
    "en", "de", "fr", "es", "it", "ar", "tr", "hi", "ta", "te", "bn",
    "zh", "ja", "ko", "pl", "ro", "nl",
]
ToneType = Literal["professional", "casual", "premium", "fun"]
AdPlatformType = Literal["facebook", "google", "tiktok"]


# ========== 用户 ==========
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""
    company_name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Google Identity Services 返回的 ID token（credential）"""
    credential: str = Field(min_length=20, max_length=4096)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    plan: str
    usage_today: int
    daily_limit: int


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    company_name: str
    plan: str
    created_at: datetime
    usage_today: int = 0
    daily_limit: int = 0

    class Config:
        from_attributes = True


# ========== 产品描述 ==========
class ProductDescriptionRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    keywords: List[str] = Field(min_length=1, max_length=20)
    platform: PlatformType = "amazon"
    language: Optional[LanguageType] = None  # 缺省 → 按平台主推市场自动选择
    tone: ToneType = "professional"
    target_audience: Optional[str] = None
    unique_selling_points: Optional[List[str]] = None
    with_gpsr: bool = True  # 生成时附带 GPSR 合规块（CE 类目自动触发）
    cultural_adaptation: bool = True  # 文化本地化：按目标市场买家习惯改写卖点（非机翻）


class BulletPoint(BaseModel):
    heading: str
    content: str


class ProductDescriptionResponse(BaseModel):
    id: Optional[str] = None
    platform: Optional[str] = None
    provenance: Optional[Dict] = None   # Art.50(2) 机器可读标记
    provenance: Optional[Dict] = None   # Art.50(2) 机器可读标记
    language: str = "en"
    title: str
    bullet_points: List[BulletPoint]
    description: str
    search_terms: str
    character_count: int
    platform_compliant: bool
    optimization_score: float
    violations: List[str] = []
    # GPSR 合规（CE 类目自动附带）
    gpsr_risk_level: Optional[str] = None
    gpsr_block: Optional[str] = None
    # Rufus/iZi 语义搜索适配
    semantic_score: Optional[float] = None
    semantic_gaps: List[str] = []
    # 文化本地化（按市场买家习惯改写，非机翻）
    cultural_market: Optional[str] = None
    cultural_score: Optional[float] = None
    cultural_gaps: List[str] = []
    # P0-2 合规×运营一体化：最近一次合规体检未通过项注入
    compliance_note: Optional[str] = None
    related_audit_id: Optional[str] = None


# ========== GPSR 合规体检 ==========
class GpsrCheckRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    keywords: List[str] = Field(min_length=1, max_length=20)
    platform: PlatformType = "amazon"
    asin: Optional[str] = Field(
        None, min_length=10, max_length=10,
        description="Amazon ASIN（可选，仅作记录与报告关联；报告判定基于标题/关键词）")


class GpsrCheckResponse(BaseModel):
    risk_level: str                       # high / medium / low
    platform: str
    ce_required: bool
    matched_categories: str
    ce_directives: List[str] = []
    required_languages: List[str] = []
    category_notes: str = ""
    checklist: List[Dict] = []
    gpsr_block: Optional[str] = None      # 免费版脱敏为 None（付费钩子）
    upsell_note: Optional[str] = None
    asin: Optional[str] = None
    data_source: str = "title_keywords"   # 如实标注：判定基于标题/关键词


# ========== 多平台市场矩阵（欧洲主打） ==========
class MarketMatrixRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    keywords: List[str] = Field(min_length=1, max_length=20)
    platforms: List[PlatformType] = Field(min_length=1, max_length=9)
    tone: ToneType = "professional"
    target_audience: Optional[str] = None
    unique_selling_points: Optional[List[str]] = None
    language: Optional[LanguageType] = None  # 指定则覆盖所有平台的默认语言


class MarketMatrixResponse(BaseModel):
    product_name: str
    requested: int
    succeeded: int
    results: List[ProductDescriptionResponse]
    errors: List[Dict] = []


# ========== AI 客服 ==========
class CustomerServiceRequest(BaseModel):
    customer_message: str = Field(min_length=1, max_length=4000)
    order_id: Optional[str] = None
    language: Optional[LanguageType] = "en"   # 用于 Art.50 当地语言披露
    ai_act_disclosure: bool = True             # 默认开启 AI Act Art.50 身份告知注入
    platform: Optional[PlatformType] = None    # 缺省 → "amazon"；决定 GPSR 合规块语言与 Art.50 披露语言
    # 事实护栏：卖家/平台提供的真实数据；缺省时 AI 不得猜测时效或退货期限
    delivery_status: Optional[str] = Field(default=None, max_length=200)
    delivery_estimate: Optional[str] = Field(default=None, max_length=200)
    return_window_days: Optional[int] = Field(default=None, ge=0, le=365)


class CustomerServiceResponse(BaseModel):
    reply: str
    intent: str
    sentiment: str
    confidence: float
    needs_escalation: bool
    escalation_reason: Optional[str] = None
    # 政策安全红线层：命中的威胁类型 + 红线说明
    policy_flags: List[str] = []
    guardrail: Optional[str] = None
    # EU AI Act Art.50 透明度义务层（2026-08-02 生效）
    ai_act_disclosure: Optional[str] = None    # 当地语言「AI 身份告知」文本（前端须展示）
    ai_generated: bool = True                   # Art.50(2) 机器可读标记（合成内容）
    gpsr_incident: bool = False                 # 买家消息触发 GPSR 产品安全事件（合规优先回复已启用）
    # P0-2 合规×运营一体化：最近一次合规体检未通过项注入（事实回答 + 合规口径提示）
    compliance_note: Optional[str] = None
    related_audit_id: Optional[str] = None


# ========== P0-4 跨平台差评回复改写 ==========
class ReviewRewriteRequest(BaseModel):
    platform: str = Field(description="amazon / ebay")          # 决定规则模板
    review_snippet: str = Field(min_length=1, max_length=4000)  # 差评原文
    listing_ref: str = Field(default="", max_length=120)        # ASIN / item id / 链接
    mode: str = Field(default="both")                           # public / private / both


class ReviewRewriteResponse(BaseModel):
    id: int
    platform: str
    listing_ref: str = ""
    review_snippet: str
    public_reply: str = ""
    private_message: str = ""
    rule_check: Dict = {}          # 规则自查结果（通过项/待确认项/风险项）
    status: str                    # pending / approved / exported
    created_at: Optional[str] = None


# ========== EU 授权代表（欧代）台账 ==========
class EuRepCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=1000)
    email: str = ""
    phone: str = ""
    website: str = ""
    contact_person: str = ""
    is_default: bool = False


class EuRepSetDefault(BaseModel):
    rep_id: str


class EuRepOut(BaseModel):
    id: str
    company_name: str
    address: str
    email: str
    phone: str
    website: str
    contact_person: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 平台属性树校验 ==========
class AttributeValidateRequest(BaseModel):
    platform: PlatformType
    category: str = "generic"
    attributes: Dict[str, str] = {}


class AttributeValidateResponse(BaseModel):
    platform: str
    category: str
    missing: List[Dict] = []
    invalid: List[Dict] = []
    blockers: List[str] = []
    ready_to_list: bool
    completeness: float
    checked_total: int


# ========== 差评 → Listing 闭环 ==========
class ReviewInsightRequest(BaseModel):
    reviews: List[str] = Field(min_length=1, max_length=20,
                               description="粘贴的差评原文（1-20 条）")
    rating: Optional[int] = Field(None, ge=1, le=5, description="平均星级（可选）")
    material: Optional[str] = None
    battery_life: Optional[str] = None
    compatibility: Optional[str] = None


class ReviewInsightResponse(BaseModel):
    reviews_analyzed: int
    sentiment: str
    themes: List[Dict] = []          # theme/evidence/severity/listing_action/bullet_fix
    improved_bullets: List[BulletPoint] = []
    summary: str
    safety_alert: Optional[Dict] = None   # GPSR 安全事件预警（安全词命中时非空）


# ========== 埋点 ==========
class AnalyticsTrackRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=40)
    platform: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    meta: Dict = {}


# ========== 广告文案 ==========
class AdCopyRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    platform: AdPlatformType = "facebook"
    target_audience: str = Field(min_length=1, max_length=200)
    unique_selling_point: str = Field(min_length=1, max_length=300)
    tone: str = "persuasive"
    language: LanguageType = "en"


class AdCopyResponse(BaseModel):
    primary_text: str
    headline: str
    description: str
    cta: str
    hashtags: List[str]
    character_counts: Dict[str, int]


# ========== 订阅 ==========
class SubscriptionCreate(BaseModel):
    plan: Literal["starter", "pro", "business"]
    billing: Literal["monthly", "yearly"] = "monthly"


class SubscriptionInfo(BaseModel):
    plan: str
    stripe_status: str
    monthly_price_usd: Optional[float] = None
    usage_today: int
    daily_limit: int
    monthly_limit: Optional[int] = None
