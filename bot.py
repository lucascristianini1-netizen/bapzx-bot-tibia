import base64
import html
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime

import requests
from flask import Flask, request

from storage import OrderStore

VERSION = "1.9.1"

BRAND = "BAPZX"
STORE = "RUBINI COINS"
SERVICE_NAME = "Service BAPZX"
SERVICE_PRICE = "US$20 por hora"
SERVICE_WHATSAPP_DISPLAY = "(19) 99181-3598"
SERVICE_WHATSAPP_LINK = "https://wa.me/5519991813598"
DELIVERY_NOTE = "Entrega: em até 10 minutos após a confirmação do pagamento, via trade no seu char."

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_env_key(var, paths=None):
    value = os.environ.get(var)
    if value:
        return value
    candidates = paths or [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gemini-cli", ".env"),
    ]
    for env_path in candidates:
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(var + "=") and not line.startswith("#"):
                        return line.split("=", 1)[1].strip()
    return None


TOKEN = load_env_key("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("Token nao encontrado. Crie o .env com TELEGRAM_BOT_TOKEN=seu_token")
    sys.exit(1)

BASE = f"https://api.telegram.org/bot{TOKEN}"
PIX_KEY = load_env_key("PIX_KEY")
MP_ACCESS_TOKEN = load_env_key("MP_ACCESS_TOKEN")
SHEET_WEBAPP_URL = load_env_key("SHEET_WEBAPP_URL")
SHEET_TOKEN = load_env_key("SHEET_TOKEN")
RENDER_URL = load_env_key("RENDER_URL") or "https://bapzx-bot-tibia.onrender.com"
AWAITING_EMAIL = {}
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
CHAT_HISTORY = {}
EMAIL_EXPIRY_SECONDS = 30 * 60
CHAR_STOP_WORDS = {
    "mundo", "world", "pagamento", "pix", "via", "em", "na", "no", "com",
    "para", "pra", "e", "vou", "quero", "trade", "email", "e-mail", "depois",
    "aguardando", "entrega", "sera", "vai",
}
SHEET_STATUS_MAP = {"pendente": "pagamento_pendente"}
MODELS = [
    "models/gemini-3.6-flash",
    "models/gemini-3-flash-preview",
    "models/gemini-3.5-flash",
]
PRICES = {
    100: "R$11,50",
    250: "R$22,50",
    500: "R$45",
    1000: "R$90",
    2500: "R$230",
}

HELP_TEXT = (
    "Olá! Bem-vindo à BAPZX. Esta é a área de vendas online. Veja o que posso fazer:\n\n"
    "🪙 RUBINI COINS (Tibia Coins)\n"
    "  /preco - tabela de preços\n"
    "  /quemsomos - conhecer a loja\n\n"
    "💼 Service BAPZX\n"
    "  /servico - Service BAPZX (US$20 por hora)\n\n"
    "/vendedor - falar com um atendente humano\n"
    "/ajuda - mostrar esta lista de novo\n\n"
    "PARA COMPRAR TIBIA COINS, me informe estes 4 dados:\n"
    "1. Nome do char\n"
    "2. Quantidade de Tibia Coins\n"
    "3. Mundo\n"
    "4. Forma de pagamento (Pix)\n\n"
    "Depois que eu confirmar o pedido, vou te pedir um e-mail para gerar "
    "o QR Code do Pix na hora.\n\n"
    "Exemplo: quero comprar 500 tc, mundo pacera, char Teste, pagamento pix"
)

ABOUT_TEXT = (
    "RUBINI COINS é a loja de Rubini Coins (Tibia Coins) da BAPZX: venda rápida e segura.\n"
    "Pagamento via Pix e entrega por Trade in-game na sua world/char.\n"
    "Entrega em até 10 minutos após a confirmação do pagamento.\n"
    "Use /preco para ver a tabela, /servico para os serviços BAPZX, "
    "/vendedor para falar com um atendente humano e /ajuda para rever as opções."
)

SERVICO_TEXT = (
    f"💼 Service BAPZX\n\n"
    f"Valor: {SERVICE_PRICE}\n"
    "O que inclui: service dedicado no Tibia (1 hora, termos usuais do jogo).\n\n"
    "Para solicitar, entre em contato pelo WhatsApp:\n"
    f"{SERVICE_WHATSAPP_DISPLAY}\n"
    f"{SERVICE_WHATSAPP_LINK}\n\n"
    "💳 Tibia Coins? Fale comigo aqui ou use /preco."
)


def price_table_text():
    lines = [f"TABELA DE PREÇOS - {STORE} (BAPZX)"]
    for value, price in PRICES.items():
        lines.append(f"  {value} TC - {price}")
    lines.append("\nPagamento: Pix. Entrega: Trade in-game em até 10 min após o pagamento confirmado.")
    return "\n".join(lines)


def load_persona():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persona.txt")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Você é um assistente de atendimento em português do Brasil."


def clean_ai_text(text):
    return (text or "").replace("*", "").replace("```", "").replace("`", "").strip()


def ask_ai(text):
    from google import genai

    key = load_env_key("GOOGLE_API_KEY")
    if not key:
        return "IA nao configurada (sem GOOGLE_API_KEY)."
    client = genai.Client(api_key=key)
    persona = load_persona()
    tabela = price_table_text()
    prompt = (
        f"{persona}\n\n"
        f"TABELA DE PREÇOS OFICIAL (use EXATAMENTE estes valores, nunca outros):\n"
        f"{tabela}\n\n"
        "REGRAS DE RESPOSTA:\n"
        "- Nunca use asteriscos (*), negrito ou marcação de texto. Responda em texto simples.\n"
        "- Quando o cliente quiser comprar, peça/confirme os 4 dados obrigatórios:\n"
        "  nome do char, quantidade de Tibia Coins, mundo e forma de pagamento (Pix).\n"
        "- O e-mail do cliente quem pede é o próprio sistema (depois de fechar o pedido);\n"
        "  não peça e-mail na conversa da IA.\n"
        "- Para calcular o valor de uma quantidade de TC fora da tabela acima, use a "
        "proporção de que 1.000 TC custam R$ 90: multiplique a quantidade por 90, divida "
        "por 1.000 e mostre o cálculo passo a passo, terminando com o valor em Reais.\n"
        "- Quantidades que estão na tabela (100, 250, 500, 1.000, 2.500 TC) usam o valor "
        "da tabela, sem recálculo.\n\n"
        f"Cliente: {text}"
    )
    last = None
    for attempt in range(2):
        for model in MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return clean_ai_text(response.text)
            except Exception as error:
                last = error
                code = getattr(getattr(error, "error", None), "code", None) or getattr(error, "code", None)
                if code in (503, 429):
                    import time
                    time.sleep(2 + attempt * 2)
                    continue
                return f"Erro: {error}"
    return f"IA ocupada, tente em instantes. ({last})"


def send_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    requests.post(f"{BASE}/sendMessage", json=payload, timeout=15)


def pedidos_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "pedidos.json")


