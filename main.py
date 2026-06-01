import html
import logging
import os
import ssl
import sys
import threading
import time
import traceback

import certifi
from output_stream import ativar as _ativar_stream
_ativar_stream()

# ── SSL patches ── devem rodar antes de qualquer import de rede ─────────────
_original_load_verify = ssl.SSLContext.load_verify_locations

def _patched_load_verify(self, cafile=None, capath=None, cadata=None):
    if cafile and not cadata:
        try:
            with open(cafile, 'r', encoding='utf-8') as f:
                cadata = f.read()
            cafile = None
        except Exception:
            pass
    return _original_load_verify(self, cafile=cafile, capath=capath, cadata=cadata)

ssl.SSLContext.load_verify_locations = _patched_load_verify
ssl.SSLContext.load_default_certs = lambda self, purpose=ssl.Purpose.SERVER_AUTH: \
    self.load_verify_locations(cafile=certifi.where())
ssl._create_default_https_context = ssl._create_unverified_context

# ── Third-party imports ───────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

import telebot
from google import genai
from playwright.sync_api import sync_playwright

telebot.logger.setLevel(logging.CRITICAL)

# ── Project modules ───────────────────────────────────────────────────────────
from analisador import AnalisadorJuridico
from bot_handlers import register_handlers
from carteiro import carteiro_worker, fila_saida
from detector import AndamentoInicial, Detector, FalhaCaptura, Mudanca
from repo import ProcessoRepo
from scrapers import (
    extrair_playwright,
    extrair_stf_stealth,
    extrair_tse_stealth,
    exterminar_zumbis,
)
from web_panel import iniciar_servidor_web

# ── Config ────────────────────────────────────────────────────────────────────
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
ADMIN_ID = os.getenv("ADMIN_ID", "").strip().strip("[]") or None
_chats_raw = os.getenv("CHATS_ESPECTADORES", "").strip().strip("[]")
CHATS_ESPECTADORES = [c.strip() for c in _chats_raw.split(",") if c.strip()]


def _notify_admin(bot, texto: str) -> None:
    if not ADMIN_ID:
        return
    try:
        bot.send_message(ADMIN_ID, texto, parse_mode="HTML")
    except Exception as e:
        print(f"❌ Erro ao notificar admin: {e}")
API_KEY_GEMINI = os.getenv("API_KEY_GEMINI")


# ── Orchestration ─────────────────────────────────────────────────────────────

def _despachar(detector, repo, bot, analisador, proc, tribunal, txt, img):
    resultado = detector.processar(proc, tribunal, txt, img)
    pid = proc['id']

    if resultado is None:
        print(f"      ✅ {pid}: Sem novidades.")
        return

    if isinstance(resultado, FalhaCaptura):
        print(f"      ❌ {pid}: Falha na leitura (#{resultado.contagem}).")
        if resultado.contagem == detector.limite_alerta:
            msg = (
                f"⚠️ <b>ALERTA DE CAPTURA ({tribunal})</b>\n\n"
                f"O processo <code>{proc['numero']}</code> ({pid}) falhou por "
                f"{detector.limite_alerta} ciclos consecutivos.\n"
                f"O layout do site pode ter mudado ou o serviço está instável."
            )
            _notify_admin(bot, msg)
        return

    if isinstance(resultado, AndamentoInicial):
        repo.save_andamento(pid, resultado.txt_novo)
        print(f"      📁 {pid}: Base inicial salva no Banco de Dados.")
        return

    if isinstance(resultado, Mudanca):
        print(f"      🚨 {pid}: MUDANÇA DETECTADA!")
        repo.save_andamento(pid, resultado.txt_novo)
        threading.Thread(
            target=lambda r=resultado, p=proc: repo.save_resumo(
                r.pid, analisador.resumo_evolutivo(p, r.txt_novo)
            ),
            daemon=True,
        ).start()
        fila_saida.put({"tribunal": tribunal, "conteudo": resultado.txt_novo, "proc": proc, "img": img})


