from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

PT_WEEKDAYS = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


def format_horario(dt: datetime, tz: str = "America/Sao_Paulo") -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    local = dt.astimezone(ZoneInfo(tz))
    weekday = PT_WEEKDAYS[local.weekday()]
    return f"{weekday}, {local:%d/%m/%Y %H:%M}"