def parse_amount(text):
    m = re.search(
        r"(\d{1,4}(?:[.,]\d{3})?)\s*(?:tc\b|t\b|tibias?\b|tibia\s+coins?\b|coins?\b|mil\b)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return int(m.group(1).replace(".", "").replace(",", ""))


def calc_price(tc):
    if not tc:
        return None
    if tc in PRICES:
        return PRICES[tc]
    value = tc * 90 / 1000
    return f"R${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def clean_char(raw):
    partes = []
    for word in raw.split():
        if word in CHAR_STOP_WORDS:
            break
        partes.append(word)
        if len(partes) == 4:
            break
    return " ".join(partes) or None


def extract_order_details(text, pagamento=None):
    lower = text.lower()
    tc = parse_amount(lower)
    mundo = re.search(r"(?:mundo|world)\s*[:=]?\s*([a-z0-9]+)", lower)
    char = re.search(
        r"(?:char|personagem|nick|nome do char)\s*[:=]?\s*([a-z0-9]+(?:\s+[a-z0-9]+){0,3})",
        lower,
    )
    return {
        "tc": tc,
        "preco": calc_price(tc) if tc else None,
        "pagamento": pagamento or ("Pix" if "pix" in lower else None),
        "mundo": mundo.group(1) if mundo else None,
        "char": clean_char(char.group(1)) if char else None,
    }


def build_order(chat_id, username, text):
    entry = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "chat_id": chat_id,
        "usuario": username,
        "mensagem": text,
        "status": "pendente",
    }
    entry.update(extract_order_details(text))
    return entry


