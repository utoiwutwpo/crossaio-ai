"""
CrossAIO — 全局配置
所有敏感信息从环境变量 / .env 读取，绝不硬编码。
"""
import os
from pydantic_settings import BaseSettings
from pathlib import Path

# .env 位置：backend/.env（不存在时全部走默认值，方便本地零配置跑通）
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # ===== AI（智谱 GLM-4，OpenAI 兼容接口）=====
    llm_api_key: str = ""  # 为空 → Mock 模式（本地开发/测试无需 Key）
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    llm_model: str = "glm-4-plus"

    # ===== 数据库 =====
    # 默认 SQLite（本地零配置）；上线换 Supabase PostgreSQL
    database_url: str = f"sqlite:///{Path(__file__).resolve().parent.parent / 'crossbot.db'}"

    # ===== 认证 =====
    jwt_secret: str = "dev-secret-change-me-before-production"
    jwt_expire_days: int = 30

    # ===== Google 登录（OAuth2 / Google Identity Services）=====
    # 为空 → Google 按钮显示"未配置"提示；填入后前端自动加载 GIS 弹窗
    google_client_id: str = ""
    google_client_secret: str = ""

    # ===== 出网代理（可选）=====
    # 中国大陆直连 Google 等海外 API 会被阻断：填本地代理如 http://127.0.0.1:7890（Clash 等）
    # 留空 = 直连（海外服务器部署时）
    proxy_url: str = ""

    # ===== 管理端点（埋点漏斗 /analytics/summary）=====
    # 上线前务必改成强随机值
    admin_token: str = ""

    # ===== 支付（Stripe，上线时填）=====
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""
    # 年付价格（相当于月付的年总价：€276 / €468 / €1428）
    stripe_price_starter_year: str = ""
    stripe_price_pro_year: str = ""
    stripe_price_business_year: str = ""

    # ===== 支付（PayPal，上线时填；与 Stripe 并行提供）=====
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_webhook_id: str = ""
    paypal_env: str = "sandbox"          # sandbox / live
    paypal_plan_starter: str = ""
    paypal_plan_pro: str = ""
    paypal_plan_business: str = ""

    # ===== eBay 接入（上线时填）=====
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_encryption_key: str = ""        # AES-256 加密密钥（base64），未配置则用固定 dev key

    # ===== Listing 监控（Phase 1：每日定时体检 + 风险日报）=====
    watch_scheduler_enabled: bool = True   # 上线后如用外部 cron 可关闭
    watch_daily_hour: int = 8              # 每日体检时间（UTC 小时）
    # SMTP（不配置则日报只入库不发邮件）
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_ssl: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # ===== 应用 =====
    app_name: str = "CrossAIO"
    app_url: str = "http://localhost:8000"
    # 对外公开域名（SEO/展示链接用：sitemap、canonical、RSS、邮件）。
    # 留空则回退 app_url。OAuth 回调始终用 app_url，与开发者控制台注册值保持一致。
    public_base_url: str = ""
    # SEO 身份域名（sitemap/robots/canonical/hreflang 用）：默认生产域名，
    # 本机/内网部署也会输出正确的收录地址，可用 SITE_PUBLIC_URL 覆盖。
    site_public_url: str = "https://www.crossaio.com"
    # Google Search Console 所有权验证文件内容（访问 /google****.html 时返回）。
    google_site_verification: str = ""
    cors_origins: str = "*"  # 生产改为具体域名

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def public_url(self) -> str:
        """对外公开基址：优先 PUBLIC_BASE_URL，否则回退 APP_URL。"""
        return (self.public_base_url or self.app_url).rstrip("/")

    @property
    def site_url(self) -> str:
        """SEO 身份基址：优先 SITE_PUBLIC_URL，否则回退 public_url。"""
        return (self.site_public_url or self.public_url).rstrip("/")


settings = Settings()

# 兼容 SQLite 的 check_same_thread
if settings.database_url.startswith("sqlite"):
    os.environ.setdefault("SQLALCHEMY_WARN_20", "0")
