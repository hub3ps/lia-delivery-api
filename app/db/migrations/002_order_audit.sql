CREATE TABLE IF NOT EXISTS public.order_audit (
  id bigserial PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now(),
  session_id text,
  telefone text,
  trace_id text,
  status text,
  agent_order_json jsonb,
  saipos_payload_json jsonb,
  error text
);

CREATE INDEX IF NOT EXISTS order_audit_session_id_idx ON public.order_audit (session_id);
CREATE INDEX IF NOT EXISTS order_audit_telefone_idx ON public.order_audit (telefone);
CREATE INDEX IF NOT EXISTS order_audit_created_at_idx ON public.order_audit (created_at DESC);
