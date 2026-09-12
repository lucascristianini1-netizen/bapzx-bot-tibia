# Memória de Pendências

Lista única de pendências, observações e bloqueios do projeto BAPZX / RUBINI COINS.
Atualizar sempre que algo mudar de estado.

## Bloqueios que dependem do dono (1 clique quando quiser)

- [ ] **Publish do app Google (OAuth)** — console.cloud.google.com/auth →
      Settings → Branding → Publishing status → **Publish app**.
      Hoje o app está em modo Teste: só o e-mail `lucascristianini1@gmail.com`
      consegue logar na área do cliente/admin. Publicar libera o login para
      **qualquer conta Google** (grátis; não precisa de verificação, pois só
      usa nome e e-mail do perfil).
- [ ] **Portfólio `itens.html`** — trocar os "Item Exemplo A/B/C..." e os
      preços `R$ --` pelos itens reais. O dono vai ajustar quando definir
      como vai vender itens.
- [ ] **Fase C (divulgação) e 1ª venda real** — VETADA pelo dono até tudo
      ajustado. Quando liberar:
      - ficha de divulgação (o que falar, onde postar);
      - post em comunidades/grupos de Tibia;
      - avaliar o WEB DIVULGADOR para divulgação programada.
      - validar venda real de ponta a ponta (cliente paga Pix, `/webhook/mp`
        confirma, `/entregue` encerra com aviso).

## A confirmar com o dono

- [ ] Número do WhatsApp **(19) 99181-3598** e valor do **Serviço BAPZX =
      R$20/h** (confirmar antes de divulgação real).
- [ ] **Limite por venda** a revisar (entrega em até 10 min definida;
      limite de TC por pedido não fechado).

## Qualidade / docs

- [ ] Conferir visualmente a **resposta da IA em atendimento real** (o pedido
      grava certo; falta confirmar a qualidade da resposta no chat, pois o
      Google Login mudou o fluxo).
- [ ] Revisar `manual.txt` (raiz de MEUS PROJETOS) com os recursos novos:
    Google Login, `/cliente`, `/admin`, `TELEGRAM_WEBHOOK_SECRET`, e agora o fluxo de
    confirmação do personagem via RubiNot (v1.12.0). Tema do ROS (roleta) também
    se aplicável.

- [ ] **Deploy da v1.12.0 no Render + teste ao vivo** — validar fluxo com
    confirmação de personagem via Telegram com personagem real; verificar se a API
    do RubiNot responde normalmente no Render (timeout 12s). Toggle
    `RUBINOT_VALIDATE=1` na env do Render (já é default; não precisa forçar).
      Google Login, área do cliente `/cliente`, área admin `/admin`, webhook
      protegido por `TELEGRAM_WEBHOOK_SECRET`.

## Concluído (manter como histórico; reabrir se voltar a aparecer)

- [x] Excluir client OAuth antigo (Desktop app `r2512...`) no Google — FEITO.
- [x] `TELEGRAM_WEBHOOK_SECRET` ativo no Render — FEITO e verificado
      (webhook responde 403 sem o header correto).
- [x] Usuário do GitHub renomeado para `bapzxdev` (URL do portfólio =
      https://bapzxdev.github.io/bapzx-portfolio/) — FEITO.
- [x] Auditoria de segurança v1.11.2 (XSS `/dashboard`, referer exato,
      sessão 7 dias + headers, secret do webhook) — FEITA.