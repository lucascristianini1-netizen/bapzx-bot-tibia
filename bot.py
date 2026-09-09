import os
import sys

import requests
from flask import Flask, request

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


app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    return "bot ok", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}
    message = update.get("message") or {}
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")
    if text and chat_id:
        print(f"[{chat_id}] {text}")
        reply = ask_ai(text)
        send_message(chat_id, reply)
    return "ok", 200


def set_webhook(url):
    response = requests.post(f"{BASE}/setWebhook", json={"url": url}, timeout=15)
    print("setWebhook:", response.json())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if len(sys.argv) > 1 and sys.argv[1] == "--set-webhook":
        set_webhook(sys.argv[2] if len(sys.argv) > 2 else f"http://localhost:{port}/webhook")
    else:
        app.run(host="0.0.0.0", port=port)