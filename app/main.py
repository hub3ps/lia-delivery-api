from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.api.routes_webhooks import router as webhooks_router
from app.db.session import get_db
from app.logging_config import init_logging
from app.services.evolution_client import EvolutionClient
from app.services.followup_service import FollowupService
from app.services.geocode_service import GeocodeService
from app.services.llm_agent import LLMAgent
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.saipos_client import SaiposClient
from app.settings import settings

app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(webhooks_router)


@app.on_event("startup")
def startup() -> None:
    init_logging(settings.log_level)

    def llm_factory(db):
        saipos = SaiposClient(settings.saipos_base_url, settings.saipos_partner_id, settings.saipos_partner_secret, settings.saipos_token_ttl_seconds)
        menu = MenuService(db, saipos)
        orders = OrderService(db, saipos)
        geocode = GeocodeService(settings.google_maps_api_key)
        atendente_prompt = open("prompts/atendente.md", "r", encoding="utf-8").read()
        followup_prompt = open("prompts/followup.md", "r", encoding="utf-8").read()
        return LLMAgent(db, orders, menu, geocode, atendente_prompt, followup_prompt)

    evolution = EvolutionClient(settings.evolution_base_url, settings.evolution_api_key)
    followup = FollowupService(get_db, llm_factory, evolution)
    followup.start()
