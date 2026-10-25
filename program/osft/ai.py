"""Optional AI connection (Settings › AI). OFF by default; nothing here runs unless the owner turns it on.

Speaks the OpenAI-compatible ``/chat/completions`` API, which OpenAI, xAI, Anthropic (compat endpoint),
Ollama and most others accept. The API key lives only in the server's data/config.json and is never
returned to the browser. Every result is a *proposal* the user reviews before anything is saved.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request

PRESETS = {
    "openai": {"label": "OpenAI (ChatGPT)", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "needs_key": True},
    "anthropic": {"label": "Anthropic (Claude)", "base_url": "https://api.anthropic.com/v1", "model": "claude-sonnet-4-5", "needs_key": True},
    "xai": {"label": "xAI (Grok)", "base_url": "https://api.x.ai/v1", "model": "grok-4", "needs_key": True},
    "ollama": {"label": "Ollama (on this computer)", "base_url": "http://localhost:11434/v1", "model": "llama3.2-vision", "needs_key": False},
    "custom": {"label": "Other (OpenAI-compatible)", "base_url": "", "model": "", "needs_key": False},
}


class AIOff(RuntimeError):
    """Raised instead of making any network call when AI is off or not set up."""


class AIError(RuntimeError):
    pass


def public(cfg: dict | None) -> dict:
    cfg = cfg or {}
    k = cfg.get("api_key") or ""
    return {"enabled": bool(cfg.get("enabled")), "provider": cfg.get("provider") or "openai",
            "base_url": cfg.get("base_url") or "", "model": cfg.get("model") or "", "has_key": bool(k),
            "key_hint": ("…" + k[-4:]) if len(k) >= 8 else "", "last_test": cfg.get("last_test")}


def update(cfg: dict | None, data: dict) -> tuple[dict | None, str | None]:
    cfg = dict(cfg or {})
    if not cfg.get("provider"):
        cfg.update(provider="openai", base_url=cfg.get("base_url") or PRESETS["openai"]["base_url"],
                   model=cfg.get("model") or PRESETS["openai"]["model"])
    if "provider" in data:
        p = str(data["provider"] or "")
        if p not in PRESETS:
            return None, "Unknown AI provider."
        if p != cfg.get("provider"):
            cfg["provider"] = p
            cfg["base_url"] = PRESETS[p]["base_url"]
            cfg["model"] = PRESETS[p]["model"]
    for k in ("base_url", "model"):
        if k in data and data[k] is not None:
            cfg[k] = str(data[k]).strip()
    if cfg.get("base_url") and not re.match(r"^https?://", cfg["base_url"]):
        return None, "The address must start with http:// or https://"
    if data.get("api_key"):
        cfg["api_key"] = str(data["api_key"]).strip()
    if data.get("clear_key"):
        cfg.pop("api_key", None)
    if "enabled" in data:
        cfg["enabled"] = bool(data["enabled"])
    prov = PRESETS.get(cfg.get("provider") or "openai", PRESETS["custom"])
    if cfg.get("enabled"):
        if not cfg.get("base_url") or not cfg.get("model"):
            return None, "Fill in the address and model before turning AI on."
        if prov["needs_key"] and not cfg.get("api_key"):
            return None, "Add your API key before turning AI on."
    return cfg, None


def _ready(cfg: dict | None, require_enabled: bool = True) -> dict:
    cfg = cfg or {}
    if require_enabled and not cfg.get("enabled"):
        raise AIOff("AI is off. Turn it on in Settings › AI, or enter this by hand.")
    if not cfg.get("base_url") or not cfg.get("model"):
        raise AIOff("AI isn't set up yet (address and model). See Settings › AI.")
    return cfg


def chat(cfg: dict, content, *, want_json: bool = True, max_tokens: int = 2000, timeout: int = 90,
         require_enabled: bool = True, opener=None) -> str:
    cfg = _ready(cfg, require_enabled)
    url = cfg["base_url"].rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    body = {"model": cfg["model"], "max_tokens": max_tokens, "messages": [{"role": "user", "content": content}]}
    if want_json and (cfg.get("provider") in ("openai", "xai", "ollama")):
        body["response_format"] = {"type": "json_object"}
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
        if cfg.get("provider") == "anthropic":
            headers["x-api-key"] = cfg["api_key"]
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode()).get("error", {})
            detail = detail.get("message") if isinstance(detail, dict) else str(detail)
        except Exception:
            pass
        raise AIError(f"The AI service said {e.code}{': ' + detail if detail else ''}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AIError(f"Couldn't reach the AI service ({getattr(e, 'reason', e)}).") from None
    try:
        return payload["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise AIError("The AI service sent back something we couldn't read.") from None


def parse_json(text: str) -> dict:
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        raise AIError("The AI answer wasn't JSON.")
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        raise AIError("The AI answer wasn't valid JSON.") from None


def test(cfg: dict, opener=None) -> str:
    out = chat(cfg, 'Reply with the JSON {"ok": true} and nothing else.', max_tokens=20, timeout=30,
               require_enabled=False, opener=opener)
    return out.strip()[:120]


def _num(v):
    if v in (None, ""):
        return None
    try:
        return round(float(str(v).replace("$", "").replace(",", "")), 4)
    except ValueError:
        return None


# ---------- files → message parts ----------

def pdf_text(data: bytes) -> str:
    if not shutil.which("pdftotext"):
        return ""
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        try:
            return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=30).stdout.decode("utf-8", "ignore")
        except Exception:
            return ""


def file_parts(files: list[tuple[bytes, str]]) -> list[dict]:
    parts = []
    for data, mime in files:
        if mime == "application/pdf":
            txt = pdf_text(data)
            if not txt.strip():
                raise AIError("That PDF has no readable text (it's probably a scan). Take a photo of it instead.")
            parts.append({"type": "text", "text": "Invoice text:\n" + txt[:20000]})
        elif mime.startswith("image/"):
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}})
    return parts


# ---------- invoice ----------

INVOICE_PROMPT = (
    "You read food-service supplier invoices for a food truck. Return ONLY JSON: "
    '{"vendor": string|null, "invoice_no": string|null, "date": "YYYY-MM-DD"|null, "lines": [{"description": string, '
    '"qty": number|null, "unit": string|null, "unit_cost": number|null, "total": number|null}]}. '
    "One line per product. qty is cases/units received; unit_cost is price per that unit. Use null when unsure. Don't invent lines."
)


def clean_invoice(raw: dict) -> dict:
    lines = []
    for ln in raw.get("lines") or []:
        if not isinstance(ln, dict):
            continue
        desc = str(ln.get("description") or ln.get("name") or "").strip()
        if not desc:
            continue
        qty, uc, tot = _num(ln.get("qty")), _num(ln.get("unit_cost")), _num(ln.get("total"))
        if uc is None and tot is not None and qty:
            uc = round(tot / qty, 4)
        lines.append({"description": desc[:120], "qty": qty, "unit": (str(ln.get("unit") or "").strip()[:20] or None),
                      "unit_cost": uc, "total": tot})
    date = str(raw.get("date") or "")[:10]
    return {"vendor": (str(raw.get("vendor") or "").strip()[:80] or None),
            "invoice_no": (str(raw.get("invoice_no") or "").strip()[:40] or None),
            "date": date if re.match(r"^\d{4}-\d{2}-\d{2}$", date) else None, "lines": lines}


def extract_invoice(cfg: dict, files: list[tuple[bytes, str]], opener=None) -> dict:
    _ready(cfg)
    parts = [{"type": "text", "text": INVOICE_PROMPT}] + file_parts(files)
    return clean_invoice(parse_json(chat(cfg, parts, opener=opener)))


# ---------- shelf / walk ----------

SHELF_PROMPT = (
    "You help a food-truck owner list what's stored in one section of the truck: “{section}”. "
    "Return ONLY JSON: {{\"items\": [{{\"name\": string, \"qty\": number|null, \"unit\": string, \"category\": string}}]}}. "
    "Use short, plain product names (e.g. \"Corn tortillas\", \"Chicken thigh\"). unit is how it's counted: "
    "case, lb, ea, bag, can, qt, gal, pack, box, tub, bottle. qty is how many you can see or were told; null if unknown. "
    "Prefer these names when they match: {known}. Don't invent items."
)


def clean_items(raw: dict) -> list[dict]:
    out, seen = [], set()
    for it in raw.get("items") or []:
        if not isinstance(it, dict):
            continue
        name = re.sub(r"\s+", " ", str(it.get("name") or "")).strip()[:80]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        q = _num(it.get("qty"))
        out.append({"name": name[0].upper() + name[1:], "qty": q if q is None or q >= 0 else None,
                    "unit": (str(it.get("unit") or "ea").strip().lower()[:20] or "ea"),
                    "category": (str(it.get("category") or "Other").strip()[:40] or "Other")})
    return out


def propose_shelf(cfg: dict, section: str, known: list[str], image: tuple[bytes, str] | None = None,
                  text: str = "", opener=None) -> list[dict]:
    _ready(cfg)
    if not image and not text.strip():
        raise AIError("Add a photo or say what's there first.")
    prompt = SHELF_PROMPT.format(section=section, known=", ".join(known[:150]) or "(none yet)")
    parts = [{"type": "text", "text": prompt}]
    if text.strip():
        parts.append({"type": "text", "text": "What the owner said or typed:\n" + text[:6000]})
    if image:
        parts += file_parts([image])
    return clean_items(parse_json(chat(cfg, parts, opener=opener)))
