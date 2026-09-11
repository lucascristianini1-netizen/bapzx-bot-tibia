# BAPZX Tibia Coins Bot — Memória do projeto

## PROTOCOLO DE REENTRADA (atualizado no último check-out)

- Onde paramos: v1.9.0 — REBRAND: empresa é BAPZX (main), loja de Tibia Coins vira RUBINI COINS (opção "BAPZX RUBINOT"); novo Serviço BAPZX R$20/h com contato WhatsApp (19) 99181-3598 (/servico); entrega padronizada em até 10 min após a confirmação do pagamento; resumo do pedido sai junto com o QR. Planilha de clientes 100% automática FUNCIONANDO (bot → Apps Script → Google Sheets, confirmação ao vivo; planilha agora RESTRITA). Painel protegido; env vars completas no Render (DASHBOARD_KEY/SHEET_WEBAPP_URL/SHEET_TOKEN). Fase C e validação com 1º cliente real VETADAS até tudo ajustado.
- Próximo passo: conferir com o dono (a) o número do WhatsApp (19) 99181-3598 e (b) se o serviço é R$20 (reais) por hora; depois QA geral do código/site; opções de site gratuito pro portfólio entregues na sessão. Pendências de tel: atualizar manual para v1.9.0/branding.
- Arquivos tocados: bot.py, persona.txt, MEMORIA.md, planilha-clientes/, .env local, manual.txt, ROADMAP.
- Bloqueios: nenhum.
- Dias restantes: 10 de 15.

Atendente IA de venda de Tibia Coins via Telegram (Flask webhook + Google Gemini).
Versão atual do bot: 1.9.0.

## Leitura obrigatória antes de alterar (memórias do projeto)

- `MEMORIA.md` (este arquivo) — decisões e histórico.
- `MEMORIA_COMPRA.md` — regra de cálculo de preço (1.000 TC = R$ 90).
- `MEMORIA_SEGURANCA.md` — regra de segurança absoluta: confidencialidade
  de código, dados e métricas; leitura obrigatória em toda sessão.

## Estrutura

- `bot.py` — webhook Flask: `/` (landing page pública de vendas), `/health` (ok + versão), `/webhook` (mensagens), `/webhook/mp` (notificações do Mercado Pago), `/pedidos` e `/dashboard` (protegidos por chave), comandos `/id`. Landing gerada por `landing_page()` (preços, como comprar, botão + QR para t.me/bapzx_bot).
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
- `MP_ACCESS_TOKEN` — Access Token de produção do Mercado Pago (começa com `APP_USR-`). Sem ele o bot volta ao modo manual (texto com PIX_KEY + /pago).
- `RENDER_URL` — URL do deploy (padrão `bapzx-bot-tibia.onrender.com`), usada como notification_url das cobranças: `<RENDER_URL>/webhook/mp`.
- `PIX_KEY` — chave Pix estática, usada só como fallback quando o Mercado Pago não está configurado.
- `DASHBOARD_KEY` — chave de acesso do `/dashboard` e `/pedidos` (query `?key=` ou header `X-Dashboard-Key`). Sem ela as rotas ficam bloqueadas (fail-closed). Valor gerado fica só no `.env` local e no Render — nunca em código/docs/repo (ver MEMORIA_SEGURANCA.md).
- `SHEET_WEBAPP_URL` e `SHEET_TOKEN` — alimentação automática da planilha de clientes (Google Sheets via Apps Script Web App). URL do deploy + token compartilhado bot↔script. Sem eles o bot pula o envio sem quebrar.

## Decisões