def save_order(entry):
    return STORE.save(entry)


def payment_text(entry):
    linhas = ["PAGAMENTO DOS SEUS TIBIA COINS", ""]
    linhas.append("Resumo do seu pedido:")
    if entry.get("tc"):
        linhas.append(f"  Tibia Coins: {entry['tc']}")
    if entry.get("preco"):
        linhas.append(f"  Valor: {entry['preco']}")
    if entry.get("mundo"):
        linhas.append(f"  Mundo: {entry['mundo']}")
    if entry.get("char"):
        linhas.append(f"  Char: {entry['char']}")
    linhas.append("")
    if PIX_KEY:
        linhas.append(f"Para pagar via Pix, envie {entry.get('preco') or 'o valor'} para a chave Pix:")
        linhas.append(f"  {PIX_KEY}")
    else:
        linhas.append("Para pagar via Pix, peça a chave Pix ao atendente com /vendedor.")
    linhas.append("")
    linhas.append("Depois de pagar, me avise aqui: paguei")
    linhas.append("Quando o pagamento for confirmado, você recebe a confirmação aqui.")
    linhas.append(DELIVERY_NOTE)
    return "\n".join(linhas)


def notify_payment(entry):
    send_message(entry["chat_id"], payment_text(entry))


def push_to_sheet(order):
    if not SHEET_WEBAPP_URL or not SHEET_TOKEN:
        return
    status = (order.get("status") or "pendente")
    payload = {
        "token": SHEET_TOKEN,
        "order": {
            "data": (order.get("data") or "")[:10],
            "cliente": order.get("usuario") or "",
            "contato": str(order.get("chat_id") or ""),
            "origem": "Bot/Telegram",
            "mundo": order.get("mundo") or "",
            "char": order.get("char") or "",
            "quantidade_tc": order.get("tc") or "",
            "preco": order.get("preco") or "",
            "tipo_pagamento": "MP Pix" if MP_ACCESS_TOKEN else "Pix manual",
            "data_pagamento": (order.get("pix_confirmado_em") or "")[:10],
            "data_entrega": (order.get("entregue_em") or "")[:10],
            "status": SHEET_STATUS_MAP.get(status, status),
            "id_pedido": order.get("id") or "",
            "observacoes": "",
        },
    }
    try:
        response = requests.post(SHEET_WEBAPP_URL, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[planilha] status {response.status_code}: {response.text[:200]}")
    except Exception as error:
        print(f"[planilha] erro ao enviar pedido {order.get('id')}: {error}")


def create_pix_charge(order, email):
    amount = parse_brl(order.get("preco"))
    if amount <= 0:
        return False, "pedido sem valor definido."
    tc = order.get("tc")
    description = f"Tibia Coins {tc} TC - pedido {order['id']}" if tc else f"Tibia Coins - pedido {order['id']}"
    payload = {
        "transaction_amount": amount,
        "description": description,
        "payment_method_id": "pix",
        "payer": {
            "email": email,
            "first_name": order.get("usuario") or "Cliente",
        },
        "external_reference": str(order["id"]),
        "notification_url": f"{RENDER_URL}/webhook/mp",
    }
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }
    try:
        response = requests.post(
            "https://api.mercadopago.com/v1/payments", json=payload, headers=headers, timeout=20
        )
    except Exception as error:
        return False, str(error)
    if response.status_code not in (200, 201):
        return False, f"Mercado Pago {response.status_code}: {response.text[:200]}"
    data = response.json()
    if data.get("status") != "pending":
        return False, f"status inesperado: {data.get('status')}"
    return True, data


