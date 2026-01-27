# Lia Delivery (FastAPI)

Projeto Python que replica os workflows n8n do atendimento/integrações do Marcio Lanches.

## Rodar local

1) Crie o `.env` a partir do `.env.example`.
2) Suba Postgres (opcional via docker-compose):

```bash
docker-compose up -d db
```

3) Aplique a migration:

```bash
psql "$DATABASE_URL" -f app/db/migrations/001_init.sql
```

4) Instale dependências e rode:

```bash
pip install -e .
./scripts/dev.sh
```

Health check:

```bash
curl http://localhost:8000/healthz
```

## Rodar local sem Docker (Mac)

1) Crie o `.env` a partir do `.env.example`.
2) (Opcional) Crie e ative um venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3) Rode o script de dev (instala deps se necessário):

```bash
./scripts/dev.sh
```

4) Teste:

```bash
curl http://localhost:8000/healthz
```

## Endpoints

- `POST /v3.1` (webhook Evolution)
- `POST /webhooks/evolution` (alias)
- `POST /saipos-central` (webhook central Saipos)
- `POST /webhooks/saipos` (alias)
- `POST /marcio_lanches` (status de pedidos)
- `POST /enviar-pedido`
- `POST /cancelar_pedido`

### Exemplos (curl)

Webhook Evolution:
```bash
curl -X POST http://localhost:8000/v3.1 \
  -H 'Content-Type: application/json' \
  -d '{"data":{"key":{"id":"abc","remoteJid":"554799999999@s.whatsapp.net","fromMe":false},"message":{"conversation":"oi"},"messageTimestamp":1730000000},"instance":"inst1","server_url":"https://evo.example"}'
```

Enviar pedido:
```bash
curl -X POST http://localhost:8000/enviar-pedido \
  -H 'Content-Type: application/json' \
  -d '{"JSON":{"itens":[{"nome":"X Salada","qtd":1,"valor_unitario":28.00,"adicionais":[]}],"dados_cliente":{"nome":"Joao","telefone":"554799999999"},"tipo_entrega":"entrega","endereco":{"rua":"Rua A","numero":"10","bairro":"Centro","cep":"88300-000","complemento":"casa"},"pagamento":"credito","taxa_entrega":7,"desconto":0,"troco_para":0,"total":35}}'
```

Cancelar pedido:
```bash
curl -X POST http://localhost:8000/cancelar_pedido \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"123"}'
```

## Scripts

- `scripts/sync_menu.py` → sincroniza cardápio Saipos e grava em `public.saipos_menu_raw`
- `scripts/generate_embeddings.py` → gera embeddings a partir de `v_menu_catalog`

## Views necessárias no Supabase

As views abaixo **devem existir** (já existem no ambiente atual):
- `v_menu_catalog`
- `v_menu_search_index`
- `menu_catalog_agent_v1`
- `view_client_snapshot`

Se precisar recriar em ambiente local, use templates básicos (ajuste para o seu schema real):

```sql
-- Exemplo simplificado
CREATE VIEW v_menu_search_index AS
SELECT
  pdv_code AS pdv,
  item AS nome_original,
  item_type,
  parent_pdv_code AS parent_pdv,
  price,
  -- fingerprint deve ser gerado na ingestão (ver app/utils/fingerprints.py)
  ''::text AS fingerprint
FROM public.saipos_menu_raw;
```

> Observação: esta view acima é apenas um *template* e precisa refletir o schema real do Supabase.

## Embeddings

O workflow original grava em `menu_embeddings` com coluna `embedding` do tipo `vector` (pgvector).
Se ainda não existir, crie manualmente:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS menu_embeddings (
  id BIGSERIAL PRIMARY KEY,
  pdv TEXT,
  display_name TEXT,
  category TEXT,
  price NUMERIC,
  embedding VECTOR(1536)
);
```

## Observações de fidelidade

- Mensagens de status do pedido são iguais às do n8n (com emojis).
- URLs/tokens são lidos de variáveis de ambiente.
- Scheduler de follow-up roda por padrão a cada `FOLLOWUP_INTERVAL_MINUTES` (default 2).
