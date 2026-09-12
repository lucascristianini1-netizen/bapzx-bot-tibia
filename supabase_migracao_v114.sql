-- BAPZX/CALVAO bot-negocio v1.14.0
-- Pede colunas de feedback do cliente (aplicar no Supabase SQL Editor)
ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS feedback text;
ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS feedback_score integer;