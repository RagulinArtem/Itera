"""Telegram Mini App initData validation."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote

from bot.config import settings


def validate_init_data(init_data: str, max_age: int = 86400) -> dict | None:
    """Validate Telegram WebApp initData. Returns user dict or None if invalid."""
    parsed = parse_qs(init_data, keep_blank_values=True)

    received_hash = parsed.get("hash", [None])[0]
    if not received_hash:
        return None

    # Check auth_date freshness
    auth_date = parsed.get("auth_date", [None])[0]
    if not auth_date:
        return None
    if time.time() - int(auth_date) > max_age:
        return None

    # Build data-check-string (sorted key=value, excluding hash)
    items = []
    for key, values in sorted(parsed.items()):
        if key == "hash":
            continue
        items.append(f"{key}={values[0]}")
    data_check_string = "\n".join(items)

    # HMAC-SHA256
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    user_raw = parsed.get("user", [None])[0]
    if not user_raw:
        return None

    return json.loads(unquote(user_raw))
