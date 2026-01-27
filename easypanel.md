# Deploy no EasyPanel

1) Crie um novo serviço (Dockerfile).
2) Configure domínio (ex: `api.hub3ps.com`).
3) Variáveis de ambiente (exemplo):

```
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
EVOLUTION_BASE_URL=https://evo.hub3ps.com
EVOLUTION_API_KEY=...
EVOLUTION_INSTANCE=...
SAIPOS_PARTNER_ID=...
SAIPOS_PARTNER_SECRET=...
SAIPOS_COD_STORE=MAR001
OPENAI_API_KEY=...
GOOGLE_MAPS_API_KEY=...
CLIENT_ID=06a81600-26fc-472b-880e-e6293943354e
```

4) Health check: `GET /healthz`
5) Porta interna: `8000`
6) (Opcional) Worker para scripts:
   - `python scripts/sync_menu.py`
   - `python scripts/generate_embeddings.py`

## Observações

- Garanta que as views do Supabase existem (`v_menu_catalog`, `v_menu_search_index`, `menu_catalog_agent_v1`, `view_client_snapshot`).
- Se usar `unaccent` na query de taxa de entrega, habilite a extensão no Postgres.
