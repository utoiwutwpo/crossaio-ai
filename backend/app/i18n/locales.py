"""四语种文本（EN / DE / FR / PL）。

en / de / fr 直接复用 experts.platform_credentials.PLATFORM_CRED_I18N，
本文件只补 pl，并统一补齐缺失语种的英文回退。
"""
from typing import Dict, List

LANGS: tuple = ("en", "de", "fr", "pl")

# 波兰语包：与注册表同 key，字段顺序一致（label / apply_note / unlocks）。
PL_PACK: Dict[str, dict] = {
    "amazon": {
        "label": "Amazon Europa",
        "apply_note": "Seller Central → Integracja → Deweloper, zarejestruj aplikację LWA; "
                      "konto Professional, część uprawnień wymaga weryfikacji przez Amazon (1–3 dni).",
        "unlocks": "Zwrot bloku zgodności GPSR do prawdziwych ofert Amazon",
    },
    "ebay": {
        "label": "eBay",
        "apply_note": "Sprzedawca nie potrzebuje własnego konta dewelopera: po skonfigurowaniu "
                      "aplikacji wystarczy kliknąć „Autoryzuj”, aby dokończyć OAuth.",
        "unlocks": "Synchronizacja wiadomości kupujących w czasie rzeczywistym",
    },
    "allegro": {
        "label": "Allegro (Polska)",
        "apply_note": "Darmowa rejestracja aplikacji na developer.allegro.pl — Client ID/Secret "
                      "otrzymasz natychmiast (sandbox od razu, produkcja zatwierdzana automatycznie).",
        "unlocks": "Automatyczny import wiadomości kupujących po polsku",
    },
    "otto": {
        "label": "Otto (Niemcy)",
        "apply_note": "Sprzedawcy OTTO Marketplace mogą wnioskować o dostęp API na "
                      "developer.otto.market; wymagane aktywne konto sprzedawcy.",
        "unlocks": "Import wiadomości kupujących po niemiecku",
    },
    "kaufland": {
        "label": "Kaufland (Niemcy / Europa Środkowa)",
        "apply_note": "Najniższy próg wejścia: Portal Sprzedawcy Kaufland → Ustawienia → API "
                      "generuje Client-Key / Secret-Key bez dodatkowej weryfikacji.",
        "unlocks": "Import wiadomości kupujących z wielu krajów",
    },
    "cdiscount": {
        "label": "Cdiscount (Francja)",
        "apply_note": "Rejestracja na dev.cdiscount.com wymaga powiązania konta sprzedawcy; "
                      "dane API (v2 OAuth2 / SOAP) przesyłane przez operatora.",
        "unlocks": "Import wiadomości kupujących po francusku",
    },
    "emag": {
        "label": "eMAG (Rumunia)",
        "apply_note": "Panel eMAG Marketplace → Ustawienia → Dostęp API, token dostępny od razu.",
        "unlocks": "Import wiadomości kupujących po rumuńsku",
    },
    "zalando": {
        "label": "Zalando (moda europejska)",
        "apply_note": "Klienci programu Zalando Partner (zDirect) mogą wnioskować o klienta API; "
                      "weryfikacja jest rygorystyczna.",
        "unlocks": "Wielojęzyczny import wiadomości kupujących",
    },
    "bol": {
        "label": "bol.com (Holandia / Belgia)",
        "apply_note": "developer.bol.com — zaloguj się kontem sprzedawcy i utwórz dane API "
                      "(Client ID + Secret), aktywne natychmiast.",
        "unlocks": "Import wiadomości kupujących po niderlandzku",
    },
    "walmart": {
        "label": "Walmart (USA)",
        "apply_note": "Walmart Seller Center → Ustawienia → generowanie API Key (natychmiast).",
        "unlocks": "Import wiadomości kupujących po angielsku",
    },
    "fruugo": {
        "label": "Fruugo (paneuropejski)",
        "apply_note": "Portal Fruugo → Konto → API, generuje Merchant ID + API Key.",
        "unlocks": "Wielojęzyczny import wiadomości kupujących",
    },
    "tiktok": {
        "label": "TikTok Shop",
        "apply_note": "TikTok Shop Partner Center → Deweloper → utwórz aplikację "
                      "(sprzedawca indywidualny może użyć aplikacji własnej).",
        "unlocks": "Import wiadomości kupujących + zgodne odpowiedzi",
    },
}