- Pedido detectado por palavras-chave em conversa privada; salvo de forma estruturada (TC, preço da tabela, pagamento, mundo, char) e dono notificado (mensagem "🛒 NOVO PEDIDO").
- Preços fixos na persona (100 a 2500 TC). Pagamento: Pix. Entrega: Trade in-game (pedir mundo e char).
- Fallback de modelo IA: gemini-3.6-flash → gemini-3-flash-preview → gemini-3.5-flash.
- Persistência: `OrderStore` usa Supabase (REST) como fonte de verdade quando `SUPABASE_URL`/`SUPABASE_KEY` estão setadas; falha/ausência cai para `pedidos.json` (local). Contagem (`/pedidos`) vem do Supabase via `Prefer: count=exact`, com fallback no arquivo.
- Tarifa do Mercado Pago no Pix: ABSORVIDA pela loja por enquanto (decisão de 11/09) — o cliente paga exatamente o valor da tabela, sem acréscimo. Reavaliar quando a 1ª venda real aparecer no /dashboard (ver Pendências).
- Segurança do painel: `/dashboard` e `/pedidos` exigem `DASHBOARD_KEY`; sem chave configurada as rotas negam acesso. Landing `/` é pública (só conteúdo comercial, sem dados).
- Defesa contra spam: rate limit por chat (máx. ~5 mensagens em 12s) com resposta única; protege custo da IA e fluxos.
- Extração do char usa stop-words (mundo, pagamento, pix, etc.) para não engolir palavras seguintes.
- Pedido de e-mail do Pix expira em 30 min se o cliente não responder (limpeza do estado em memória).
- Fase C (divulgação) VETADA pelo dono até tudo ficar ajustado. Controle de clientes será via Google Sheets online (modelo em planilha-clientes/: TEMPLATE_CLIENTES_v2.csv recomendado + COMO_USAR_GOOGLE_SHEETS.txt; dono já importou/criou a planilha, ID 1CAjZTzAPkkhDXfIJrjUDg6aUVYxk6wW5HjuZpN0wRfU, agora RESTRITA c/ automação por token). Plano B documentado em planilha-clientes/PLANO_B.txt (operação manual não para: fallback Supabase→pedidos.json já no código; MP falha→Pix manual via /pago; Render/Gemini/Telegram falha→atendimento manual + planilha como registro).
- REBRAND (11/09): a empresa é BAPZX (main); este bot é a área de vendas online da BAPZX; a loja de Tibia Coins vira RUBINI COINS (internamente opção "BAPZX RUBINOT"). Novo Serviço BAPZX: R$20 por hora, solicitação pelo WhatsApp (19) 99181-3598 (comando /servico). Entrega padronizada: trade in-game em até 10 minutos após a confirmação do pagamento. Confirmar com o dono o número do WhatsApp e se o serviço é R$20/h (R$ ou dólar).

## Testes feitos (09/09/2026)

- Local: pedido de teste `quero comprar 500 tc` registrado (2 pedidos) e notificação enviada.
- Render: health `200 - bot ok`; webhook respondeu `200` a `quero comprar 250 tc`; `/pedidos` == 1 (filesystem do deploy é separado do local).
- Webhook aponta para `https://bapzx-bot-tibia.onrender.com/webhook`.

## Testes feitos (10/09/2026)

