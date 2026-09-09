import os
import uuid
import base64
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
GRUPO_LINK = os.getenv("GRUPO_LINK")
VIDEO_FILE_ID = os.getenv("VIDEO_FILE_ID")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

VALOR = "4.99"

usuarios = {}
acessos_liberados = set()


def enviar_mensagem(chat_id, texto, teclado=None):
    dados = {
        "chat_id": chat_id,
        "text": texto
    }

    if teclado:
        dados["reply_markup"] = teclado

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=dados,
        timeout=20
    )


def enviar_menu(chat_id):
    teclado = {
        "inline_keyboard": [[
            {
                "text": "🔥 GRUPO VITALÍCIO",
                "callback_data": "comprar"
            }
        ]]
    }

    texto = (
        "🛍️ BEM-VINDO À NOSSA LOJA!\n\n"
        "✨ Confira nossos produtos\n"
        "⚡ Acesso rápido\n"
        "💳 Pagamento via Pix\n"
        "✅ Liberação após confirmação\n\n"
        "👇 Clique no botão abaixo para continuar:"
    )

    if VIDEO_FILE_ID:
        requests.post(
            f"{TELEGRAM_API}/sendVideo",
            data={
                "chat_id": chat_id,
                "video": VIDEO_FILE_ID,
                "caption": texto,
                "reply_markup": str(teclado).replace("'", '"')
            },
            timeout=20
        )
    else:
        enviar_mensagem(chat_id, texto, teclado)


def responder_callback(callback_id):
    requests.post(
        f"{TELEGRAM_API}/answerCallbackQuery",
        json={"callback_query_id": callback_id},
        timeout=20
    )


def criar_pix(chat_id):
    email = usuarios.get(chat_id)

    if not email:
        enviar_mensagem(
            chat_id,
            "📧 Primeiro envie seu e-mail para continuar."
        )
        return

    dados = {
        "type": "online",
        "total_amount": VALOR,
        "external_reference": str(chat_id),
        "processing_mode": "automatic",
        "transactions": {
            "payments": [{
                "amount": VALOR,
                "payment_method": {
                    "id": "pix",
                    "type": "bank_transfer"
                }
            }]
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
        json=dados,
        timeout=30
    )

    try:
        resultado = resposta.json()
    except Exception:
        resultado = {}

    print(
        "STATUS MERCADO PAGO:",
        resposta.status_code,
        flush=True
    )
    print(
        "RESPOSTA:",
        resultado,
        flush=True
    )

    if resposta.status_code >= 400:
        enviar_mensagem(
            chat_id,
            f"❌ Erro ao gerar o Pix.\nCódigo: {resposta.status_code}"
        )
        return

    try:
        pagamento = resultado["transactions"]["payments"][0]
        metodo = pagamento["payment_method"]

        qr_base64 = metodo.get("qr_code_base64")
        copia_cola = metodo.get("qr_code")
        ticket_url = metodo.get("ticket_url")

    except (KeyError, IndexError, TypeError):
        enviar_mensagem(
            chat_id,
            "❌ Não consegui encontrar os dados do Pix."
        )
        return

    if qr_base64:
        try:
            imagem = base64.b64decode(qr_base64)

            requests.post(
                f"{TELEGRAM_API}/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": (
                        "💳 PIX DE R$ 4,99\n\n"
                        "📲 Escaneie o QR Code para pagar.\n\n"
                        "Após o pagamento, aguarde a confirmação automática."
                    )
                },
                files={
                    "photo": (
                        "pix.png",
                        imagem,
                        "image/png"
                    )
                },
                timeout=30
            )

        except Exception as erro:
            print(
                "ERRO QR CODE:",
                erro,
                flush=True
            )

    if copia_cola:
        enviar_mensagem(
            chat_id,
            f"📋 PIX COPIA E COLA:\n\n"
            f"{copia_cola}\n\n"
            "Após pagar, aguarde a confirmação automática."
        )

    elif ticket_url:
        enviar_mensagem(
            chat_id,
            f"💳 Abra o link abaixo para visualizar o pagamento:\n\n"
            f"{ticket_url}"
        )


def verificar_pedido(order_id):
    resposta = requests.get(
        f"https://api.mercadopago.com/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}"
        },
        timeout=20
    )

    print(
        "VERIFICAÇÃO DO PEDIDO:",
        resposta.status_code,
        resposta.text,
        flush=True
    )

    if resposta.status_code != 200:
        return None

    try:
        return resposta.json()
    except Exception:
        return None


def pagamento_aprovado(dados):
    if dados.get("status") == "processed":
        return True

    pagamentos = (
        dados.get("transactions", {})
        .get("payments", [])
    )

    for pagamento in pagamentos:
        if pagamento.get("status") == "approved":
            return True

    return False


def liberar_acesso(order_id):
    dados = verificar_pedido(order_id)

    if not dados:
        return

    print(
        "STATUS DO PEDIDO:",
        order_id,
        dados.get("status"),
        flush=True
    )

    if not pagamento_aprovado(dados):
        return

    if order_id in acessos_liberados:
        return

    referencia = dados.get("external_reference")

    if not referencia:
        return

    try:
        chat_id = int(referencia)
    except ValueError:
        return

    acessos_liberados.add(order_id)

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
        "🎉 Seu acesso foi liberado!\n\n"
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

    mensagem = dados.get("message")

    if mensagem:
        chat = mensagem.get("chat", {})
        texto = mensagem.get("text", "").strip()
        chat_id = chat.get("id")

        if not chat_id:
            return "OK", 200

        # Captura o ID do vídeo enviado ao bot
        video = mensagem.get("video")

        if video:
            video_id = video.get("file_id")

            if video_id:
                print(
                    "VIDEO_FILE_ID:",
                    video_id,
                    flush=True
                )

                enviar_mensagem(
                    chat_id,
                    "✅ Vídeo recebido!\n\n"
                    "Veja o VIDEO_FILE_ID nos logs do Render."
                )

        if texto == "/start":
            enviar_menu(chat_id)

        elif "@" in texto and " " not in texto:
            usuarios[chat_id] = texto

            enviar_mensagem(
                chat_id,
                "📧 E-mail salvo ✅\n\n"
                "Agora clique novamente em:\n"
                "🔥 GRUPO VITALÍCIO"
            )

        elif texto == "/pix":
            criar_pix(chat_id)

    callback = dados.get("callback_query")

    if callback:
        callback_id = callback.get("id")
        callback_data = callback.get("data")

        mensagem_callback = callback.get(
            "message",
            {}
        )

        chat = mensagem_callback.get(
            "chat",
            {}
        )

        chat_id = chat.get("id")

        if callback_id:
            responder_callback(callback_id)

        if callback_data == "comprar" and chat_id:
            email = usuarios.get(chat_id)

            if not email:
                enviar_mensagem(
                    chat_id,
                    "📧 Para continuar, envie seu e-mail."
                )
            else:
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
