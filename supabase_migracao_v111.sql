-- Migração v1.11.0 — Áreas de cliente e administrador (login com Google)
-- Rodar no Supabase > SQL Editor > New query, e executar o bloco inteiro.

-- 1) Vínculo dos pedidos com a conta Google do cliente:
--    cada pedido passa a guardar o e-mail usado na cobrança do Pix.
ALTER TABLE pedidos
  ADD COLUMN IF NOT EXISTS email TEXT;

-- 2) Perfis: quem logou com Google, nome e papel (cliente/admin).
CREATE TABLE IF NOT EXISTS profiles (
  email      TEXT PRIMARY KEY,
  name       TEXT,
  sub        TEXT,
  role       TEXT NOT NULL DEFAULT 'cliente',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'cliente';
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS sub TEXT DEFAULT '';
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

-- Verificação rápida (deve listar as colunas de pedidos, incluindo email):
-- SELECT column_name FROM information_schema.columns WHERE table_name='pedidos' ORDER BY ordinal_position;