- v1.2.0 (estrutura + persistência): `quero comprar 1000 tc, pagamento pix, mundo pacera, char Nap Lord` → extrato `tc=1000, preco=R$90, pag=Pix, mundo=pacera, char=nap lord`; `quero comprar 250 tc` → `tc=250, preco=R$22,50`. Health exibe `bot ok v1.2.0`. Contagem `/pedidos` == 3.
- v1.2.1 (fix de configuração): `SUPABASE_URL`/`SUPABASE_KEY` passados via `load_env_key` (antes só `os.environ`, então o Supabase nunca ativava no .env local). Pedido `quero comprar 500 tc, mundo pacera, char Nap Lord` gravado no Supabase com `tc=500, preco=R$45, mundo=pacera, char=nap lord`; `/pedidos` passou a contar do Supabase (2). Feito também o teste POST/GET/DELETE direto na REST API.
- v1.2.1 no Render: após configurar as 5 Environment Variables no serviço, pedido via webhook do Render (`quero comprar 250 tc, mundo ferobra`) gravado no Supabase (id=3, tc=250, mundo=ferobra) — persistência em nuvem confirmada no deploy.
- **Teste real end-to-end (10/09)**: mensagem enviada de dentro do Telegram (`quero comprar 500 tc, mundo pacera, char Teste Real`) → webhook → gravado no Supabase id=5 com `tc=500, preco=R$45, mundo=pacera, char=teste real`, chat 1695600926 (Lucas). `/id` respondeu pelo webhook. Durante o teste, `GOOGLE_API_KEY` estava incorreta no Render (erro 400 API_KEY_INVALID); corrigida para a chave correta do `gemini-cli/.env` (formato `AQ.` — validada, 50 modelos acessíveis). Parser validado com 5 mensagens de amostra.
- v1.3.0 (comandos + IA reforçada): testados local `/start`, `/preco`, `/quemsomos`, `/vendedor`, `/help` (respostas enviadas ao chat do dono em teste) e pedido `quero comprar 1000 tc, pix, mundo antica, char Rei Leao` → Supabase id=6 (tc=1000, preco=R$90, pag=Pix, mundo=antica, char=rei leao). IA reforçada: tabela oficial injetada no prompt e respostas limpas sem asteriscos.
- v1.3.1 (texto do pedido): ajuda e regra da IA agora deixam claro os 4 dados obrigatórios para comprar — nome do char, quantidade de TC, mundo e forma de pagamento (Pix). Exemplo no /start. Testado local (200 ok).
- v1.4.0 (dashboard de vendas): rota GET /dashboard com faturado total, nº de pedidos, nº de clientes, pedidos dos últimos 14 dias (gráfico de barras) e tabela dos últimos 10 pedidos — dados reais do Supabase via novo método `OrderStore.list()` (paginação Range + fallback para arquivo). /pedidos agora aponta para /dashboard. Testado local: 5 pedidos, R$247,50, 1 cliente.
- v1.4.1 (memoria de compra): criado MEMORIA_COMPRA.md com a regra de cálculo de preço (proporção 1.000 TC = R$ 90 — valor = quantidade x 90 / 1.000, passo a passo). Regra injetada no prompt da IA (calcula quantidades fora da tabela mostrando o cálculo) e aplicada no registro: novo `calc_price()` em bot.py (tabela fixa para 100/250/500/1.000/2.500; fórmula para o resto). Testado local: pedido de 600 TC gravou no Supabase id=7 com preco R$54,00; calc_price(800)=R$72,00, calc_price(1500)=R$135,00.
- Migração do histórico (10/09): script `scripts/migrar_pedidos.py` insere no Supabase as linhas do `pedidos.json` ainda ausentes (dedupe por mensagem+chat_id) e esvazia o arquivo local ao concluir. Resultado: 5 inseridos (banco com 11 pedidos), pedidos do dia 09/09 preservados com data/chat/usuario originais.
- v1.5.0 (fluxo de pagamento Pix): colunas `status`, `pix_confirmado_em` e `entregue_em` adicionadas ao Supabase via `scripts/migracao_status.sql`; pedido nasce com `status=pendente` e cliente recebe texto com valor + chave Pix (configurável via var `PIX_KEY` no .env/Render; sem chave o texto pede para usar /vendedor). Comandos `/pago <id>` e `/entregue <id>` no chat do dono (validação por chat_id), com aviso automático ao cliente em cada etapa; não-dono recebendo `/pago` é bloqueado. Dashboard: faturado contabiliza só pedidos com `status=pago` e agora tem card "Pagos" + coluna "Status" estilizada. Testado local: pedido id=13 (1500 tc, R$135, nisseus, antica) -> /pago -> status=pago (ts preenchido) -> /entregue -> status=entregue; dashboard exibe status e totais; não-dono bloqueado.
## Testes feitos (11/09/2026)

