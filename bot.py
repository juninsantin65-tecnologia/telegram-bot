import os
import uuid
import base64
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
GRUPO_LINK = os.getenv("GRUPO_LINK")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

VALOR = "4.99"

usuarios = {}
pedidos = {}


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
        enviar_mensagem(
            chat_id,
            "❌ Primeiro envie seu e-mail."
        )
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
            "first_name": "Cliente"
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

    print("STATUS MERCADO PAGO:", resposta.status_code, flush=True)
    print("RESPOSTA:", resultado, flush=True)

    if resposta.status_code >= 400:
        enviar_mensagem(
            chat_id,
            f"❌ Erro ao gerar o Pix.\nCódigo: {resposta.status_code}"
        )
        return

    order_id = resultado.get("id")

    try:
        pagamento = resultado["transactions"]["payments"][0]
        metodo = pagamento["payment_method"]

        qr_base64 = metodo.get("qr_code_base64")
        copia_cola = metodo.get("qr_code")

    except (KeyError, IndexError, TypeError):
        enviar_mensagem(
            chat_id,
            "❌ Não consegui encontrar os dados do Pix."
        )
        return

    pedidos[order_id] = chat_id

    if qr_base64:
        try:
            imagem = base64.b64decode(qr_base64)

            requests.post(
                f"{TELEGRAM_API}/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": "💳 Pix de R$ 4,99\n\nApós o pagamento, aguarde a confirmação automática."
                },
                files={
                    "photo": (
                        "pix.png",
                        imagem,
                        "image/png"
                    )
                }
            )

        except Exception as erro:
            print("ERRO QR CODE:", erro, flush=True)

    if copia_cola:
        enviar_mensagem(
            chat_id,
            f"📋 Pix Copia e Cola:\n\n{copia_cola}\n\n"
            "Após pagar, aguarde a confirmação automática."
        )


def verificar_pedido(order_id):
    resposta = requests.get(
        f"https://api.mercadopago.com/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}"
        }
    )

    print(
        "VERIFICAÇÃO DO PEDIDO:",
        resposta.status_code,
        resposta.text,
        flush=True
    )

    if resposta.status_code != 200:
        return None

    return resposta.json()


def liberar_acesso(order_id):
    dados = verificar_pedido(order_id)

    if not dados:
        return

    status = dados.get("status")

    print(
        "STATUS DO PEDIDO:",
        order_id,
        status,
        flush=True
    )

    if status != "processed":
        return

    referencia = dados.get("external_reference")

    if not referencia:
        return

    chat_id = int(referencia)

    if not GRUPO_LINK:
        enviar_mensagem(
            chat_id,
            "✅ Pagamento aprovado!\n\n"
            "⚠️ O link do grupo ainda não foi configurado."
        )
        return

    enviar_mensagem(
        chat_id,
        "✅ PAGAMENTO APROVADO!\n\n"
        "🎉 Seu acesso foi liberado.\n\n"
        f"👉 {GRUPO_LINK}"
    )


@app.route("/", methods=["GET"])
def inicio():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>TP Intermediações de Pagamentos</title>
    </head>
    <body>
        <h1>TP Intermediações de Pagamentos</h1>
        <p>Intermediação de pagamentos para produtos digitais.</p>
        <p>Atendimento e vendas realizados através do Telegram.</p>
    </body>
    </html>
    """, 200


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    dados = request.get_json(silent=True) or {}

    print(
        "TELEGRAM RECEBIDO:",
        dados,
        flush=True
    )

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
            "Agora envie:\n/pix"
        )

    elif texto == "/pix":

        criar_pix(chat_id)

    return "OK", 200


@app.route("/mercadopago/webhook", methods=["POST"])
def mercadopago_webhook():

    dados = request.get_json(silent=True) or {}

    print(
        "MERCADO PAGO WEBHOOK:",
        dados,
        flush=True
    )

    order_id = None

    if dados.get("data"):
        order_id = dados["data"].get("id")

    if not order_id:
        order_id = request.args.get("data.id")

    if order_id:
        liberar_acesso(order_id)

    return "OK", 200


if __name__ == "__main__":

    porta = int(
        os.getenv("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=porta
    )
