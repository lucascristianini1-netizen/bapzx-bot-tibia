import json
import os
import re
import sys
from datetime import datetime

import requests
from flask import Flask, request

from storage import OrderStore

VERSION = "1.4.0"

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
    "Olá! Eu sou o atendente da BAPZX Tibia Coins. Veja o que posso fazer:\n\n"
    "/preco - tabela de preços\n"
    "/vendedor - falar com um atendente humano\n"
    "/quemsomos - conhecer a loja\n"
    "/ajuda - mostrar esta lista de novo\n\n"
    "PARA COMPRAR, me informe estes 4 dados:\n"
    "1. Nome do char\n"
    "2. Quantidade de Tibia Coins\n"
    "3. Mundo\n"
    "4. Forma de pagamento (Pix)\n\n"
    "Exemplo: quero comprar 500 tc, mundo pacera, char Teste, pagamento pix"
)

ABOUT_TEXT = (
    "BAPZX Tibia Coins vende Tibia Coins de forma rápida e segura.\n"
    "Pagamento via Pix e entrega por Trade in-game na sua world/char.\n"
    "Use /preco para ver a tabela, /vendedor para falar com um atendente "
    "humano e /ajuda para rever as opções."
)


def price_table_text():
    lines = ["TABELA DE PREÇOS - BAPZX Tibia Coins"]
    for value, price in PRICES.items():
        lines.append(f"  {value} TC - {price}")
    lines.append("\nPagamento: Pix. Entrega: Trade in-game.")
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
        "  nome do char, quantidade de Tibia Coins, mundo e forma de pagamento (Pix).\n\n"
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
        "preco": PRICES.get(tc) if tc else None,
        "pagamento": pagamento or ("Pix" if "pix" in lower else None),
        "mundo": mundo.group(1) if mundo else None,
        "char": char.group(1).strip() if char else None,
    }


def build_order(chat_id, username, text):
    entry = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "chat_id": chat_id,
        "usuario": username,
        "mensagem": text,
    }
    entry.update(extract_order_details(text))
    return entry


def save_order(entry):
    return STORE.save(entry)


def looks_like_order(text):
    lower = text.lower()
    markers = ["quero", "vou querer", "queria comprar", "confirm", "pode fechar",
               "comprar", "fechado", "vou levar", "vou pegar", "pedido", "to comprando"]
    return any(marker in lower for marker in markers)


app = Flask(__name__)
STORE = OrderStore(
    pedidos_path(),
    url=load_env_key("SUPABASE_URL"),
    key=load_env_key("SUPABASE_KEY"),
)


@app.route("/", methods=["GET"])
def health():
    return f"bot ok v{VERSION}", 200


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

    if chat_type == "private" and looks_like_order(text):
        entry = build_order(chat_id, username, text)
        save_order(entry)
        notify_owner(entry)

    reply = ask_ai(text)
    send_message(chat_id, reply)
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
    for order in orders:
        faturado += parse_brl(order.get("preco"))
        dia = (order.get("data") or "")[:10]
        if dia:
            por_dia[dia] = por_dia.get(dia, 0) + 1
        chat = order.get("chat_id")
        if chat is not None:
            clientes.add(chat)
    return faturado, por_dia, clientes


@app.route("/dashboard", methods=["GET"])
def dashboard():
    orders = STORE.list()
    faturado, por_dia, clientes = dashboard_metrics(orders)

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
        rows += (
            "<tr>"
            f"<td>{order.get('data') or '-'}</td>"
            f"<td>{order.get('char') or '-'}</td>"
            f"<td>{order.get('tc') or '-'} TC</td>"
            f"<td>{order.get('preco') or '-'}</td>"
            f"<td>{order.get('mundo') or '-'}</td>"
            f"<td>{order.get('pagamento') or '-'}</td>"
            f"<td>{order.get('usuario') or '-'}</td>"
            "</tr>"
        )
    if not rows:
        rows = "<tr><td colspan='7' class='empty'>Nenhum pedido ainda</td></tr>"
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
</style>
</head>
<body>
<header><h1>BAPZX Tibia Coins - Dashboard de vendas</h1></header>
<main>
<div class="cards">
<div class="card"><div class="num">{total_brl}</div><div class="lbl">Faturado total</div></div>
<div class="card"><div class="num">{len(orders)}</div><div class="lbl">Pedidos</div></div>
<div class="card"><div class="num">{len(clientes)}</div><div class="lbl">Clientes</div></div>
</div>
<section><h2>Pedidos nos últimos 14 dias</h2>{''.join(bars)}</section>
<section><h2>Últimos pedidos</h2>
<table><tr><th>Quando</th><th>Char</th><th>Qtd</th><th>Valor</th><th>Mundo</th><th>Pagamento</th><th>Cliente</th></tr>{rows}</table>
</section>
</main>
</body>
</html>"""
    return page, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/pedidos", methods=["GET"])
def pedidos():
    return f"{STORE.count()} pedido(s) registrado(s) | dashboard: /dashboard", 200


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
    lines.append(f"Quando: {entry['data']}")
    lines.append(f"Mensagem: {entry['mensagem']}")
    send_message(owner_chat, "\n".join(lines))


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