from __future__ import annotations

import re


def normalize_phone(raw: str | None) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"\D+", "", str(raw))
    cleaned = cleaned.lstrip("0")
    if cleaned and not cleaned.startswith("55"):
        cleaned = "55" + cleaned
    return cleaned


def extract_phone_from_jid(jid: str | None) -> str:
    if not jid:
        return ""
    if "@" in jid:
        jid = jid.split("@")[0]
    return normalize_phone(jid)


def is_group_jid(jid: str | None) -> bool:
    if not jid:
        return False
    return jid.endswith("@g.us")