def send_qr(chat_id, data, order=None):
    order = order or {}
    transaction_data = ((data.get("point_of_interaction") or {}).get("transaction_data")) or {}
    img_b64 = transaction_data.get("qr_code_base64")
    if img_b64:
        try:
            png = base64.b64decode(img_b64)
            requests.post(
                f"{BASE}/sendPhoto",
                data={"chat_id": chat_id, "caption": "QR Code Pix - BAPZX Tibia Coins"},
                files={"photo": ("qr.png", png, "image/png")},
                timeout=15,
            )
        except Exception as error:
            print(f"[mp] erro ao enviar QR: {error}")
    qr_code = transaction_data.get("qr_code")
    linhas = [
        "PIX GERADO - Pedido confirmado",
        "",
        "Resumo do seu pedido:",
        f"  Tibia Coins: {order.get('tc') or '-'}",
        f"  Valor: {order.get('preco') or '-'}",
        f"  Mundo: {order.get('mundo') or '-'}",
        f"  Char: {order.get('char') or '-'}",
        "",
        "Escaneie o QR Code acima ou use o código abaixo (copia e cola):",
        "",
        qr_code or "(código indisponível)",
        "",
        "Validade: 30 minutos.",
        DELIVERY_NOTE,
        "O pagamento é confirmado automaticamente. Assim que bater, te aviso aqui!",
    ]
    send_message(chat_id, "\n".join(linhas))


def apply_status(order_id, status, ts_field=None):
    order = STORE.find(order_id)
    if not order:
        return "nao encontrado", None
    now_iso = datetime.now().isoformat(timespec="seconds")
    STORE.set_status(order_id, status, ts_field, now_iso)
    updated = STORE.find(order_id) or order
    push_to_sheet(updated)
    return "ok", order


def looks_like_order(text):
    lower = text.lower()
    markers = ["quero", "vou querer", "queria comprar", "confirm", "pode fechar",
               "comprar", "fechado", "vou levar", "vou pegar", "pedido", "to comprando"]
    return any(marker in lower for marker in markers)


def rate_limited(chat_id):
    now = time.time()
    stamps = [t for t in CHAT_HISTORY.get(chat_id, []) if now - t < 12]
    stamps.append(now)
    CHAT_HISTORY[chat_id] = stamps
    return len(stamps) > 5


def dashboard_allowed():
    expected = load_env_key("DASHBOARD_KEY")
    if not expected:
        return False
    given = request.args.get("key") or request.headers.get("X-Dashboard-Key")
    return given == expected


app = Flask(__name__)
STORE = OrderStore(
    pedidos_path(),
    url=load_env_key("SUPABASE_URL"),
    key=load_env_key("SUPABASE_KEY"),
)


@app.route("/", methods=["GET"])
def home():
    return landing_page(), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/health", methods=["GET"])
def health():
    return f"bot ok v{VERSION}", 200


def landing_page():
    price_rows = "".join(
        f"<tr><td>{value} TC</td><td class='price'>{price}</td></tr>"
        for value, price in PRICES.items()
    )
    page = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RUBINI COINS - BAPZX Tibia Coins rapidinho</title>
