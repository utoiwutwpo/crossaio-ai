"""四语种文本层：EN / DE / FR / PL 一次同时解析。

设计：
- 复用既有 PLATFORM_CRED_I18N（en/de/fr），只补波兰语包，避免重复维护三份文案。
- 对外只暴露两个入口：platform_text() 单语种、platform_text_all() 四语种同时返回。
- 缺失语种一律回退英文，绝不返回空串（前端拿不到文案会直接白屏）。
"""
from .locales import (  # noqa: F401
    LANGS,
    STATUS_TEXT,
    platform_text,
    platform_text_all,
    matrix_all_locales,
    status_text,
)
