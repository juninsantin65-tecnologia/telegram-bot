import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
GRUPO_PRODUTOS_LINK = "https://t.me/+0xV30mWWl2A5OThh"

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        }
    )


@app.route("/", methods=["GET"])
def home():
    return "Bot online", 200


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json(silent=True) or {}

    message = data.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "")

    if chat.get("id"):
        chat_id = chat["id"]

        if text == "/start":
            send_message(
                chat_id,
                "Olá! 👋\n\nBem-vindo!\n\nEm breve você poderá fazer sua compra por Pix aqui mesmo no Telegram."
            )

    return "OK", 200


@app.route("/mercadopago/webhook", methods=["POST"])
def mercadopago_webhook():
    data = request.get_json(silent=True) or {}

    print("Mercado Pago webhook:", data)

    return "OK", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
