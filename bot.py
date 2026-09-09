import os
import uuid
import base64
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

VALOR = "50.00"

usuarios = {}


def enviar_mensagem(chat_id, texto):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": texto
        }
    )


def criar_pix(chat_id):
    email = usuarios.get(chat_id)

    if not email:
        enviar_mensagem(chat_id, "Digite seu e-mail primeiro.")
        return

    dados = {
        "type": "online",
        "total_amount": VALOR,
        "external_reference": str(chat_id),
        "processing_mode": "automatic",
        "transactions": {
            "payments": [
                {
                    "amount": VALOR,
                    "payment_method": {
                        "id": "pix",
                        "type": "bank_transfer"
                    }
                }
            ]
        },
        "payer": {
            "email": email,
            "first_name": "APRO"
        }
    }

    resposta = requests.post(
        "https://api.mercadopago.com/v1/orders",
        headers={
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4())
        },
        json=dados
    )

    resultado = resposta.json()

    print("STATUS MERCADO PAGO:", resposta.status_code)
    print("RESPOSTA MERCADO PAGO:", resultado)

    if resposta.status_code >= 400:
        enviar_mensagem(
            chat_id,
            "Não consegui gerar o Pix agora. Tente novamente."
        )
        return

    pagamento = resultado["transactions"]["payments"][0]
    metodo = pagamento["payment_method"]

    qr_base64 = metodo.get("qr_code_base64")
    copia_cola = metodo.get("qr_code")

    if qr_base64:
        imagem = base64.b64decode(qr_base64)

        requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={
                "chat_id": chat_id,
                "caption": "💳 Pix de R$ 50,00\n\nPix de teste do Mercado Pago."
            },
            files={
                "photo": ("pix.png", imagem, "image/png")
            }
        )

    enviar_mensagem(
        chat_id,
        f"📋 Pix Copia e Cola:\n\n{copia_cola}"
    )


@app.route("/", methods=["GET"])
def inicio():
    return "Bot online", 200


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    dados = request.get_json(silent=True) or {}

    print("TELEGRAM RECEBIDO:", dados)

    mensagem = dados.get("message", {})
    chat = mensagem.get("chat", {})
    texto = mensagem.get("text", "").strip()

    chat_id = chat.get("id")

    if not chat_id:
        return "OK", 200

    if texto == "/start":
        enviar_mensagem(
            chat_id,
            "Olá! 👋\n\n"
            "Bem-vindo!\n\n"
            "Envie seu e-mail para continuar."
        )

    elif "@" in texto and " " not in texto:
        usuarios[chat_id] = texto

        enviar_mensagem(
            chat_id,
            "E-mail salvo ✅\n\n"
            "Agora envie:\n"
            "/pix"
        )

    elif texto == "/pix":
        criar_pix(chat_id)

    return "OK", 200


@app.route("/mercadopago/webhook", methods=["POST"])
def mercadopago_webhook():
    dados = request.get_json(silent=True) or {}

    print("MERCADO PAGO WEBHOOK:", dados)

    return "OK", 200


if __name__ == "__main__":
    porta = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=porta)