<style>
body { font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
.wrap { max-width: 720px; margin: 0 auto; padding: 24px; }
header { text-align: center; padding: 40px 0 16px; }
header h1 { margin: 0 0 8px; font-size: 28px; }
header p { margin: 0; color: #94a3b8; font-size: 15px; }
.badge { display: inline-block; background: #064e3b; color: #4ade80; border-radius: 999px;
         padding: 4px 14px; font-size: 13px; margin-top: 12px; }
.cta { text-align: center; margin: 24px 0; }
.btn { display: inline-block; background: #2563eb; color: #fff; text-decoration: none;
       padding: 14px 28px; border-radius: 10px; font-size: 17px; font-weight: bold; }
.btn:hover { background: #1d4ed8; }
.qr { margin-top: 14px; }
section { background: #1e293b; border-radius: 12px; padding: 20px; margin: 20px 0; }
section h2 { margin: 0 0 12px; font-size: 17px; }
table { width: 100%; border-collapse: collapse; font-size: 15px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #334155; }
th { color: #94a3b8; font-weight: normal; }
.price { color: #4ade80; font-weight: bold; }
ol { margin: 0; padding-left: 20px; line-height: 1.9; }
.steps li b { color: #60a5fa; }
.note { font-size: 13px; color: #94a3b8; margin-top: 10px; }
footer { text-align: center; color: #64748b; font-size: 12px; padding: 24px 0; }
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>BAPZX &middot; RUBINI COINS</h1>
<p>Área de vendas online da BAPZX. Compra de Tibia Coins rápida, segura e com pagamento via Pix.</p>
<span class="badge">Entrega por trade in-game em até 10 min</span>
</header>

<div class="cta">
<a class="btn" href="https://t.me/bapzx_bot">Comprar no Telegram</a>
<div class="qr"><img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https%3A%2F%2Ft.me%2Fbapzx_bot" alt="QR Code t.me/bapzx_bot" width="200" height="200"></div>
</div>

<section>
<h2>Tabela de preços</h2>
<table>
<tr><th>Quantidade</th><th>Preço</th></tr>
{price_rows}
</table>
<p class="note">Pagamento: Pix. Entrega: Trade in-game no seu char/mundo.</p>
</section>

<section>
<h2>Como comprar</h2>
<ol class="steps">
<li>Abra o bot no Telegram: mesmo os preços acima, direto no <b>t.me/bapzx_bot</b>.</li>
<li>Toque em <b>Iniciar</b> e informe seus 4 dados: char, quantidade de TC, mundo e pagamento (Pix).</li>
<li>Confirme com o bot e informe um <b>e-mail</b> para gerar o QR Code do Pix na hora.</li>
<li>Pague pelo QR e a confirmação chega sozinha; a <b>entrega é feita em até 10 minutos</b> via trade no seu char.</li>
</ol>
</section>

<section>
<h2>Service BAPZX (US$20 por hora)</h2>
<p>Service dedicado no Tibia, hora a hora (US$20/h).</p>
<p>Para solicitar, chame no WhatsApp:</p>
<p><a class="btn" href="https://wa.me/5519991813598">Chamar no WhatsApp</a></p>
<p class="note">(19) 99181-3598</p>
</section>

<section>
<h2>Por que comprar com a BAPZX?</h2>
<ul>
<li>Pagamento automatico via Pix (confirmacao em segundos).</li>
<li>Atendimento pelo Telegram, sem telas confusas.</li>
<li>Entrega por trade dentro do jogo.</li>
</ul>
</section>

<footer>BAPZX &middot; RUBINI COINS &middot; v""" + VERSION + """</footer>
</div>
</body>
</html>"""
    return page.replace("{price_rows}", price_rows)


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}
    message = update.get("message") or {}
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")
    chat_type = message.get("chat", {}).get("type")
    username = message.get("from", {}).get("first_name") or message.get("from", {}).get("username") or str(chat_id)
    if not text or not chat_id:
        return "ok", 200

    print(f"[{chat_id}] {text}")

    if text.strip() == "/id":
        send_message(chat_id, f"Seu chat_id é: {chat_id}")
        return "ok", 200

    command = text.strip().lower().split(" ", 1)[0]
    if command in ("/start", "/inicio", "/ajuda", "/help"):
        send_message(chat_id, HELP_TEXT)
        return "ok", 200

    if command == "/preco":
        send_message(chat_id, price_table_text())
        return "ok", 200

    if command == "/quemsomos":
        send_message(chat_id, ABOUT_TEXT)
        return "ok", 200

    if command == "/vendedor":
        reply_vendor(chat_id, username)
        return "ok", 200

    if command in ("/servico", "/servicos", "/service"):
        send_message(chat_id, SERVICO_TEXT)
        return "ok", 200

    if command in ("/pago", "/entregue"):
        owner_chat = load_env_key("TELEGRAM_OWNER_CHAT_ID")
        if str(chat_id) != str(owner_chat):
            send_message(chat_id, "Comando indisponível. Se precisar, use /vendedor.")
            return "ok", 200
        parts = text.strip().split()
        if len(parts) < 2:
            send_message(chat_id, "Use o comando com o número do pedido. Ex.: /pago 12 ou /entregue 12")
            return "ok", 200
        try:
            order_id = int(parts[1])
        except ValueError:
            send_message(chat_id, "O número do pedido deve ser numérico. Ex.: /pago 12")
            return "ok", 200
        if command == "/pago":
            result, order = apply_status(order_id, "pago", "pix_confirmado_em")
            if result == "nao encontrado":
                send_message(chat_id, f"Não achei o pedido {order_id}.")
                return "ok", 200
            send_message(chat_id, f"Pedido {order_id} marcado como PAGO. Cliente avisado para combinar o trade.")
            if order:
                send_message(
                    order["chat_id"],
                    "Seu pagamento foi CONFIRMADO. O atendente vai te chamar aqui para combinar o trade.\n"
                    "Preparado o char certo e on-line no horário combinado.",
                )
            return "ok", 200
        if command == "/entregue":
            result, order = apply_status(order_id, "entregue", "entregue_em")
            if result == "nao encontrado":
                send_message(chat_id, f"Não achei o pedido {order_id}.")
                return "ok", 200
            send_message(chat_id, f"Pedido {order_id} marcado como ENTREGUE. Cliente encerrado.")
            if order:
                send_message(
                    order["chat_id"],
                    "Tibia Coins entregues! Obrigado pela confiança e até a próxima. =)",
                )
            return "ok", 200

    if chat_type == "private" and chat_id in AWAITING_EMAIL:
        info = AWAITING_EMAIL.get(chat_id)
        expired = bool(info) and time.time() - info["ts"] > EMAIL_EXPIRY_SECONDS
        candidate = text.strip()
        if expired:
            AWAITING_EMAIL.pop(chat_id, None)
            send_message(
                chat_id,
                "O tempo para gerar o Pix expirou. Faça um novo pedido ou use /vendedor.",
            )
            return "ok", 200
        if not EMAIL_RE.match(candidate):
            send_message(
                chat_id,
                "Preciso do seu e-mail (ex.: nome@exemplo.com) para gerar o QR Code do Pix.",
            )
            return "ok", 200
        AWAITING_EMAIL.pop(chat_id, None)
        order = STORE.find(info["order_id"]) if info else None
        if not order:
            send_message(chat_id, "Não encontrei seu pedido. Fale com um atendente usando /vendedor.")
            return "ok", 200
        ok, result = create_pix_charge(order, candidate)
        if not ok:
            send_message(chat_id, "Não consegui gerar o Pix agora. " + result)
            send_message(chat_id, payment_text(order))
        else:
            send_qr(chat_id, result, order)
            notify_owner_pix(result, order)
        return "ok", 200

    if chat_type == "private" and looks_like_order(text):
        entry = build_order(chat_id, username, text)
        entry = save_order(entry)
        notify_owner(entry)
        push_to_sheet(entry)
        if MP_ACCESS_TOKEN and entry.get("id"):
            AWAITING_EMAIL[chat_id] = {"order_id": entry["id"], "ts": time.time()}
            send_message(
                chat_id,
                "Pedido registrado! Já calculei o valor. Para gerar seu QR Code do Pix, "
                "me responda com o seu e-mail (ex.: nome@exemplo.com).",
            )
            return "ok", 200
        notify_payment(entry)

    if rate_limited(chat_id):
        send_message(
            chat_id,
            "Calma aí! Estou processando suas mensagens em sequência. Escreva aqui em instantes.",
        )
        return "ok", 200

    reply = ask_ai(text)
    send_message(chat_id, reply)
    return "ok", 200


@app.route("/webhook/mp", methods=["POST"])
def webhook_mp():
    payload = request.get_json(silent=True) or {}
    data = payload.get("data") or {}
    payment_id = data.get("id")
    if not payment_id or not MP_ACCESS_TOKEN:
        return "ok", 200
    try:
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
            timeout=15,
        )
    except Exception as error:
        print(f"[mp] erro ao consultar pagamento: {error}")
        return "ok", 200
    if response.status_code != 200:
        return "ok", 200
    payment = response.json()
    if payment.get("status") != "approved":
        return "ok", 200
    reference = payment.get("external_reference") or ""
    if not reference.isdigit():
        return "ok", 200
    order_id = int(reference)
    order = STORE.find(order_id)
    if not order:
        print(f"[mp] pedido {order_id} nao encontrado")
        return "ok", 200
    if (order.get("status") or "pendente") == "pago":
        return "ok", 200
    apply_status(order_id, "pago", "pix_confirmado_em")
    owner_chat = load_env_key("TELEGRAM_OWNER_CHAT_ID")
    send_message(
        order["chat_id"],
        "Seu pagamento foi CONFIRMADO. O atendente vai te chamar aqui para combinar o trade.\n"
        "Deixa o char certo on-line no horário combinado.",
    )
    if owner_chat:
        linhas = ["💸 PAGAMENTO CONFIRMADO - PIX", f"Pedido: {order_id}"]
        if order.get("tc"):
            linhas.append(f"Tibia Coins: {order['tc']}")
        if order.get("preco"):
            linhas.append(f"Valor: {order['preco']}")
        if order.get("char"):
            linhas.append(f"Char: {order['char']}")
        if order.get("mundo"):
            linhas.append(f"Mundo: {order['mundo']}")
        linhas.append("Pagamento confirmado automaticamente via Mercado Pago.")
        linhas.append(f"Chame o cliente para o trade e use /entregue {order_id}")
        send_message(owner_chat, "\n".join(linhas))
    return "ok", 200


def parse_brl(value):
    if not value:
        return 0.0
    text = str(value).replace("R$", "").replace(" ", "")
    return float(text.replace(".", "").replace(",", "."))


def dashboard_metrics(orders):
    faturado = 0.0
    por_dia = {}
    clientes = set()
    pagos = 0
    for order in orders:
        if (order.get("status") or "pendente") == "pago":
            faturado += parse_brl(order.get("preco"))
            pagos += 1
        dia = (order.get("data") or "")[:10]
        if dia:
            por_dia[dia] = por_dia.get(dia, 0) + 1
        chat = order.get("chat_id")
        if chat is not None:
            clientes.add(chat)
    return faturado, por_dia, clientes, pagos


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if not dashboard_allowed():
        return "Acesso restrito.", 401
    orders = STORE.list()
    faturado, por_dia, clientes, pagos = dashboard_metrics(orders)

    dias = []
    from datetime import timedelta
    base = datetime.now().date()
    for offset in range(13, -1, -1):
        dia = base - timedelta(days=offset)
        dias.append((dia.isoformat(), por_dia.get(dia.isoformat(), 0)))
    max_dia = max((count for _, count in dias), default=0) or 1

    bars = []
    for dia, count in dias:
        width = int((count / max_dia) * 100)
        bars.append(
            f"<div class='day'><span class='label'>{dia}</span>"
            f"<div class='bar'><div class='fill' style='width:{width}%'></div></div>"
            f"<span class='value'>{count}</span></div>"
        )

    total_brl = f"R$ {faturado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    rows = ""
    for order in sorted(orders, key=lambda o: (o.get("data") or ""), reverse=True)[:10]:
        status = order.get("status") or "pendente"
        rows += (
            "<tr>"
            f"<td>{order.get('data') or '-'}</td>"
            f"<td>{order.get('char') or '-'}</td>"
            f"<td>{order.get('tc') or '-'} TC</td>"
            f"<td>{order.get('preco') or '-'}</td>"
            f"<td>{order.get('mundo') or '-'}</td>"
            f"<td>{order.get('pagamento') or '-'}</td>"
            f"<td>{order.get('usuario') or '-'}</td>"
            f"<td><span class='status {status}'>{status}</span></td>"
            "</tr>"
        )
    if not rows:
        rows = "<tr><td colspan='8' class='empty'>Nenhum pedido ainda</td></tr>"
    import html
    title = html.escape("BAPZX Tibia Coins - Dashboard")

    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }}
header {{ background: #1e293b; padding: 18px 24px; }}
header h1 {{ margin: 0; font-size: 20px; }}
main {{ padding: 24px; max-width: 900px; margin: 0 auto; }}
.cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
.card {{ background: #1e293b; border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 160px; }}
.card .num {{ font-size: 26px; font-weight: bold; color: #4ade80; }}
.card .lbl {{ font-size: 13px; color: #94a3b8; }}
section {{ background: #1e293b; border-radius: 10px; padding: 16px 20px; margin-bottom: 24px; }}
section h2 {{ margin-top: 0; font-size: 16px; }}
.day {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
.label {{ width: 110px; font-size: 12px; color: #94a3b8; }}
.bar {{ flex: 1; background: #334155; height: 14px; border-radius: 7px; overflow: hidden; }}
.fill {{ height: 100%; background: #4ade80; }}
.value {{ width: 28px; font-size: 12px; text-align: right; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ text-align: left; padding: 7px 8px; border-bottom: 1px solid #334155; }}
th {{ color: #94a3b8; font-weight: normal; }}
.empty {{ text-align: center; color: #64748b; padding: 18px; }}
.status {{ padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }}
.status.pendente {{ background: #78350f; color: #fbbf24; }}
.status.pago {{ background: #064e3b; color: #4ade80; }}
.status.entregue {{ background: #1e3a5f; color: #60a5fa; }}
.status.cancelado {{ background: #7f1d1d; color: #f87171; }}
</style>
</head>
<body>
<header><h1>BAPZX Tibia Coins - Dashboard de vendas</h1></header>
<main>
<div class="cards">
<div class="card"><div class="num">{total_brl}</div><div class="lbl">Faturado (pagos)</div></div>
<div class="card"><div class="num">{pagos}</div><div class="lbl">Pagos</div></div>
<div class="card"><div class="num">{len(orders)}</div><div class="lbl">Pedidos</div></div>
<div class="card"><div class="num">{len(clientes)}</div><div class="lbl">Clientes</div></div>
</div>
<section><h2>Pedidos nos últimos 14 dias</h2>{''.join(bars)}</section>
<section><h2>Últimos pedidos</h2>
<table><tr><th>Quando</th><th>Char</th><th>Qtd</th><th>Valor</th><th>Mundo</th><th>Pagamento</th><th>Cliente</th><th>Status</th></tr>{rows}</table>
</section>
</main>
</body>
</html>"""
    return page, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/pedidos", methods=["GET"])
def pedidos():
    if not dashboard_allowed():
        return "Acesso restrito.", 401
    return f"{STORE.count()} pedido(s) registrado(s) | dashboard: /dashboard?key=SUA_CHAVE", 200


def notify_owner(entry):
    owner_chat = load_env_key("TELEGRAM_OWNER_CHAT_ID")
    if not owner_chat:
        return
    lines = ["🛒 NOVO PEDIDO"]
    lines.append(f"Usuário: {entry['usuario']}")
    lines.append(f"ID: {entry['chat_id']}")
    if entry.get("tc"):
        lines.append(f"Tibia Coins: {entry['tc']}")
    if entry.get("preco"):
        lines.append(f"Preço: {entry['preco']}")
    if entry.get("pagamento"):
        lines.append(f"Pagamento: {entry['pagamento']}")
    if entry.get("mundo"):
        lines.append(f"Mundo: {entry['mundo']}")
    if entry.get("char"):
        lines.append(f"Char: {entry['char']}")
    lines.append(f"Status: {entry.get('status') or 'pendente'} (confirme com /pago + id)")
    lines.append(f"Quando: {entry['data']}")
    lines.append(f"Mensagem: {entry['mensagem']}")
    send_message(owner_chat, "\n".join(lines))


def notify_owner_pix(charge, entry):
    owner_chat = load_env_key("TELEGRAM_OWNER_CHAT_ID")
    if not owner_chat:
        return
    linhas = ["🧾 PIX GERADO PARA O PEDIDO"]
    linhas.append(f"Pedido: {entry.get('id')}")
    if entry.get("tc"):
        linhas.append(f"Tibia Coins: {entry['tc']}")
    if entry.get("preco"):
        linhas.append(f"Valor: {entry['preco']}")
    if entry.get("usuario"):
        linhas.append(f"Cliente: {entry['usuario']}")
    linhas.append(f"Mercado Pago id: {charge.get('id')}")
    linhas.append("Aguardando pagamento (confirmação automática).")
    send_message(owner_chat, "\n".join(linhas))


def reply_vendor(chat_id, username):
    owner_chat = load_env_key("TELEGRAM_OWNER_CHAT_ID")
    send_message(
        chat_id,
        "Você foi encaminhado a um atendente humano. Ele vai te chamar aqui "
        "em instantes. Fique on-line e me diga se a demora passar de alguns minutos.",
    )
    if owner_chat:
        send_message(
            owner_chat,
            "🙋 CLIENTE SOLICITOU ATENDENTE HUMANO\n"
            f"Usuário: {username}\n"
            f"ID: {chat_id}\n"
            "Responda este chat iniciando a conversa com o cliente.",
        )


def set_webhook(url):
    response = requests.post(f"{BASE}/setWebhook", json={"url": url}, timeout=15)
    print("setWebhook:", response.json())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if len(sys.argv) > 1 and sys.argv[1] == "--set-webhook":
        set_webhook(sys.argv[2] if len(sys.argv) > 2 else f"http://localhost:{port}/webhook")
    else:
        app.run(host="0.0.0.0", port=port)