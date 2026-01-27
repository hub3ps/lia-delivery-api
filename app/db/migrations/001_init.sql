-- Core tables required by the workflows (no views here)

CREATE TABLE IF NOT EXISTS public.n8n_fila_mensagens (
  id BIGSERIAL PRIMARY KEY,
  id_mensagem TEXT NOT NULL,
  telefone TEXT NOT NULL,
  mensagem TEXT,
  timestamp TIMESTAMPTZ,
  client_id UUID,
  trace_id TEXT,
  message_id TEXT,
  remote_jid TEXT,
  message_type TEXT,
  status TEXT DEFAULT 'pending',
  locked_at TIMESTAMPTZ,
  locked_by TEXT,
  processed_at TIMESTAMPTZ,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_n8n_fila_tel_ts ON public.n8n_fila_mensagens (telefone, timestamp);
CREATE INDEX IF NOT EXISTS idx_n8n_fila_tel_status ON public.n8n_fila_mensagens (telefone, status);

CREATE TABLE IF NOT EXISTS public.active_sessions (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT UNIQUE NOT NULL,
  last_message TEXT,
  last_message_type TEXT,
  last_message_id TEXT,
  status TEXT DEFAULT 'active',
  followup_sent_at TIMESTAMPTZ,
  followup_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_active_sessions_status_updated ON public.active_sessions (status, updated_at);

CREATE TABLE IF NOT EXISTS public.orders (
  id BIGSERIAL PRIMARY KEY,
  order_id TEXT UNIQUE NOT NULL,
  telefone TEXT,
  status TEXT,
  cod_store TEXT,
  payload JSONB,
  response JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_telefone_created ON public.orders (telefone, created_at);

CREATE TABLE IF NOT EXISTS public.saipos_menu_raw (
  id BIGSERIAL PRIMARY KEY,
  client_id UUID,
  tipo TEXT,
  categoria TEXT,
  tamanho TEXT,
  id_store_item BIGINT,
  item TEXT,
  id_store_choice BIGINT,
  complemento TEXT,
  complemento_item TEXT,
  price NUMERIC,
  codigo_saipos TEXT,
  store_item_enabled TEXT,
  store_choice_enabled TEXT,
  store_choice_item_enabled TEXT,
  item_type TEXT,
  pdv_code TEXT,
  parent_pdv_code TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saipos_menu_client ON public.saipos_menu_raw (client_id);
