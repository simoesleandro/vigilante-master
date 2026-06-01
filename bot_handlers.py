import os
import threading
import time

import telebot

from analisador import AnalisadorJuridico
from carteiro import fila_saida
from repo import ProcessoRepo


def register_handlers(
    bot: telebot.TeleBot,
    repo: ProcessoRepo,
    analisador: AnalisadorJuridico,
    chats_espectadores: list,
) -> None:

    def _autorizado(chat_id) -> bool:
        return str(chat_id) in chats_espectadores

    # ── AI analysis task (runs in a thread) ──────────────────────────────────

    def tarefa_ia_resumo(message, pid: str, proc: dict) -> None:
        try:
            andamentos = proc.get("ultimo_andamento")
            if not andamentos:
                bot.send_message(message.chat.id, "⚠️ Sem dados de andamentos no banco para análise.")
                return

            historico = repo.get_historico_contexto(pid)
            texto = analisador.analisar(proc, andamentos, historico)

            if not texto:
                bot.send_message(message.chat.id, "🛑 Servidores Google ocupados.")
                return

            tag = "ANÁLISE INTERATIVA COMPLETA" if historico else "ANÁLISE ESTRATÉGICA"
            mensagem_final = (
                f"🏛 <b>🧠 {tag} - {pid}</b>\n"
                f"<code>{proc['numero']}</code>\n"
                f"----------------------------------------\n\n"
                f"{texto}"
            )
            bot.send_message(message.chat.id, mensagem_final, parse_mode="HTML")

        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Erro Crítico na IA: {e}")

    # ── Context submission flow ───────────────────────────────────────────────

    def processar_texto_humano(message, pid: str, proc: dict) -> None:
        if not message.text:
            bot.send_message(message.chat.id, "⚠️ Digite um texto válido para adicionar ao contexto.")
            return

        agora = time.strftime('%d/%m/%Y %H:%M')
        repo.add_contexto(pid, agora, message.text)

        bot.send_message(
            message.chat.id,
            "🧠 Memória atualizada! Refazendo análise com histórico completo...",
            parse_mode="HTML",
        )
        proc_atualizado = repo.get_processo(pid)
        threading.Thread(target=tarefa_ia_resumo, args=(message, pid, proc_atualizado)).start()

    # ── Listing / removal helpers ─────────────────────────────────────────────

    def listar_processos(message) -> None:
        rows = repo.list_todos()
        if not rows:
            bot.send_message(message.chat.id, "📭 Nenhum processo cadastrado no banco de dados.")
            return

        texto = "📋 <b>PROCESSOS MONITORADOS:</b>\n\n"
        for r in rows:
            texto += f"🔹 <b>{r[0]}</b> ({r[1]})\n"
            texto += f"   Número: <code>{r[2]}</code>\n"
            texto += f"   Classe: {r[3]}\n\n"
        bot.send_message(message.chat.id, texto, parse_mode="HTML")

    def reenviar_notificacao(message, pid: str) -> None:
        proc = repo.get_processo(pid)
        if not proc:
            bot.send_message(message.chat.id, f"❌ ID {pid} não encontrado no banco de dados.")
            return
        andamento = proc.get("ultimo_andamento")
        if not andamento:
            bot.send_message(message.chat.id, f"⚠️ {pid} ainda não tem andamentos registrados.")
            return
        img_path = f"print_{pid}.png"
        fila_saida.put({
            "tribunal": proc["tribunal"],
            "conteudo": andamento,
            "proc": proc,
            "img": img_path if os.path.exists(img_path) else None,
        })
        bot.send_message(message.chat.id, f"📤 Reenvio de <b>{pid}</b> enfileirado.", parse_mode="HTML")

    def remover_processo(message, pid: str) -> None:
        if not repo.pid_exists(pid):
            bot.send_message(message.chat.id, f"❌ ID {pid} não encontrado no banco de dados.")
            return
        repo.delete_processo(pid)
        bot.send_message(
            message.chat.id,
            f"✅ Processo <b>{pid}</b> e seu histórico foram removidos com sucesso!",
            parse_mode="HTML",
        )

    # ── New processo wizard ───────────────────────────────────────────────────

    def iniciar_cadastro(message) -> None:
        bot.send_message(
            message.chat.id,
            "✍️ <b>Cadastro de Novo Processo:</b>\n\n"
            "Para cancelar a qualquer momento, digite 'cancelar'.\n\n"
            "1. Qual o <b>Tribunal</b>? (Responda exatamente TJRJ, STF ou TSE)",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(message, _obter_tribunal)

    def _obter_tribunal(message) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        tribunal = message.text.upper().strip()
        if tribunal not in ["TJRJ", "STF", "TSE"]:
            msg = bot.reply_to(message, "⚠️ Tribunal inválido. Digite TJRJ, STF ou TSE:")
            bot.register_next_step_handler(msg, _obter_tribunal)
            return
        bot.send_message(
            message.chat.id,
            f"Tribunal definido: {tribunal}\n\n2. Digite um <b>ID único</b> para o processo (Ex: TJRJ_5, STF_4):",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(message, _obter_pid, tribunal)

    def _obter_pid(message, tribunal: str) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        pid = message.text.upper().strip()
        if repo.pid_exists(pid):
            msg = bot.reply_to(message, f"⚠️ O ID {pid} já está cadastrado. Digite um ID diferente:")
            bot.register_next_step_handler(msg, _obter_pid, tribunal)
            return
        bot.send_message(
            message.chat.id,
            f"ID definido: {pid}\n\n3. Digite o <b>Número do Processo</b> (Ex: 3004566-28.2026.8.19.0000):",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(message, _obter_numero, tribunal, pid)

    def _obter_numero(message, tribunal: str, pid: str) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        numero = message.text.strip()
        bot.send_message(
            message.chat.id,
            f"Número definido: {numero}\n\n4. Digite a <b>URL de Consulta</b> do processo:",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(message, _obter_url, tribunal, pid, numero)

    def _obter_url(message, tribunal: str, pid: str, numero: str) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        url = message.text.strip()
        bot.send_message(
            message.chat.id,
            f"URL definida.\n\n5. Digite a <b>Classe Processual</b> (Ex: Mandado de Segurança Cível):",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(message, _obter_classe, tribunal, pid, numero, url)

    def _obter_classe(message, tribunal: str, pid: str, numero: str, url: str) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        classe = message.text.strip()
        bot.send_message(
            message.chat.id,
            f"Classe definida: {classe}\n\n6. Digite o <b>Rótulo da Parte</b> (Ex: Impetrante, Requerente):",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(message, _obter_parte_label, tribunal, pid, numero, url, classe)

    def _obter_parte_label(message, tribunal: str, pid: str, numero: str, url: str, classe: str) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        parte_label = message.text.strip()
        bot.send_message(
            message.chat.id,
            f"Rótulo definido: {parte_label}\n\n7. Digite o <b>Nome da Parte</b> (Ex: PDT DIRETÓRIO RJ):",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(message, _obter_parte_nome, tribunal, pid, numero, url, classe, parte_label)

    def _obter_parte_nome(message, tribunal: str, pid: str, numero: str, url: str, classe: str, parte_label: str) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        parte_nome = message.text.strip()
        bot.send_message(
            message.chat.id,
            f"Nome da parte definido: {parte_nome}\n\n8. Digite o <b>Resumo Base Inicial</b> do processo:",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(
            message, _obter_resumo, tribunal, pid, numero, url, classe, parte_label, parte_nome
        )

    def _obter_resumo(
        message, tribunal: str, pid: str, numero: str, url: str,
        classe: str, parte_label: str, parte_nome: str,
    ) -> None:
        if message.text.lower() == 'cancelar':
            bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
            return
        resumo = message.text.strip()
        try:
            repo.add_processo(pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo)
            bot.send_message(
                message.chat.id,
                f"✅ <b>Processo cadastrado com sucesso!</b>\n\n"
                f"📌 <b>ID:</b> {pid}\n"
                f"🏛 <b>Tribunal:</b> {tribunal}\n"
                f"⚖️ <b>Número:</b> {numero}",
                parse_mode="HTML",
            )
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Erro ao salvar processo no banco: {e}")

    # ── Telegram event handlers ───────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: True)
    def processar_clique_botao(call) -> None:
        if not _autorizado(call.message.chat.id):
            return
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        try:
            partes = call.data.split('|')
            if len(partes) < 2:
                return
            acao, pid = partes[0], partes[1]
            proc = repo.get_processo(pid)
            if not proc:
                bot.send_message(call.message.chat.id, "⚠️ Processo não encontrado no banco de dados.")
                return

            if acao == "resumo":
                texto_resumo = proc.get("resumo", "⚠️ Resumo não cadastrado no banco.")
                bot.send_message(call.message.chat.id, texto_resumo, parse_mode="HTML")

            elif acao == "ia":
                bot.send_message(
                    call.message.chat.id,
                    f"🔍 <b>IA</b> processando histórico de {pid}...",
                    parse_mode="HTML",
                )
                threading.Thread(target=tarefa_ia_resumo, args=(call.message, pid, proc)).start()

            elif acao == "reenviar":
                reenviar_notificacao(call.message, pid)

            elif acao == "ctx":
                msg_pergunta = bot.send_message(
                    call.message.chat.id,
                    f"📝 <b>Novo Contexto para {pid}:</b>\n"
                    f"Digite ou cole abaixo o resumo da petição ou despacho para guardar na memória e refazer a análise:",
                    parse_mode="HTML",
                )
                bot.register_next_step_handler(msg_pergunta, processar_texto_humano, pid, proc)

        except Exception as e:
            print(f"⚠️ Erro ao processar clique: {e}")

    @bot.message_handler(commands=['resumo', 'ia', 'listar', 'remover', 'adicionar', 'reenviar'])
    def comandos_digitados(message) -> None:
        if not _autorizado(message.chat.id):
            return
        try:
            partes = message.text.split()
            comando = partes[0].lower()

            if "/listar" in comando:
                listar_processos(message)
                return

            if "/adicionar" in comando:
                iniciar_cadastro(message)
                return

            if "/reenviar" in comando and len(partes) < 2:
                rows = repo.list_todos()
                if not rows:
                    bot.send_message(message.chat.id, "📭 Nenhum processo cadastrado.")
                    return
                texto = "📤 <b>Reenviar notificação — escolha o ID:</b>\n\n"
                for r in rows:
                    andamento = repo.get_processo(r[0]).get("ultimo_andamento")
                    status = "✅ tem andamento" if andamento else "⚠️ sem andamento"
                    texto += f"🔹 <code>/reenviar {r[0]}</code> ({r[1]}) — {status}\n"
                bot.send_message(message.chat.id, texto, parse_mode="HTML")
                return

            if len(partes) < 2:
                bot.reply_to(message, "⚠️ Use: /resumo ID, /ia ID, /reenviar ID ou /remover ID")
                return

            pid = partes[1].upper()

            if "/remover" in comando:
                remover_processo(message, pid)
                return

            if "/reenviar" in comando:
                reenviar_notificacao(message, pid)
                return

            proc = repo.get_processo(pid)
            if not proc:
                bot.reply_to(message, f"❌ ID {pid} não encontrado no banco de dados.")
                return

            if "/resumo" in comando:
                texto_resumo = proc.get("resumo", "⚠️ Resumo manual não cadastrado.")
                bot.send_message(
                    message.chat.id,
                    f"📖 <b>Resumo do BD ({pid}):</b>\n\n{texto_resumo}",
                    parse_mode="HTML",
                )

            elif "/ia" in comando:
                bot.send_message(
                    message.chat.id,
                    f"🔍 <b>IA</b> processando histórico de {pid}...",
                    parse_mode="HTML",
                )
                threading.Thread(target=tarefa_ia_resumo, args=(message, pid, proc)).start()

        except Exception as e:
            print(f"Erro no comando: {e}")
            bot.reply_to(message, "⚠️ Ocorreu um erro ao processar o comando.")
