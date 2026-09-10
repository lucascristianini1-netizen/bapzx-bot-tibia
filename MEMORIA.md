# BAPZX Tibia Coins Bot — Memória do projeto

Atendente IA de venda de Tibia Coins via Telegram (Flask webhook + Google Gemini).

## Estrutura

- `bot.py` — webhook Flask: `/` (health), `/webhook` (mensagens), `/pedidos` (contagem), comandos `/id`.
- `persona.txt` — persona da loja e regras de atendimento.
- `pedidos.json` — pedidos salvos (runtime, fora do git).
- `requirements.txt` — flask, requests, google-genai.
- `.env` — segredos (fora do git).

## Variáveis de ambiente

- `TELEGRAM_BOT_TOKEN` (obrigatório, no `.env` local e no Render).
- `TELEGRAM_OWNER_CHAT_ID` = `1695600926` (aviso de novo pedido).
- `GOOGLE_API_KEY` — fallback lido de `gemini-cli/.env`; no Render deve estar configurada.

## Decisões

- Pedido detectado por palavras-chave em conversa privada; salvo em `pedidos.json` e dono notificado (mensagem "🛒 NOVO PEDIDO").
- Preços fixos na persona (100 a 2500 TC). Pagamento: Pix. Entrega: Trade in-game (pedir mundo e char).
- Fallback de modelo IA: gemini-3.6-flash → gemini-3-flash-preview → gemini-3.5-flash.

## Testes feitos (09/09/2026)

- Local: pedido de teste `quero comprar 500 tc` registrado (2 pedidos) e notificação enviada.
- Render: health `200 - bot ok`; webhook respondeu `200` a `quero comprar 250 tc`; `/pedidos` == 1 (filesystem do deploy é separado do local).
- Webhook aponta para `https://bapzx-bot-tibia.onrender.com/webhook`.

## Pendências

- Rotacionar `TELEGRAM_BOT_TOKEN` (exposto no terminal durante sessão — gerar novo no BotFather e atualizar `.env` + Render).
- Estruturar pedidos (valor TC, preço, Pix, mundo/char) em vez de mensagem crua.
- Persistência no Render: free tier tem filesystem efêmero — `pedidos.json` zera a cada redeploy; migrar para banco (ex: Supabase) ou storage persistente.
- Teste real end-to-end: enviar mensagem real do Telegram e validar resposta da IA + aviso ao dono.
- Remover placeholders pendentes da persona, se houver.