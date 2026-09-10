-- Migracao para a Fase B - identificacao/status de pagamento Pix.
-- Rode no SQL Editor do Supabase (uma vez).

alter table public.pedidos
  add column if not exists status          text default 'pendente';
alter table public.pedidos
  add column if not exists pix_confirmado_em timestamptz;
alter table public.pedidos
  add column if not exists entregue_em     timestamptz;

-- Status possiveis: pendente | pago | entregue | cancelado
-- USO: o bot marca 'pendente' ao receber o pedido; o dono confirma o
-- Pix (chat do dono -> /pago <id>) e depois /entregue <id>.