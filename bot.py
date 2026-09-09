import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

PAGAMENTO_LINK = "https://mpago.la/2akiy3E"


def enviar_mensagem(chat_id, texto):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": texto
        }
    )


@app.route("/", methods=["GET"])
def inicio():
    return "Bot online", 200


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    dados = request.get_json(silent=True) or {}

    mensagem = dados.get("message", {})
    chat = mensagem.get("chat", {})
    texto = mensagem.get("text", "")

    if chat.get("id") and texto == "/start":
        chat_id = chat["id"]

        enviar_mensagem(
            chat_id,
            "Olá! 👋\n\n"
            "Bem-vindo!\n\n"
            "💳 Para comprar sua capinha, acesse:\n"
            f"{PAGAMENTO_LINK}"
        )

    return "OK", 200


@app.route("/mercadopago/webhook", methods=["POST"])
def mercadopago_webhook():
    dados = request.get_json(silent=True) or {}
    print("Mercado Pago:", dados)

    return "OK", 200


if __name__ == "__main__":
    porta = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=porta)
