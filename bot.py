import json
import os
import re
import sys
from datetime import datetime

import requests
from flask import Flask, request

from storage import OrderStore

VERSION = "1.2.1"

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


def load_persona():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persona.txt")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Você é um assistente de atendimento em português do Brasil."


def ask_ai(text):
    from google import genai

    key = load_env_key("GOOGLE_API_KEY")
    if not key:
        return "IA nao configurada (sem GOOGLE_API_KEY)."
    client = genai.Client(api_key=key)
    prompt = f"{load_persona()}\n\nCliente: {text}"
    last = None
    for attempt in range(2):
        for model in MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text or "(sem resposta)"
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

    if chat_type == "private" and looks_like_order(text):
        entry = build_order(chat_id, username, text)
        save_order(entry)
        notify_owner(entry)

    reply = ask_ai(text)
    send_message(chat_id, reply)
    return "ok", 200


@app.route("/pedidos", methods=["GET"])
def pedidos():
    return f"{STORE.count()} pedido(s) registrado(s)", 200


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


def set_webhook(url):
    response = requests.post(f"{BASE}/setWebhook", json={"url": url}, timeout=15)
    print("setWebhook:", response.json())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if len(sys.argv) > 1 and sys.argv[1] == "--set-webhook":
        set_webhook(sys.argv[2] if len(sys.argv) > 2 else f"http://localhost:{port}/webhook")
    else:
        app.run(host="0.0.0.0", port=port)