# 授权状态机文案（四语种）。
STATUS_TEXT: Dict[str, Dict[str, str]] = {
    "unconnected": {
        "en": "Not connected",
        "de": "Nicht verbunden",
        "fr": "Non connecté",
        "pl": "Nie połączono",
    },
    "pending": {
        "en": "Credentials incomplete",
        "de": "Zugangsdaten unvollständig",
        "fr": "Identifiants incomplets",
        "pl": "Niekompletne dane dostępowe",
    },
    "connected": {
        "en": "Connected (format check passed)",
        "de": "Verbunden (Formatprüfung bestanden)",
        "fr": "Connecté (format validé)",
        "pl": "Połączono (format zweryfikowany)",
    },
    "live_ok": {
        "en": "Connected (live API check passed)",
        "de": "Verbunden (Live-API-Prüfung bestanden)",
        "fr": "Connecté (vérification API en direct réussie)",
        "pl": "Połączono (test API na żywo zaliczony)",
    },
    "live_fail": {
        "en": "Live check failed",
        "de": "Live-Prüfung fehlgeschlagen",
        "fr": "Échec de la vérification en direct",
        "pl": "Test na żywo nieudany",
    },
    "live_unavailable": {
        "en": "Live check not enabled for this platform",
        "de": "Live-Prüfung für diese Plattform nicht aktiviert",
        "fr": "Vérification en direct non activée pour cette plateforme",
        "pl": "Test na żywo niedostępny dla tej platformy",
    },
}

_FALLBACK_LANG = "en"


def _i18n_source() -> Dict[str, Dict[str, dict]]:
    """延迟导入，避免与 experts 包形成循环依赖。"""
    from ..experts.platform_credentials import PLATFORM_CRED_I18N
    return PLATFORM_CRED_I18N


def _pack_for(lang: str) -> Dict[str, dict]:
    if lang == "pl":
        return PL_PACK
    return _i18n_source().get(lang, {})


def platform_text(platform: str, lang: str = "en") -> Dict[str, str]:
    """单语种文案；缺失或字段不全时逐字段回退英文。"""
    lang = lang if lang in LANGS else _FALLBACK_LANG
    out: Dict[str, str] = {}
    for field in ("label", "apply_note", "unlocks"):
        val = (_pack_for(lang).get(platform) or {}).get(field)
        if not val:
            val = (_pack_for(_FALLBACK_LANG).get(platform) or {}).get(field)
        out[field] = val or platform
    return out


def platform_text_all(platform: str) -> Dict[str, Dict[str, str]]:
    """四语种同时返回：{en: {...}, de: {...}, fr: {...}, pl: {...}}。"""
    return {lang: platform_text(platform, lang) for lang in LANGS}


def status_text(status: str, lang: str = "en") -> str:
    labels = STATUS_TEXT.get(status) or {}
    return labels.get(lang) or labels.get(_FALLBACK_LANG) or status


def matrix_all_locales(platforms: List[str],
                       statuses: Dict[str, str]) -> List[dict]:
    """12 平台 × 4 语种一次性组装（凭证中心与状态矩阵的单一数据源）。"""
    rows = []
    for p in platforms:
        status = statuses.get(p, "unconnected")
        rows.append({
            "platform": p,
            "status": status,
            "status_text": {lang: status_text(status, lang) for lang in LANGS},
            "text": platform_text_all(p),
        })
    return rows
