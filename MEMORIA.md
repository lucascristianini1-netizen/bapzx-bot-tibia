# BAPZX Tibia Coins Bot — Memória do projeto

Atendente IA de venda de Tibia Coins via Telegram (Flask webhook + Google Gemini).
Versão atual do bot: **1.2.0**.

## Estrutura

- `bot.py` — webhook Flask: `/` (health, informa versão), `/webhook` (mensagens), `/pedidos` (contagem), comandos `/id`.
- `storage.py` — `OrderStore`: salva/lista pedidos em Supabase (persistente) com fallback em `pedidos.json`.
- `persona.txt` — persona da loja e regras de atendimento.
- `pedidos.json` — pedidos salvos (runtime, fora do git, usado como fallback).
- `scripts/criar_tabela_supabase.sql` — DDL da tabela `public.pedidos` para o Supabase.
- `requirements.txt` — flask, requests, google-genai.
- `.env` — segredos (fora do git).

## Variáveis de ambiente

- `TELEGRAM_BOT_TOKEN` (obrigatório, no `.env` local e no Render).
- `TELEGRAM_OWNER_CHAT_ID` = `1695600926` (aviso de novo pedido).
- `GOOGLE_API_KEY` — fallback lido de `gemini-cli/.env`; no Render deve estar configurada.
- `SUPABASE_URL` e `SUPABASE_KEY` — persistência em nuvem (opcional). Sem elas o bot grava só no arquivo local.

## Decisões

- Pedido detectado por palavras-chave em conversa privada; salvo de forma **estruturada** (TC, preço da tabela, pagamento, mundo, char) e dono notificado (mensagem "🛒 NOVO PEDIDO").
- Preços fixos na persona (100 a 2500 TC). Pagamento: Pix. Entrega: Trade in-game (pedir mundo e char).
- Fallback de modelo IA: gemini-3.6-flash → gemini-3-flash-preview → gemini-3.5-flash.
- Persistência: `OrderStore` usa Supabase (REST) como fonte de verdade quando `SUPABASE_URL`/`SUPABASE_KEY` estão setadas; falha/ausência cai para `pedidos.json` (local). Contagem (`/pedidos`) vem do Supabase via `Prefer: count=exact`, com fallback no arquivo.

## Testes feitos (09/09/2026)

- Local: pedido de teste `quero comprar 500 tc` registrado (2 pedidos) e notificação enviada.
- Render: health `200 - bot ok`; webhook respondeu `200` a `quero comprar 250 tc`; `/pedidos` == 1 (filesystem do deploy é separado do local).
- Webhook aponta para `https://bapzx-bot-tibia.onrender.com/webhook`.

## Testes feitos (10/09/2026)

- v1.2.0 (estrutura + persistência): `quero comprar 1000 tc, pagamento pix, mundo pacera, char Nap Lord` → extrato `tc=1000, preco=R$90, pag=Pix, mundo=pacera, char=nap lord`; `quero comprar 250 tc` → `tc=250, preco=R$22,50`. Health exibe `bot ok v1.2.0`. Contagem `/pedidos` == 3.

## Pendências

- **Supabase**: criar projeto, rodar `scripts/criar_tabela_supabase.sql`, preencher `SUPABASE_URL`/`SUPABASE_KEY` no `.env` local e no Render, e testar no deploy.
- Rotacionar `TELEGRAM_BOT_TOKEN` (exposto no terminal durante sessão — gerar novo no BotFather e atualizar `.env` + Render).
- Teste real end-to-end: enviar mensagem real do Telegram e validar resposta da IA + aviso ao dono.
- Tratar pedido assíncrono: cliente informa mundo/char depois do valor (pedido parcial).
- Remover placeholders pendentes da persona, se houver.