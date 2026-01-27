from app.db.session import get_db
from app.services.menu_service import MenuService
from app.services.saipos_client import SaiposClient
from app.settings import settings


def main():
    with get_db() as db:
        saipos = SaiposClient(settings.saipos_base_url, settings.saipos_partner_id, settings.saipos_partner_secret, settings.saipos_token_ttl_seconds)
        service = MenuService(db, saipos)
        result = service.generate_embeddings()
        print(result)


if __name__ == "__main__":
    main()
