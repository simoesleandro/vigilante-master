import html
import os
import queue
import time

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

fila_saida: queue.Queue = queue.Queue()


def carteiro_worker(bot: telebot.TeleBot, chats_espectadores: list) -> None:
    while True:
        t = fila_saida.get()
        if t is None:
            break
        try:
            p = t['proc']
            agora = time.strftime('%d/%m/%Y %H:%M')

            texto_bruto = t['conteudo']
            truncado = len(texto_bruto) > 250
            if truncado:
                texto_bruto = texto_bruto[:250] + "..."

            texto_extraido_seguro = html.escape(texto_bruto)
            if truncado:
                texto_extraido_seguro += "\n<i>[Texto cortado — use os botões abaixo]</i>"

            texto_html = (
                f"🏛 <b>NOVA MOVIMENTAÇÃO DETECTADA</b>\n"
                f"📌 <b>Processo:</b> <code>{p['numero']}</code>\n"
                f"⚖️ <b>Tribunal:</b> {t['tribunal']}\n"
                f"📋 <b>Classe:</b> {p['classe']}\n"
                f"👤 <b>{p['parte_label']}:</b> {p['parte_nome']}\n"
                f"📅 <b>Alerta:</b> {agora}\n\n"
                f"🔍 <b>Andamentos Recentes:</b>\n"
                f"<blockquote>🟡 <b>ATUALIZAÇÃO:</b>\n{texto_extraido_seguro}</blockquote>\n"
                f"🔗 <a href='{p['url']}'>Abrir no Tribunal</a>"
            )

            markup = InlineKeyboardMarkup()
            btn_resumo = InlineKeyboardButton("📖 Resumo", callback_data=f"resumo|{p['id']}")
            btn_ia = InlineKeyboardButton("🧠 Análise IA", callback_data=f"ia|{p['id']}")
            btn_ctx = InlineKeyboardButton("🗣️ Add Contexto", callback_data=f"ctx|{p['id']}")
            btn_reenviar = InlineKeyboardButton("📤 Reenviar", callback_data=f"reenviar|{p['id']}")
            markup.row(btn_resumo, btn_ia)
            markup.row(btn_ctx, btn_reenviar)

            for chat in chats_espectadores:
                if t['img'] and os.path.exists(t['img']):
                    with open(t['img'], 'rb') as f:
                        bot.send_photo(chat, f, caption=texto_html, parse_mode="HTML", reply_markup=markup)
                else:
                    bot.send_message(chat, texto_html, parse_mode="HTML", reply_markup=markup)

        except Exception as e:
            print(f"❌ Erro crítico no Carteiro ao tentar enviar pro Telegram: {e}")

        fila_saida.task_done()
        time.sleep(1)
