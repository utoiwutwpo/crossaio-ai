"""12 平台店铺授权子包。"""
from .spec import (AUTH_SPECS, FIELD_LABELS, PLATFORM_ORDER, all_specs,  # noqa: F401
                   get_spec, supports_authorize_url)
from .providers import (build_authorize_url, exchange_code,  # noqa: F401
                        validate_shape, verify_credential, verify_many)
