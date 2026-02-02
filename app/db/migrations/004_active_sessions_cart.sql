ALTER TABLE public.active_sessions
  ADD COLUMN IF NOT EXISTS cart_json JSONB,
  ADD COLUMN IF NOT EXISTS cart_updated_at TIMESTAMPTZ;
