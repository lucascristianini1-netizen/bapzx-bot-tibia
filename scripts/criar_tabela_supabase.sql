-- Tabela de pedidos do bot BAPZX Tibia Coins (Supabase).
-- Rode no SQL Editor do seu projeto Supabase.

create table if not exists public.pedidos (
  id        bigint generated always as identity primary key,
  data      timestamptz not null,
  chat_id   bigint,
  usuario   text,
  mensagem  text,
  tc        integer,
  preco     text,
  pagamento text,
  mundo     text,
  char      text
);

-- Após criar, copie para as Environment Variables do bot:
--   SUPABASE_URL = https://SEU-PROJETO.supabase.co
--   SUPABASE_KEY = sua service role key (Project Settings -> API)
-- Adicione no .env local e no Render. Sem essas variáveis o bot
-- continua funcionando em modo arquivo (pedidos.json).