"""Optional AI receipt/invoice reader hook for OSFT. OFF by default.

When the operator turns it on in Setup and supplies *their own* API key, an
attached invoice photo can be sent to an OpenAI-compatible vision endpoint
(``/v1/chat/completions``) which returns suggested receive lines. Nothing is
ever applied automatically: suggestions are shown for the operator to confirm.
With the hook off (default) OSFT never makes a network call; manual entry only.

GPLv3 — see LICENSE.txt.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import urllib.request
from pathlib import Path

DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

PROMPT = (
    "You read food-service supplier invoices and receipts. Return ONLY JSON: "
    '{"vendor": str, "date": "YYYY-MM-DD", "lines": [{"description": str, "qty": number, '
    '"unit": str, "unit_cost": number, "total": number}]}. Use null when unknown.'
)


class AIReaderDisabled(RuntimeError):
    pass


def public_config(cfg: dict | None) -> dict:
    cfg = cfg or {}
    return {
        "enabled": bool(cfg.get("enabled")),
        "endpoint": cfg.get("endpoint") or DEFAULT_ENDPOINT,
        "model": cfg.get("model") or DEFAULT_MODEL,
        "has_key": bool(cfg.get("api_key")),
    }


def read_image(path: Path, cfg: dict | None, timeout: int = 60) -> dict:
    cfg = cfg or {}
    if not cfg.get("enabled"):
        raise AIReaderDisabled("AI reading is off. Enter the invoice manually or enable it in Setup.")
    if not cfg.get("api_key"):
        raise AIReaderDisabled("AI reading is on but no API key is saved.")
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    body = {
        "model": cfg.get("model") or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        cfg.get("endpoint") or DEFAULT_ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg['api_key']}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)