def iniciar_vigilancia():
    print("🚀 Vigilante Master v14.0 Inicializando...")

    repo = ProcessoRepo()
    analisador_ia = AnalisadorJuridico(genai.Client(api_key=API_KEY_GEMINI))
    detector = Detector()
    bot = telebot.TeleBot(TOKEN_TELEGRAM)

    register_handlers(bot, repo, analisador_ia, CHATS_ESPECTADORES)

    _notify_admin(bot, "🚀 <b>Vigilante Master v14.0 Online!</b>\nBanco de Dados, IA Evolutiva e Painel Web Ativados.")

    threading.Thread(
        target=carteiro_worker, args=(bot, CHATS_ESPECTADORES), daemon=True
    ).start()
    def _run_polling():
        while True:
            try:
                bot.infinity_polling(skip_pending=True)
            except Exception as e:
                if "409" in str(e):
                    print("⚠️ Conflito de instância (409) — aguardando 30s para reconectar...")
                    time.sleep(30)
                else:
                    print(f"⚠️ Polling encerrado: {e}")
                    break

    threading.Thread(target=_run_polling, daemon=True).start()
    threading.Thread(target=iniciar_servidor_web, daemon=True).start()

    cnt = 0
    while True:
        print(f"\n--- CICLO #{cnt} | {time.strftime('%H:%M:%S')} ---")
        exterminar_zumbis()

        processos_tjrj = repo.list_processos("TJRJ")
        processos_stf = repo.list_processos("STF")
        processos_tse = repo.list_processos("TSE")

        with sync_playwright() as p:
            for pr in processos_tjrj:
                t, i = extrair_playwright(p, pr['id'], pr['url'])
                _despachar(detector, repo, bot, analisador_ia, pr, "TJRJ", t, i)

        for pr in processos_stf:
            t, i = extrair_stf_stealth(pr['id'], pr['url'])
            _despachar(detector, repo, bot, analisador_ia, pr, "STF", t, i)

        if cnt % 10 == 0:
            def rodar_tse(lista, _bot=bot, _det=detector, _repo=repo, _ia=analisador_ia):
                for pr in lista:
                    t, i = extrair_tse_stealth(
                        pr['id'], pr['url'], pr['numero'],
                        on_captcha=lambda n, b=_bot: _notify_admin(b, f"🔑 Resolva TSE: {n}"),
                    )
                    _despachar(_det, _repo, _bot, _ia, pr, "TSE", t, i)
                    time.sleep(5)
            threading.Thread(target=rodar_tse, args=(processos_tse,), daemon=True).start()

        print("✅ Ciclo finalizado. Dormindo 2 min...")
        time.sleep(120)
        cnt += 1


if __name__ == "__main__":
    try:
        iniciar_vigilancia()
    except Exception as e:
        erro_str = str(e)
        erro_trace = traceback.format_exc()
        erro_str_curto = erro_str[:400] + " [...]" if len(erro_str) > 400 else erro_str
        erro_trace_curto = erro_trace[-1000:] if len(erro_trace) > 1000 else erro_trace

        mensagem_alerta = (
            "🚨 <b>VIGILANTE MASTER CAIU!</b> 🚨\n\n"
            "A Máquina Virtual encontrou um Erro Fatal e o script foi interrompido.\n\n"
            f"<b>Motivo:</b> {html.escape(erro_str_curto)}\n\n"
            "<b>Log:</b>\n"
            f"<code>{html.escape(erro_trace_curto)}</code>\n\n"
            "⚠️ <i>Acesse a VM para reiniciar o sistema.</i>"
        )
        if ADMIN_ID:
            try:
                _emergency_bot = telebot.TeleBot(TOKEN_TELEGRAM)
                _emergency_bot.send_message(ADMIN_ID, mensagem_alerta, parse_mode="HTML")
                print("🚨 Alerta de CRASH enviado com sucesso para o Telegram!")
            except Exception as e_telegram:
                print(f"❌ Falha fatal ao avisar no Telegram. Erro: {e_telegram}")
