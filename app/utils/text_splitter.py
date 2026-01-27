from __future__ import annotations

import re
from typing import List


def split_messages(text: str) -> List[str]:
    raw = (text or "").strip()
    if not raw:
        return [""]
    parts = re.split(r"\r?\n\r?\n+", raw)
    out = [p.strip() for p in parts if p.strip()]
    return out if out else [""]