- v1.6.0 (Pix automático via Mercado Pago, 11/09): token de produção do Mercado Pago validado (`GET /users/me`). Fluxo novo: pedido detectado -> bot pede o e-mail do cliente -> `create_pix_charge` cria cobrança Pix real (`POST /v1/payments`, payment_method_id=pix, external_reference=id do pedido, header `X-Idempotency-Key` obrigatório, notification_url `RENDER_URL/webhook/mp`) -> `send_qr` envia QR (imagem via sendPhoto + código copia e cola, validade 30 min) -> quando o pagamento confirma, o Mercado Pago chama `/webhook/mp`, que consulta o pagamento e, se `approved`, marca o pedido como `pago` sozinho e avisa cliente e dono. Sem MP configurado, cai no fluxo manual (PIX_KEY + /pago). `OrderStore.save` voltou a retornar a linha salva com id (header `Prefer: return=representation` na REST do Supabase; fallback arquivo gera id próprio). Testado local: fluxo completo pedido->e-mail->QR no Telegram; webhook mock validou pedido -> pago com pix_confirmado_em; cobrança real de R$1,00 criada e cancelada (validação da API). Orfãos de teste cancelados e linhas de teste removidas. OBS.: nessa sessão a tabela pedidos foi limpa — as linhas existentes eram todas de teste (ids 1-13, nenhuma venda real).
- v1.7.0 (revisão, segurança e landing, 11/09): `/` virou landing pública (preços, como comprar, botão + QR para t.me/bapzx_bot), novo `/health` para monitoramento, `/dashboard` e `/pedidos` passaram a exigir `DASHBOARD_KEY` (401 sem chave; 200 com `?key=`), rate limit anti-spam da IA (5 msgs/12s), extração do char corrigida com stop-words (`char Rei Leao mundo antica` -> "rei leao"), expiração de 30 min no pedido de e-mail do Pix, prompt da IA orientado a não pedir e-mail (o sistema pede). Suite de testes offline passou: landing, health, trava de dashboard/pedidos, fluxo de pedido (fallback e MP), e-mail (válido/inválido/expirado), QR gerado, rate limit e webhook/mp idempotente.
- v1.8.0 (automação da planilha de clientes, 11/09): `push_to_sheet` envia cada pedido (e cada atualização de status via `apply_status` — pago/entregue) como POST para o Apps Script Web App (`SHEET_WEBAPP_URL`), autenticado por `SHEET_TOKEN`; payload mapeado para as 14 colunas da planilha (data, cliente, contato, origem, mundo, char, quantidade_tc, preco, tipo_pagamento, data_pagamento, data_entrega, status, id_pedido, observacoes); status "pendente" vira "pagamento_pendente" na planilha. Testes: unit de payload/mapeamento/what-if (sem config não quebra) + suíte v1.7.0 completa verde. CONFIRMADO AO VIVO: create criou linha e update por id_pedido atualizou a MESMA linha (pago/entregue) sem duplicar; script ganhou `ensureHeader` (auto-repara o cabeçalho p/ 14 colunas). Web App implantado; SHEET_WEBAPP_URL/SHEET_TOKEN/DASHBOARD_KEY adicionados no Render.
- v1.9.0 (rebrand BAPZX/RUBINI COINS + serviço + entrega 10 min, 11/09): troca do nome da loja para "RUBINI COINS" (empresa mãe BAPZX), comando /servico (R$20/h, WhatsApp (19) 99181-3598), HELP/ABOUT/persona/landing atualizados, entrega em até 10 min após pagamento em todos os textos (tabela, pedido, QR), resumo do pedido junto com o QR gerado (tc, valor, mundo, char, validade, entrega). Testado: py_compile + suítes (v1.7.0, planilha) verdes.

## Configuração Supabase (10/09/2026)

- Projeto: `https://wtgzsurppwwrzhctnnfa.supabase.co` — tabela `public.pedidos` criada via SQL Editor.
- Usar a service role key legada (JWT) — a `sb_secret_*` nova retornou 401 e a `sb_publishable_*` retornou 404. A JWT é a única funcionando com o REST.
- `.env` local configurado. Render configurado (5 variáveis direto no serviço: TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_CHAT_ID, GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY) e validado com pedido real gravado no banco.

## Segurança

- Token do bot rotacionado em 10/09 (via /revoke no BotFather): antigo revogado (401) e novo token aplicado no `.env` local, no Render (TELEGRAM_BOT_TOKEN) e no webhook (setWebhook → bapzx-bot-tibia.onrender.com/webhook). Teste end-to-end: /preco pelo webhook do Render respondeu 200 com a resposta entregue no chat do dono.
- Token do Mercado Pago (MP_ACCESS_TOKEN): fica somente no `.env` local (gitignored) e nas env vars do Render; nunca em código/documentos/backup. Validação do dono usada nas chamadas: a conta pertence a lucascristianini@outlook.com.br.
- Nunca colocar senhas, tokens ou chaves de API no código, documentação ou backup (ver MEMORIA_SEGURANCA.md).

## Pendências

- Tratar pedido assíncrono: cliente informa mundo/char depois do valor (pedido parcial).
- Remover placeholders pendentes da persona, se houver.
- Confirmar visualmente a resposta da IA em atendimento real (no teste, o pedido gravou correto; a resposta da IA precisa ser conferida no chat após a correção da chave).
- Reavaliar a tarifa do Mercado Pago no Pix: decisão atual é absorver (ver Decisões, 11/09); revisar na primeira venda real.
- Validar o fluxo Pix automático em atendimento real de ponta a ponta (cliente real paga, webhook confirma, /entregue encerra).