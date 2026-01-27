from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import crud
from app.settings import settings
from app.utils.time import format_horario


class FollowupService:
    def __init__(self, db_factory, llm_factory, evolution_client) -> None:
        self.db_factory = db_factory
        self.llm_factory = llm_factory
        self.evolution_client = evolution_client
        self.scheduler = BackgroundScheduler()

    def start(self) -> None:
        if not settings.followup_enabled:
            return
        self.scheduler.add_job(self.run_once, "interval", minutes=settings.followup_interval_minutes)
        self.scheduler.start()

    def run_once(self) -> None:
        with self.db_factory() as db:
            agent = self.llm_factory(db)
            rows = crud.fetch_followup_candidates(db)
            for row in rows:
                telefone = row.get("session_id")
                last_message = row.get("last_message") or ""
                last_type = row.get("last_message_type") or ""
                updated_at = row.get("updated_at")
                if isinstance(updated_at, datetime):
                    horario = format_horario(updated_at, settings.timezone)
                else:
                    horario = ""
                reply = agent.run_followup(last_message, telefone, horario, last_type)
                if reply:
                    self.evolution_client.send_text(settings.evolution_instance, telefone, reply)
                    crud.mark_followup_sent(db, telefone, reply)
