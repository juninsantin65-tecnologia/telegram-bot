import os
import uuid
import base64
import json
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
        "text": texto,
        "parse_mode": "Markdown"
    }

    if teclado:
        dados["reply_markup"] = teclado

    try:
        resposta = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=dados,
            timeout=20
        )

        print(
            "TELEGRAM SENDMESSAGE:",
            resposta.status_code,
            flush=True
        )

    except Exception as erro:
        print(
            "ERRO TELEGRAM:",
            erro,
            flush=True
        )


def enviar_menu(chat_id):
    teclado = {
        "inline_keyboard": [[
            {
                "text": "🔥 Acessar agora R$4,99🔥",
                "callback_data": "comprar"
            }
        ]]
    }

    texto = """🔥 𝙋𝙍𝙊𝙈𝙊𝘾̧𝘼̃𝙊 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝘼 🔥

Você viu… pensou… saiu…
Mas o acesso ainda está disponível por tempo limitado ⏳

📲 𝘼𝙘𝙚𝙨𝙨𝙤 𝙞𝙢𝙚𝙙𝙞𝙖𝙩𝙤 𝙣𝙤 𝙏𝙚𝙡𝙚𝙜𝙧𝙖𝙢
🔞 𝘾𝙤𝙣𝙩𝙚𝙪́𝙙𝙤𝙨 𝙘𝙤𝙢𝙥𝙡𝙚𝙩𝙤𝙨, sem cortes
⚡ 𝘼𝙩𝙪𝙖𝙡𝙞𝙯𝙖𝙘̧𝙤̃𝙚𝙨 𝙛𝙧𝙚𝙦𝙪𝙚𝙣𝙩𝙚𝙨
📂 𝙏𝙪𝙙𝙤 𝙤𝙧𝙜𝙖𝙣𝙞𝙯𝙖𝙙𝙤 para você acessar na hora

💥 𝙋𝙍𝙀𝘾̧𝙊 𝙋𝙍𝙊𝙈𝙊𝘾𝙄𝙊𝙉𝘼𝙇
✨ 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝙊 𝙋𝘼𝙍𝘼 𝙌𝙐𝙀𝙈 𝙑𝙊𝙇𝙏𝙊𝙐

Depois que sair, não aparece de novo 👀

👉 𝙀𝙣𝙩𝙧𝙚 𝙖𝙜𝙤𝙧𝙖 e garanta seu acesso 🔥📲"""

    if VIDEO_FILE_ID:
        try:
            resposta = requests.post(
                f"{TELEGRAM_API}/sendVideo",
                data={
                    "chat_id": chat_id,
                    "video": VIDEO_FILE_ID,
                    "caption": texto,
                    "reply_markup": json.dumps(
                        teclado,
                        ensure_ascii=False
                    )
                },
                timeout=30
            )

            print(
                "TELEGRAM SENDVIDEO:",
                resposta.status_code,
                flush=True
            )

            print(
                "RESPOSTA SENDVIDEO:",
                resposta.text,
                flush=True
            )

        except Exception as erro:
            print(
                "ERRO AO ENVIAR VIDEO:",
                erro,
                flush=True
            )

            enviar_mensagem(
                chat_id,
                texto,
                teclado
            )

    else:
        enviar_mensagem(
            chat_id,
            texto,
            teclado
        )


def responder_callback(callback_id):
    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={
                "callback_query_id": callback_id
            },
            timeout=20
        )

    except Exception as erro:
        print(
            "ERRO CALLBACK:",
            erro,
            flush=True
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

    try:
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

    except Exception as erro:
        print(
            "ERRO MERCADO PAGO:",
            erro,
            flush=True
        )

        enviar_mensagem(
            chat_id,
            "❌ Não foi possível conectar ao sistema de pagamento."
        )
        return

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

            resposta_qr = requests.post(
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

            print(
                "ENVIO QR CODE:",
                resposta_qr.status_code,
                flush=True
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
            "📋 *PIX COPIA E COLA:*\n\n"
            f"`{copia_cola}`\n\n"
            "👆 Toque no código acima para copiar\n\n"
            "Após pagar, aguarde a confirmação automática."
        )

    elif ticket_url:
        enviar_mensagem(
            chat_id,
            "💳 Abra o link abaixo para visualizar o pagamento:\n\n"
            f"{ticket_url}"
        )


def verificar_pedido(order_id):
    try:
        resposta = requests.get(
            f"https://api.mercadopago.com/v1/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {MP_ACCESS_TOKEN}"
            },
            timeout=20
        )

    except Exception as erro:
        print(
            "ERRO VERIFICANDO PEDIDO:",
            erro,
            flush=True
        )
        return None

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
        print(
            "PAGAMENTO AINDA NÃO APROVADO:",
            order_id,
            flush=True
        )
        return

    if order_id in acessos_liberados:
        print(
            "ACESSO JÁ LIBERADO:",
            order_id,
            flush=True
        )
        return

    referencia = dados.get("external_reference")

    if not referencia:
        print(
            "SEM EXTERNAL_REFERENCE:",
            order_id,
            flush=True
        )
        return

    try:
        chat_id = int(referencia)

    except ValueError:
        print(
            "EXTERNAL_REFERENCE INVÁLIDA:",
            referencia,
            flush=True
        )
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

    print(
        "ACESSO LIBERADO PARA:",
        chat_id,
        flush=True
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
                "🔥 ACESSAR AGORA"
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
