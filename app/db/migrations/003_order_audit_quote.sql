ALTER TABLE public.order_audit
  ADD COLUMN IF NOT EXISTS quoted_json jsonb;
