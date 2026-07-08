import html
import os
import queue
import time
from urllib.parse import urlparse

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

fila_saida: queue.Queue = queue.Queue()


def montar_mensagem(t: dict, p: dict, agora: str) -> tuple:
    texto_bruto = t['conteudo']
    truncado = len(texto_bruto) > 250
    if truncado:
        texto_bruto = texto_bruto[:250] + "..."

    texto_extraido_seguro = html.escape(texto_bruto)
    if truncado:
        texto_extraido_seguro += "\n<i>[Texto cortado — use os botões abaixo]</i>"

    numero_seg = html.escape(str(p.get('numero', '')))
    tribunal_seg = html.escape(str(t.get('tribunal', '')))
    classe_seg = html.escape(str(p.get('classe', '')))
    parte_label_seg = html.escape(str(p.get('parte_label', '')))
    parte_nome_seg = html.escape(str(p.get('parte_nome', '')))

    url_raw = str(p.get('url', ''))
    parsed = urlparse(url_raw)
    url_seg = html.escape(url_raw, quote=True)
    href_seguro = url_seg if parsed.scheme in ('http', 'https') else ''
    link_html = f"🔗 <a href='{href_seguro}'>Abrir no Tribunal</a>" if href_seguro else "🔗 (URL inválida)"

    texto_html = (
        f"🏛 <b>NOVA MOVIMENTAÇÃO DETECTADA</b>\n"
        f"📌 <b>Processo:</b> <code>{numero_seg}</code>\n"
        f"⚖️ <b>Tribunal:</b> {tribunal_seg}\n"
        f"📋 <b>Classe:</b> {classe_seg}\n"
        f"👤 <b>{parte_label_seg}:</b> {parte_nome_seg}\n"
        f"📅 <b>Alerta:</b> {agora}\n\n"
        f"🔍 <b>Andamentos Recentes:</b>\n"
        f"<blockquote>🟡 <b>ATUALIZAÇÃO:</b>\n{texto_extraido_seguro}</blockquote>\n"
        f"{link_html}"
    )

    tem_foto = bool(t.get('img') and os.path.exists(t['img']))
    return texto_html, tem_foto


def carteiro_worker(bot: telebot.TeleBot, chats_espectadores: list) -> None:
    while True:
        t = fila_saida.get()
        if t is None:
            break
        try:
            p = t['proc']
            agora = time.strftime('%d/%m/%Y %H:%M')

            texto_html, tem_foto = montar_mensagem(t, p, agora)

            markup = InlineKeyboardMarkup()
            btn_resumo = InlineKeyboardButton("📖 Resumo", callback_data=f"resumo|{p['id']}")
            btn_ia = InlineKeyboardButton("🧠 Análise IA", callback_data=f"ia|{p['id']}")
            btn_ctx = InlineKeyboardButton("🗣️ Add Contexto", callback_data=f"ctx|{p['id']}")
            btn_reenviar = InlineKeyboardButton("📤 Reenviar", callback_data=f"reenviar|{p['id']}")
            markup.row(btn_resumo, btn_ia)
            markup.row(btn_ctx, btn_reenviar)

            if t['img'] and not tem_foto:
                print(f"⚠️ Carteiro: foto esperada em '{t['img']}' mas arquivo não encontrado — enviando sem foto.")

            for chat in chats_espectadores:
                if tem_foto:
                    with open(t['img'], 'rb') as f:
                        bot.send_photo(chat, f, caption=texto_html, parse_mode="HTML", reply_markup=markup)
                else:
                    bot.send_message(chat, texto_html, parse_mode="HTML", reply_markup=markup)

        except Exception as e:
            print(f"❌ Erro crítico no Carteiro ao tentar enviar pro Telegram: {e}")

        fila_saida.task_done()
        time.sleep(1)
