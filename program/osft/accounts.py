"""People, PINs and permissions — mirrors OSBW V1.5 team access (people.json).

* Open mode until the first admin with a PIN exists (fresh install never locks you out).
* 6-digit PINs, salted PBKDF2 hashes; PINs are never stored or returned in clear.
* Roles: admin (everything), manager (OSBW default manager set), crew (count-only).
* A manager/crew login can be locked to one truck (OSBW "manager venue lock").
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid

PERMISSIONS = [
    "dashboard", "count", "voice_count", "inhouse", "inputs", "reports", "sheets", "menu", "orders",
    "stops", "transfers", "settings", "people", "staff_board", "other_trucks",
]
DEFAULT_PERMS = {
    "admin": {k: True for k in PERMISSIONS},
    "manager": {"dashboard": True, "count": True, "voice_count": True, "inhouse": True, "inputs": True,
                "reports": True, "sheets": True, "menu": True, "orders": True, "stops": True, "transfers": False,
                "settings": False, "people": False, "staff_board": True, "other_trucks": False},
    "crew": {"dashboard": True, "count": True, "voice_count": True, "inhouse": True, "inputs": False,
             "reports": False, "sheets": False, "menu": False, "orders": False, "stops": True, "transfers": False,
             "settings": False, "people": False, "staff_board": True, "other_trucks": False},
}
ROLES = tuple(DEFAULT_PERMS)
PIN_RE = re.compile(r"^\d{6}$")


def clean_count_types(v) -> list:
    """Which count types a login may start (empty = all). E.g. crew limited to ["daily"]."""
    if not isinstance(v, list):
        return []
    return [str(x).strip().lower()[:24] for x in v if str(x).strip()][:10]


def valid_pin(pin) -> bool:
    return bool(PIN_RE.match(str(pin or "")))


def hash_pin(pin: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", str(pin).encode(), bytes.fromhex(salt), 120_000).hex()
    return h, salt


def check_pin(pin: str, h: str, salt: str) -> bool:
    if not h or not salt:
        return False
    return hmac.compare_digest(hash_pin(pin, salt)[0], h)


def public_user(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("pin_hash", "pin_salt")} | {"has_pin": bool(u.get("pin_hash"))}


def auth_enabled(people: list[dict]) -> bool:
    return any(u.get("role") == "admin" and u.get("active", True) and u.get("pin_hash") for u in people)


def make_user(data: dict, existing: list[dict]) -> tuple[dict | None, str | None]:
    name = str(data.get("name") or "").strip()
    if not name:
        return None, "Name is required."
    role = str(data.get("role") or "crew").strip().lower()
    if role not in ROLES:
        return None, "Role must be admin, manager or crew."
    login = str(data.get("login") or name).strip().lower().replace(" ", ".")
    if any(u.get("login") == login for u in existing):
        return None, "That login name is taken."
    pin = data.get("pin")
    u = {"id": str(uuid.uuid4()), "name": name, "login": login, "role": role, "active": True,
         "email": str(data.get("email") or "").strip(), "phone": str(data.get("phone") or "").strip(),
         "truck_id": data.get("truck_id") or None, "permissions": dict(DEFAULT_PERMS[role]),
         "pin_hash": "", "pin_salt": ""}
    if pin not in (None, ""):
        if not valid_pin(pin):
            return None, "PIN must be exactly 6 digits."
        u["pin_hash"], u["pin_salt"] = hash_pin(pin)
    if role != "admin" and "count_types" in data:
        u["count_types"] = clean_count_types(data.get("count_types"))
    if isinstance(data.get("permissions"), dict) and role != "admin":
        for k, v in data["permissions"].items():
            if k in PERMISSIONS:
                u["permissions"][k] = bool(v)
    return u, None


def update_user(u: dict, data: dict, existing: list[dict]) -> str | None:
    if "name" in data:
        n = str(data["name"] or "").strip()
        if not n:
            return "Name is required."
        u["name"] = n
    if "login" in data:
        lg = str(data["login"] or "").strip().lower().replace(" ", ".")
        if not lg:
            return "Login is required."
        if any(o is not u and o.get("login") == lg for o in existing):
            return "That login name is taken."
        u["login"] = lg
    if "role" in data:
        r = str(data["role"] or "").lower()
        if r not in ROLES:
            return "Role must be admin, manager or crew."
        if u.get("role") != r:
            u["role"] = r
            u["permissions"] = dict(DEFAULT_PERMS[r])
    if "count_types" in data:
        u["count_types"] = [] if u.get("role") == "admin" else clean_count_types(data.get("count_types"))
    for k in ("email", "phone"):
        if k in data:
            u[k] = str(data[k] or "").strip()
    if "truck_id" in data:
        u["truck_id"] = data["truck_id"] or None
    if "active" in data:
        u["active"] = bool(data["active"])
    if "pin" in data and data["pin"] not in (None, ""):
        if not valid_pin(data["pin"]):
            return "PIN must be exactly 6 digits."
        u["pin_hash"], u["pin_salt"] = hash_pin(data["pin"])
    if isinstance(data.get("permissions"), dict):
        if u.get("role") == "admin":
            u["permissions"] = dict(DEFAULT_PERMS["admin"])
        else:
            for k, v in data["permissions"].items():
                if k in PERMISSIONS:
                    u.setdefault("permissions", {})[k] = bool(v)
    return None


# API path prefix → permission (checked only when auth is enabled)
ROUTE_PERMS = [
    ("/api/people", "people"), ("/api/trucks/transfer", "transfers"), ("/api/transfers", "transfers"),
    ("/api/settings", "settings"), ("/api/business", "settings"), ("/api/vendors", "orders"),
    ("/api/accounts/categories", "settings"), ("/api/accounts/pos", "settings"), ("/api/backup", "settings"),
    ("/api/restore", "settings"), ("/api/reset", "settings"), ("/api/seed", "settings"),
    ("/api/voice", "voice_count"), ("/api/count-types", "count"), ("/api/counts", "count"), ("/api/items/import", "sheets"),
    ("/api/catalog", "sheets"), ("/api/menu", "menu"), ("/api/pos", "inputs"), ("/api/sales", "inputs"),
    ("/api/receives", "inputs"), ("/api/invoice", "inputs"), ("/api/inputs", "inputs"), ("/api/orders", "orders"),
    ("/api/reorder", "orders"), ("/api/stops", "stops"), ("/api/reports", "reports"), ("/api/variance", "reports"),
    ("/api/export", "reports"), ("/api/staff-board", "staff_board"), ("/api/dashboard", "dashboard"),
    ("/api/backups", "settings"), ("/api/ai/settings", "settings"), ("/api/ai/test", "settings"),
    ("/api/ai/invoice", "inputs"), ("/api/ai/shelf", "count"), ("/api/ai/tidy", "count"), ("/api/onboarding/sample", "settings"), ("/api/onboarding/first-count", "count"),
]
WRITE_ONLY = {"/api/items": "sheets", "/api/sections": "settings"}   # reading items is fine for any logged-in user; writes need sheets


def required_perm(path: str, method: str) -> str | None:
    for prefix, perm in ROUTE_PERMS:
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
            # Settings GET is needed by every screen (locale, truck name) — only writes need the permission.
            if prefix in ("/api/settings", "/api/business") and method == "GET":
                return None
            return perm
    if path.startswith("/api/sections/") and path.endswith("/count"):
        return "count"
    if path.startswith("/api/trucks") and method not in ("GET", "HEAD") and not path.endswith("/activate"):
        return "settings"
    for prefix, perm in WRITE_ONLY.items():
        if (path == prefix or path.startswith(prefix + "/")) and method not in ("GET", "HEAD"):
            return perm
    return None
