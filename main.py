import os
import sys
import io
import time
import threading
import queue
import ssl
import certifi
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from playwright.sync_api import sync_playwright
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import html
import traceback
import sqlite3
import logging
from flask import Flask, Response, render_template_string
from dotenv import load_dotenv

load_dotenv()

# Força a saída padrão original a aceitar emojis (UTF-8) sem buffering
sys.__stdout__.reconfigure(encoding='utf-8', write_through=True)
sys.__stderr__.reconfigure(encoding='utf-8', write_through=True)

# Monkey-patch para contornar travamento no Windows Certificate Store (carregamento em memória para evitar hangs no drive de rede Z:)
original_load_verify_locations = ssl.SSLContext.load_verify_locations

def patched_load_verify_locations(self, cafile=None, capath=None, cadata=None):
    if cafile and not cadata:
        try:
            with open(cafile, 'r', encoding='utf-8') as f:
                cadata = f.read()
            cafile = None
        except Exception:
            pass
    return original_load_verify_locations(self, cafile=cafile, capath=capath, cadata=cadata)

ssl.SSLContext.load_verify_locations = patched_load_verify_locations

def patched_load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
    self.load_verify_locations(cafile=certifi.where())
ssl.SSLContext.load_default_certs = patched_load_default_certs


# ==========================================
# 🔌 PROTOCOLO DE CLONAGEM DE TERMINAL E FILA WEB
# ==========================================
fila_web = queue.Queue()

class CloneTerminal:
    def __init__(self):
        # Captura o descritor de saída padrão original do sistema
        self.terminal_original = sys.__stdout__
        
    def write(self, mensagem):
        # 1. Replica a escrita no terminal físico/VM instantaneamente
        self.terminal_original.write(mensagem)
        self.terminal_original.flush()
        
        # 2. Sanitiza e encaminha o fluxo de texto para a fila de streaming da página web
        if mensagem.strip():
            msg_segura = mensagem.replace('\n', '').replace('\r', '')
            fila_web.put(msg_segura)
            
    def flush(self):
        self.terminal_original.flush()

# Ativa o redirecionamento global do stdout
sys.stdout = CloneTerminal()

# ==========================================
# 🛡️ CONFIGURAÇÕES, SSL E SUPRESSÃO DE LOGS
# ==========================================
ssl._create_default_https_context = ssl._create_unverified_context
lock_navegador = threading.Lock() 
ia_lock = threading.Lock()
VERSAO_CHROME_VM = 147 

# Supressão de logs redundantes de rede para limpeza do console
logging.getLogger('werkzeug').setLevel(logging.ERROR)
telebot.logger.setLevel(logging.CRITICAL)

TOKEN_TELEGRAM     = os.getenv("TOKEN_TELEGRAM")
ADMIN_ID           = os.getenv("ADMIN_ID")
CHATS_ESPECTADORES = os.getenv("CHATS_ESPECTADORES", "").split(",")
API_KEY_GEMINI     = os.getenv("API_KEY_GEMINI")

client = genai.Client(api_key=API_KEY_GEMINI)
bot = telebot.TeleBot(TOKEN_TELEGRAM)
fila_saida = queue.Queue() 

# ==========================================
# 1. PROCESSOS (MANTIDOS APENAS PARA A MIGRAÇÃO INICIAL)
# ==========================================
PROCESSOS_TJRJ = [
    {
        "id": "TJRJ_1", 
        "numero": "3004566-28.2026.8.19.0000", 
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_nome_parte_publica&acao_retorno=processo_consulta_nome_parte_publica&num_processo=30045662820268190000&num_chave=&hash=b33f48b0cc0ad69e5cd182e3751fd64e&num_chave_documento=", 
        "parte_label": "Impetrante", 
        "parte_nome": "PDT - PARTIDO DEMOCRÁTICO TRABALHISTA DIRETÓRIO RJ", 
        "classe": "Mandado de Segurança Cível (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_1:</b>\n\n<b>Cerne:</b> MS contra as regras da eleição da Mesa Diretora da ALERJ (pede voto secreto).\n<b>Última Decisão:</b> Liminar <b>INDEFERIDA</b> sob o argumento de que é assunto interno da casa (<i>interna corporis</i> - Tema 1.120 STF).\n<b>Status:</b> Prazos abertos para manifestação do Estado e MP. Aguardando julgamento de mérito."
    },
    {
        "id": "TJRJ_2", 
        "numero": "3004326-39.2026.8.19.0000", 
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30043263920268190000&num_chave=&num_chave_documento=&hash=2ad7164906ea016a598e771470c6a7fb", 
        "parte_label": "Impetrante", 
        "parte_nome": "LUIZ PAULO CORRÊA DA ROCHA", 
        "classe": "Mandado de Segurança Cível (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_2:</b>\n\n<b>Cerne:</b> MS individual impetrado por Luiz Paulo contra ato da ALERJ.\n<b>Última Decisão:</b> Despacho de mero expediente em 13/04/2026. Prazo de manifestação do impetrante já encerrou.\n<b>Status:</b> Autos no Órgão Especial aguardando manifestação do MP ou julgamento."
    },
    {
        "id": "TJRJ_3", 
        "numero": "3004629-53.2026.8.19.0000", 
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30046295320268190000&num_chave=&num_chave_documento=&hash=85afa7fb1115618798dc54ecb979febd", 
        "parte_label": "Impetrante", 
        "parte_nome": "LUIZ PAULO CORRÊA DA ROCHA", 
        "classe": "Mandado de Segurança Cível (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_3:</b>\n\n<b>Cerne:</b> Novo MS de Luiz Paulo visando suspender/invalidar a eleição da Mesa da ALERJ.\n<b>Última Decisão:</b> Liminar <b>INDEFERIDA</b> em 15/04/2026 (mesmo motivo do TJRJ_1: <i>interna corporis</i>).\n<b>Status:</b> Prazos correndo até maio/2026 para o Estado e Impetrante se manifestarem."
    },
    {
        "id": "TJRJ_4", 
        "numero": "3006257-77.2026.8.19.0000", 
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30062577720268190000&num_chave=&num_chave_documento=&hash=da8242e844340fbe2106c1a341df9b82", 
        "parte_label": "Requerente", 
        "parte_nome": "PARTIDO DEMOCRÁTICO TRABALHISTA", 
        "classe": "Tutela Cautelar Antecedente (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_4:</b>\n\n<b>Cerne:</b> Ação Cautelar do PDT para tentar forçar uma liminar em apoio ao processo TJRJ_1.\n<b>Última Decisão:</b> Redistribuído por prevenção ao Relator Ricardo Couto.\n<b>Status:</b> Os autos estão conclusos para decisão sobre o pedido de urgência desde 27/04."
    }
]

PROCESSOS_STF = [
    {
        "id": "STF_1", 
        "numero": "ADI 7942", 
        "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7531465", 
        "parte_label": "Impetrante", 
        "parte_nome": "PARTIDO SOCIAL DEMOCRÁTICO - PSD DIRETÓRIO NACIONAL", 
        "classe": "Ação Direta de Inconstitucionalidade",
        "resumo": "🏛️ <b>RESUMO STF_1:</b>\n\n<b>Cerne:</b> ADI contra as regras da eleição indireta para Governador-Tampão do RJ.\n<b>Última Decisão:</b> Min. Luiz Fux deferiu liminar parcial suspendendo o voto aberto, mas manteve a eleição indireta.\n<b>Status:</b> Em julgamento no Plenário Virtual, aguardando conclusão após pedidos de destaque."
    },
    {
        "id": "STF_2", 
        "numero": "RLC 92644", 
        "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7547470", 
        "parte_label": "Reclamante", 
        "parte_nome": "DIRETÓRIO ESTADUAL DO PARTIDO SOCIAL DEMOCRÁTICO DO RIO DE JANEIRO - PSD/RJ", 
        "classe": "Reclamação",
        "resumo": "🏛️ <b>RESUMO STF_2:</b>\n\n<b>Cerne:</b> Reclamação para forçar a ALERJ a cumprir a decisão da ADI 7942 (STF_1).\n<b>Última Decisão:</b> Min. Cristiano Zanin deferiu liminar <b>SUSPENDENDO</b> a eleição indireta até decisão final do Plenário.\n<b>Status:</b> Vinculado à ADI 7942. O Presidente do TJRJ segue no comando do Executivo estadual."
    },
    {
        "id": "STF_3", 
        "numero": "ADPF 1319", 
        "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7569263", 
        "parte_label": "Requerente", 
        "parte_nome": "PARTIDO DEMOCRÁTICO TRABALHISTA – PDT", 
        "classe": "Arguição de Descumprimento de Preceito Fundamental",
        "resumo": "🏛️ <b>RESUMO STF_3:</b>\n\n<b>Cerne:</b> ADPF do PDT também questionando atos da ALERJ sobre a eleição indireta para Governador.\n<b>Última Decisão:</b> Autos conclusos em 05/05/2026 para o Min. Luiz Fux.\n<b>Status:</b> Aguardando decisão liminar urgente do relator."
    }
]

PROCESSOS_TSE = [
    {
        "id": "TSE_1", 
        "numero": "0603507-14.2022.6.19.0000", 
        "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0603507-14.2022.6.19.0000", 
        "parte_label": "Recorrente", 
        "parte_nome": "COLIGAÇÃO A VIDA VAI MELHORAR / MARCELO RIBEIRO FREIXO", 
        "classe": "Recurso Ordinário Eleitoral",
        "resumo": "🗳️ <b>RESUMO TSE_1:</b>\n\n<b>Cerne:</b> Recurso sobre as eleições de 2022 acusando a chapa de Cláudio Castro de conduta vedada a agente público.\n<b>Última Decisão:</b> Acórdão proferido em 23/04/2026. A defense opôs Embargos de Declaração.\n<b>Status:</b> Publicação de intimações em andamento. Aguarda julgamento dos Embargos pela Min. Isabel Gallotti."
    },
    {
        "id": "TSE_2", 
        "numero": "0606570-47.2022.6.19.0000", 
        "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0606570-47.2022.6.19.0000", 
        "parte_label": "Recorrente", 
        "parte_nome": "MINISTÉRIO PÚBLICO ELEITORAL", 
        "classe": "Recurso Ordinário Eleitoral",
        "resumo": "🗳️ <b>RESUMO TSE_2:</b>\n\n<b>Cerne:</b> Processo-irmão do TSE_1, focado em abuso de poder econômico nas eleições de 2022.\n<b>Última Decisão:</b> Acórdão proferido em 23/04/2026. Defesa opôs Embargos de Declaração.\n<b>Status:</b> Intimações publicadas no DJE. Autos conclusos para análise dos Embargos pela relatora."
    }
]

# ==========================================
# 2. INTERFACE HACKER DO FLASK (PAINEL WEB EVO)
# ==========================================
app = Flask(__name__)

HTML_HACKER = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VIGILANTE MASTER // CORE TERMINAL</title>
    <style>
        body {
            background-color: #030303;
            color: #00ff33;
            font-family: 'Courier New', Courier, monospace;
            margin: 0;
            padding: 10px; /* Reduzido para caber bem no mobile */
            overflow: hidden;
        }
        h1 {
            text-align: center;
            text-shadow: 0 0 12px #00ff33;
            border-bottom: 1px dashed #00ff33;
            padding-bottom: 10px;
            /* clamp() faz a fonte ser fluida: pequena no celular, grande no monitor */
            font-size: clamp(1rem, 4vw, 1.4rem); 
            letter-spacing: 1px;
            margin-top: 5px;
        }
        #painel-logs {
            height: 85vh;
            overflow-y: auto;
            background-color: #000000;
            border: 1px solid #00ff33;
            padding: 15px;
            box-shadow: inset 0 0 20px #002200, 0 0 15px #00ff33;
            font-size: clamp(0.85rem, 3vw, 1rem); /* Ajuste dinâmico de leitura */
        }
        .linha { 
            margin-bottom: 8px; 
            line-height: 1.5;
            word-wrap: break-word; /* Força quebras de linha em textos longos no mobile */
        }
        /* O cursor piscando verde no final do texto */
        .cursor {
            display: inline-block;
            width: 8px;
            height: 15px;
            background-color: #00ff33;
            animation: piscar 1s infinite;
            vertical-align: middle;
            margin-left: 2px;
        }
        @keyframes piscar {
            0%, 49% { opacity: 1; }
            50%, 100% { opacity: 0; }
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #000; border-left: 1px solid #00ff33; }
        ::-webkit-scrollbar-thumb { background: #00ff33; }
    </style>
</head>
<body>
    <h1>[ 👁️ VIGILANTE MASTER v14.0 ]</h1>
    <div id="painel-logs">
        <div class="linha">>> Inicializando handshake com a infraestrutura local... OK.</div>
        <div class="linha">>> Conectando canais de streaming SSE... OK.</div><br>
    </div>

    <script>
        const painel = document.getElementById('painel-logs');
        const evento = new EventSource('/stream');
        
        // Fila de sincronização para as mensagens não se atropelarem
        let filaDigitacao = Promise.resolve();

        // O Motor de Digitação Hacker
        function digitarTexto(elemento, htmlCompleto, velocidade = 10) {
            return new Promise(resolve => {
                let i = 0;
                let isTag = false;
                let textoExibido = "";
                
                elemento.innerHTML = '<span class="cursor"></span>';
                
                function proximoCaractere() {
                    if (i < htmlCompleto.length) {
                        let char = htmlCompleto.charAt(i);
                        textoExibido += char;
                        
                        // Atualiza o texto na tela sempre mantendo o bloco do cursor piscando no final
                        elemento.innerHTML = textoExibido + '<span class="cursor"></span>';
                        
                        // Se abrir uma tag HTML, liga o modo turbo. Se fechar, volta ao normal.
                        if (char === '<') isTag = true;
                        if (char === '>') isTag = false;
                        
                        i++;
                        painel.scrollTop = painel.scrollHeight; // Auto-scroll
                        
                        if (isTag) {
                            proximoCaractere(); // Pula o delay se for tag
                        } else {
                            setTimeout(proximoCaractere, velocidade); // Delay normal de digitação
                        }
                    } else {
                        elemento.innerHTML = textoExibido; // Remove o cursor ao terminar
                        resolve(); // Libera a fila para a próxima mensagem
                    }
                }
                proximoCaractere();
            });
        }
        
        evento.onmessage = function(event) {
            const novaLinha = document.createElement('div');
            novaLinha.className = 'linha';
            painel.appendChild(novaLinha);
            
            // Joga a mensagem nova no final da fila de digitação
            filaDigitacao = filaDigitacao.then(() => digitarTexto(novaLinha, ">> " + event.data));
        };
        
        evento.onerror = function() {
            console.log("Aguardando reconexão de pacotes do servidor...");
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_HACKER)

@app.route('/stream')
def stream():
    def gerar_eventos():
        while True:
            msg = fila_web.get()
            yield f"data: {msg}\n\n"
    return Response(gerar_eventos(), mimetype='text/event-stream')

def iniciar_servidor_web():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# ==========================================
# 3. INTERAÇÃO INTERNA COM O BANCO DE DADOS
# ==========================================
def exterminar_zumbis():
    """Força o Windows da VM a matar qualquer chromedriver e chrome órfão de automação"""
    try:
        os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
        cmd_ps = (
            'powershell -Command "'
            'Get-CimInstance Win32_Process -Filter \\"name = \'chrome.exe\'\\" | '
            'Where-Object {$_.CommandLine -like \'*--remote-debugging-port*\' -or $_.CommandLine -like \'*--headless*\'} | '
            'ForEach-Object {Stop-Process $_.ProcessId -Force}'
            '"'
        )
        os.system(cmd_ps)
        time.sleep(2)
    except: pass

def inicializar_banco():
    """Cria tabelas e migra os processos do script para o SQLite se estiver vazio"""
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processos (
                pid TEXT PRIMARY KEY,
                numero TEXT,
                url TEXT,
                tribunal TEXT,
                parte_label TEXT,
                parte_nome TEXT,
                classe TEXT,
                resumo_inicial TEXT,
                ultimo_andamento TEXT
            )
        ''')
        
        try:
            cursor.execute("ALTER TABLE processos ADD COLUMN ultimo_andamento TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
            
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_contexto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pid TEXT,
                data_hora TEXT,
                texto TEXT,
                FOREIGN KEY (pid) REFERENCES processos(pid)
            )
        ''')
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM processos")
        if cursor.fetchone()[0] == 0:
            print("📦 Migrando processos do script para o SQLite...")
            todos_processos = []
            for p in PROCESSOS_TJRJ: p['tribunal'] = 'TJRJ'; todos_processos.append(p)
            for p in PROCESSOS_STF: p['tribunal'] = 'STF'; todos_processos.append(p)
            for p in PROCESSOS_TSE: p['tribunal'] = 'TSE'; todos_processos.append(p)
            
            for p in todos_processos:
                cursor.execute('''
                    INSERT INTO processos (pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo_inicial)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (p['id'], p['numero'], p['url'], p['tribunal'], p['parte_label'], p['parte_nome'], p['classe'], p['resumo']))
            conn.commit()
            print("✅ Todos os processos migrados com sucesso!")
            
        conn.close()
    except Exception as e:
        print(f"❌ Erro crítico ao inicializar o banco: {e}")

def buscar_processos_do_bd(tribunal):
    """Busca a lista de processos para o bot monitorar"""
    lista = []
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT pid, numero, url, parte_label, parte_nome, classe, resumo_inicial, ultimo_andamento FROM processos WHERE tribunal = ?", (tribunal,))
        for row in cursor.fetchall():
            lista.append({
                "id": row[0], "numero": row[1], "url": row[2],
                "parte_label": row[3], "parte_nome": row[4], "classe": row[5], "resumo": row[6],
                "ultimo_andamento": row[7]
            })
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao buscar do {tribunal}: {e}")
    return lista

def get_processo_db(pid):
    """Pega os dados de 1 único processo pro Telegram responder aos botões"""
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo_inicial, ultimo_andamento FROM processos WHERE pid = ?", (pid,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0], "numero": row[1], "url": row[2], "tribunal": row[3],
                "parte_label": row[4], "parte_nome": row[5], "classe": row[6], "resumo": row[7],
                "ultimo_andamento": row[8]
            }
    except Exception as e:
        print(f"❌ Erro ao buscar o processo {pid}: {e}")
    return None

# ==========================================
# 4. INTELIGÊNCIA ARTIFICIAL - RESUMO EVOLUTIVO
# ==========================================
def atualizar_resumo_no_bd(pid, andamento_novo):
    """Faz a IA atualizar o resumo base automaticamente com a nova movimentação"""
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT resumo_inicial, numero FROM processos WHERE pid = ?", (pid,))
        row = cursor.fetchone()
        if not row: 
            conn.close()
            return
        resumo_atual, numero = row[0], row[1]
        
        prompt = (
            f"Você é um assistente jurídico encarregado de manter o resumo do processo {numero} atualizado.\n"
            f"Abaixo está o RESUMO ATUAL do caso e uma NOVA MOVIMENTAÇÃO que acabou de acontecer.\n"
            f"Sua tarefa é reescrever o resumo, incorporando a nova movimentação de forma concisa, "
            f"mantendo o histórico importante e atualizando o status do processo.\n\n"
            f"⚠️ REGRAS:\n"
            f"1. Use formatação HTML básica (<b>, <i>, <u>).\n"
            f"2. NUNCA use os símbolos '#', '*' ou '**'.\n"
            f"3. Seja muito conciso (máximo de 3 parágrafos).\n\n"
            f"--- RESUMO ATUAL:\n{resumo_atual}\n\n"
            f"--- NOVA MOVIMENTAÇÃO:\n{andamento_novo}"
        )
        
        analise = client.models.generate_content(model='models/gemini-3.1-flash-lite', contents=prompt)
        if analise:
            texto_novo = analise.text.replace("###", "").replace("##", "").replace("**", "")
            cursor.execute("UPDATE processos SET resumo_inicial = ? WHERE pid = ?", (texto_novo, pid))
            conn.commit()
            print(f"📝 [BD] Resumo Evolutivo do processo {pid} atualizado com sucesso pela IA!")
            
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao atualizar resumo evolutivo: {e}")

# ==========================================
# 5. CARTEIRO (ENVIO TELEGRAM CORTE RIGOROSO)
# ==========================================
def carteiro_worker():
    while True:
        t = fila_saida.get()
        if t is None: break
        try:
            p = t['proc']
            agora = time.strftime('%d/%m/%Y %H:%M')
            
            texto_bruto = t['conteudo']
            if len(texto_bruto) > 250:
                texto_bruto = texto_bruto[:250] + "...\n<i>[Texto cortado. Use os botões abaixo]</i>"
                
            texto_extraido_seguro = html.escape(texto_bruto)
            
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
            
            markup.row(btn_resumo, btn_ia)
            markup.row(btn_ctx)

            for chat in CHATS_ESPECTADORES:
                if t['img'] and os.path.exists(t['img']):
                    with open(t['img'], 'rb') as f:
                        bot.send_photo(chat, f, caption=texto_html, parse_mode="HTML", reply_markup=markup)
                else:
                    bot.send_message(chat, texto_html, parse_mode="HTML", reply_markup=markup)
                    
        except Exception as e:
            print(f"❌ Erro crítico no Carteiro ao tentar enviar pro Telegram: {e}")
            
        fila_saida.task_done()
        time.sleep(1)

# ==========================================
# 6. EXTRAÇÃO INTEGRAL DE TRIBUNAIS (SCRAPERS)
# ==========================================
def extrair_playwright(p_instance, id_nome, url):
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando TJRJ...")
        nav = p_instance.chromium.launch(
            headless=False, 
            args=[
                '--headless=new', '--disable-gpu', '--window-size=1920,1080',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        ctx = nav.new_context(
            viewport={'width': 1280, 'height': 1200},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        pag = ctx.new_page()
        
        try:
            pag.goto(url, timeout=60000, wait_until="domcontentloaded") 
            tabela = pag.locator("table:has(th:has-text('Data'))").first
            pag.wait_for_timeout(2000)
            tabela.scroll_into_view_if_needed()
            
            primeira_linha = tabela.locator("tr").nth(1)
            box = primeira_linha.bounding_box()
            print_path = f"print_{id_nome}.png"
            pag.screenshot(path=print_path, clip={'x': box['x'], 'y': box['y'] - 5, 'width': 650, 'height': 600})
            
            linhas = tabela.locator("tr").all()
            txt = "\n".join([l.inner_text().strip() for l in linhas[1:15]]) 
            return txt.strip(), print_path
            
        except Exception as e:
            print(f"   ❌ Erro ao extrair {id_nome}: {e}")
            try:
                pasta_atual = os.path.dirname(os.path.abspath(__file__))
                caminho_erro = os.path.join(pasta_atual, f"DEBUG_ERRO_{id_nome}.png")
                pag.screenshot(path=caminho_erro, full_page=True)
            except: pass
            return None, None
        finally: 
            nav.close()

def extrair_stf_stealth(id_nome, url):
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando STF...")
        driver = None
        try:
            options = uc.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--no-sandbox") 
            options.add_argument("--disable-dev-shm-usage") 
            
            driver = uc.Chrome(options=options, version_main=VERSAO_CHROME_VM) 
            driver.get(url)
            time.sleep(10)
            
            try:
                alvo = driver.find_element(By.CSS_SELECTOR, ".andamento-item, app-andamento")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", alvo)
                time.sleep(2)
            except: 
                driver.execute_script("window.scrollTo(0, 700)")
            
            print_path = f"print_{id_nome}.png"
            driver.save_screenshot(print_path)
            
            items = driver.find_elements(By.CSS_SELECTOR, ".andamento-item, .processo-detalhe-andamento tr")
            txt = "\n".join([i.text.strip() for i in items[:15] if len(i.text) > 10])
            return txt.strip(), print_path
            
        except Exception as e: 
            print(f"   ❌ Erro detalhado no STF ({id_nome}): {e}")
            return None, None
        finally:
            if driver: driver.quit()

def extrair_tse_stealth(id_nome, url, numero):
    print(f"   📡 {id_nome}: Acessando TSE...")
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.page_load_strategy = 'none' 
        driver = uc.Chrome(options=options, version_main=VERSAO_CHROME_VM)
        bot.send_message(ADMIN_ID, f"🔑 Resolva TSE: {numero}")
        driver.get(url)
        
        card_alvo = None
        tempo_limite = 300  
        tempo_inicial = time.time()
        
        print(f"      [!] Aguardando resolução do captcha na tela (limite 5 min)...")
        while time.time() - tempo_inicial < tempo_limite:
            try:
                cards = driver.find_elements(By.CLASS_NAME, "tramitacao-card")
                card_alvo = next((c for c in cards if "Movimentos" in c.text and "Documentos" not in c.text), None)
                if card_alvo:
                    if len(card_alvo.text.strip()) > 50:
                        print(f"      ✅ {id_nome}: Dados carregados após resolução do captcha!")
                        break
            except: pass
            time.sleep(3)
            
        if not card_alvo:
            print(f"      ❌ {id_nome}: Tempo esgotado aguardando resolução do captcha.")
            return None, None
            
        time.sleep(2)
        print_path = f"print_{id_nome}.png"
        card_alvo.screenshot(print_path)
        
        linhas = [l.strip() for l in card_alvo.text.split('\n') if len(l.strip()) > 3 and l.strip().lower() != "autorenew"]
        return "\n".join(linhas[:15]), print_path
    except Exception as e:
        print(f"   ❌ Erro ao extrair TSE ({id_nome}): {e}")
        return None, None
    finally:
        if driver:
            try: driver.quit()
            except: pass

# ==========================================
# 7. EVENTOS TELEGRAM & ROTEAMENTO COMPLETO
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def processar_clique_botao(call):
    if str(call.message.chat.id) not in CHATS_ESPECTADORES: return
    
    try: bot.answer_callback_query(call.id)
    except: pass

    try:
        partes = call.data.split('|')
        if len(partes) < 2: return
        
        acao, pid = partes[0], partes[1]
        proc = get_processo_db(pid)
        if not proc: 
            bot.send_message(call.message.chat.id, "⚠️ Processo não encontrado no banco de dados.")
            return

        if acao == "resumo":
            texto_resumo = proc.get("resumo", "⚠️ Resumo não cadastrado no banco.")
            bot.send_message(call.message.chat.id, texto_resumo, parse_mode="HTML")
            
        elif acao == "ia":
            bot.send_message(call.message.chat.id, f"🔍 <b>IA</b> processando histórico de {pid}...", parse_mode="HTML")
            threading.Thread(target=tarefa_ia_resumo, args=(call.message, pid, proc)).start()

        elif acao == "ctx":
            msg_pergunta = bot.send_message(
                call.message.chat.id, 
                f"📝 <b>Novo Contexto para {pid}:</b>\n"
                f"Digite ou cole abaixo o resumo da petição ou despacho para guardar na memória e refazer a análise:", 
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg_pergunta, processar_texto_humano, pid, proc)

    except Exception as e:
        print(f"⚠️ Erro ao processar clique: {e}")

def processar_texto_humano(message, pid, proc):
    if not message.text:
        bot.send_message(message.chat.id, "⚠️ Digite um texto válido para adicionar ao contexto.")
        return
        
    contexto_humano = message.text
    agora = time.strftime('%d/%m/%Y %H:%M')
    
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historico_contexto (pid, data_hora, texto) VALUES (?, ?, ?)", 
                       (pid, agora, contexto_humano))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao salvar linha do tempo no SQLite: {e}")

    bot.send_message(message.chat.id, f"🧠 Memória atualizada! Refazendo análise com histórico completo...", parse_mode="HTML")
    proc_atualizado = get_processo_db(pid)
    threading.Thread(target=tarefa_ia_resumo, args=(message, pid, proc_atualizado)).start()

def tarefa_ia_resumo(message, pid, proc):
    try:
        andamentos_recentes = proc.get("ultimo_andamento")
        if not andamentos_recentes:
            bot.send_message(message.chat.id, "⚠️ Sem dados de andamentos no banco para análise.")
            return

        resumo_base = proc.get("resumo", "Contexto base não fornecido.")
        historico_humano_texto = ""
        try:
            conn = sqlite3.connect('memoria_vigilante.db')
            cursor = conn.cursor()
            cursor.execute("SELECT data_hora, texto FROM historico_contexto WHERE pid = ? ORDER BY id ASC", (pid,))
            registros = cursor.fetchall()
            conn.close()
            
            if registros:
                historico_humano_texto = "\n\n--- 🧠 MEMÓRIA DO ADVOGADO (Interações Anteriores):\n"
                for reg in registros:
                    historico_humano_texto += f"[{reg[0]}] Nota: {reg[1]}\n"
        except Exception as e:
            print(f"❌ Erro ao ler histórico de conversas do BD: {e}")

        modelos_tentativa = ['models/gemini-3.1-flash-lite', 'models/gemini-flash-latest']
        
        instrucao_extra = ""
        if historico_humano_texto:
            instrucao_extra = (
                "O advogado responsável adicionou NOTAS e ATUALIZAÇÕES na seção 'MEMÓRIA DO ADVOGADO'. "
                "Considere essa linha do tempo para guiar seu raciocínio estratégico."
            )

        prompt = (
            f"Você é um consultor jurídico sênior auxiliando um advogado experiente. "
            f"Analise o processo {proc['numero']}.\n"
            "Sua tarefa é cruzar o CONTEXTO BASE da ação com os ANDAMENTOS RECENTES do tribunal, "
            "explicando como as novidades impactam a tese fundamental do caso.\n"
            f"{instrucao_extra}\n\n"
            "⚠️ REGRAS ESTRITAS DE FORMATAÇÃO:\n"
            "1. NUNCA use os símbolos '#' ou '*' ou '**' na sua resposta.\n"
            "2. Seja direto, técnico e focado na estratégia processual.\n"
            "3. Estruture a resposta EXATAMENTE com estes 3 tópicos, usando os emojis:\n\n"
            "📌 STATUS ATUAL: (Sintetize a evolução do caso cruzando a base com a novidade)\n\n"
            "⚖️ PONTOS DE ATENÇÃO:\n"
            "- (Item 1 crítico dos andamentos)\n"
            "- (Item 2 crítico dos andamentos)\n\n"
            "💡 RECOMENDAÇÃO: (Qual a próxima peça ou atitude estratégica a tomar)\n\n"
            f"--- CONTEXTO BASE DO PROCESSO:\n{resumo_base}\n\n"
            f"--- ANDAMENTOS RECENTES CAPTURADOS:\n{andamentos_recentes}"
            f"{historico_humano_texto}"
        )
        
        analise = None
        for m in modelos_tentativa:
            try:
                analise = client.models.generate_content(model=m, contents=prompt)
                if analise: break
            except: continue

        if not analise:
            bot.send_message(message.chat.id, "🛑 Servidores Google ocupados.")
            return

        texto_limpo = analise.text.replace("###", "").replace("##", "").replace("**", "")
        tag_analise = "🧠 ANÁLISE INTERATIVA COMPLETA" if historico_humano_texto else "🧠 ANÁLISE ESTRATÉGICA"
        
        mensagem_final = (
            f"🏛 <b>{tag_analise} - {pid}</b>\n"
            f"<code>{proc['numero']}</code>\n"
            f"----------------------------------------\n\n"
            f"{texto_limpo}"
        )
        bot.send_message(message.chat.id, mensagem_final, parse_mode="HTML")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro Crítico na IA: {e}")

def listar_processos_telegram(message):
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT pid, tribunal, numero, classe FROM processos ORDER BY tribunal, pid")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            bot.send_message(message.chat.id, "📭 Nenhum processo cadastrado no banco de dados.")
            return
            
        texto = "📋 <b>PROCESSOS MONITORADOS:</b>\n\n"
        for r in rows:
            texto += f"🔹 <b>{r[0]}</b> ({r[1]})\n"
            texto += f"   Número: <code>{r[2]}</code>\n"
            texto += f"   Classe: {r[3]}\n\n"
            
        bot.send_message(message.chat.id, texto, parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro ao listar processos: {e}")

def remover_processo_telegram(message, pid):
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT pid FROM processos WHERE pid = ?", (pid,))
        if not cursor.fetchone():
            bot.send_message(message.chat.id, f"❌ ID {pid} não encontrado no banco de dados.")
            conn.close()
            return
            
        cursor.execute("DELETE FROM processos WHERE pid = ?", (pid,))
        cursor.execute("DELETE FROM historico_contexto WHERE pid = ?", (pid,))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ Processo <b>{pid}</b> e seu histórico foram removidos com sucesso!", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro ao remover processo: {e}")

def iniciar_cadastro_processo(message):
    bot.send_message(
        message.chat.id,
        "✍️ <b>Cadastro de Novo Processo:</b>\n\n"
        "Para cancelar a qualquer momento, digite 'cancelar'.\n\n"
        "1. Qual o **Tribunal**? (Responda exatamente TJRJ, STF ou TSE)",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, obter_tribunal)

def obter_tribunal(message):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    tribunal = message.text.upper().strip()
    if tribunal not in ["TJRJ", "STF", "TSE"]:
        msg = bot.reply_to(message, "⚠️ Tribunal inválido. Digite TJRJ, STF ou TSE:")
        bot.register_next_step_handler(msg, obter_tribunal)
        return
    
    bot.send_message(message.chat.id, f"Tribunal definido: {tribunal}\n\n2. Digite um **ID único** para o processo (Ex: TJRJ_5, STF_4):")
    bot.register_next_step_handler(message, obter_pid, tribunal)

def obter_pid(message, tribunal):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    pid = message.text.upper().strip()
    
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        cursor.execute("SELECT pid FROM processos WHERE pid = ?", (pid,))
        existe = cursor.fetchone()
        conn.close()
        if existe:
            msg = bot.reply_to(message, f"⚠️ O ID {pid} já está cadastrado. Digite um ID diferente:")
            bot.register_next_step_handler(msg, obter_pid, tribunal)
            return
    except Exception as e:
        print(f"Erro ao verificar ID: {e}")
        
    bot.send_message(message.chat.id, f"ID definido: {pid}\n\n3. Digite o **Número do Processo** (Ex: 3004566-28.2026.8.19.0000):")
    bot.register_next_step_handler(message, obter_numero, tribunal, pid)

def obter_numero(message, tribunal, pid):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    numero = message.text.strip()
    bot.send_message(message.chat.id, f"Número definido: {numero}\n\n4. Digite a **URL de Consulta** do processo:")
    bot.register_next_step_handler(message, obter_url, tribunal, pid, numero)

def obter_url(message, tribunal, pid, numero):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    url = message.text.strip()
    bot.send_message(message.chat.id, f"URL definida: {url}\n\n5. Digite a **Classe Processual** (Ex: Mandado de Segurança Cível):")
    bot.register_next_step_handler(message, obter_classe, tribunal, pid, numero, url)

def obter_classe(message, tribunal, pid, numero, url):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    classe = message.text.strip()
    bot.send_message(message.chat.id, f"Classe definida: {classe}\n\n6. Digite o **Rótulo da Parte** (Ex: Impetrante, Requerente):")
    bot.register_next_step_handler(message, obter_parte_label, tribunal, pid, numero, url, classe)

def obter_parte_label(message, tribunal, pid, numero, url, classe):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    parte_label = message.text.strip()
    bot.send_message(message.chat.id, f"Rótulo definido: {parte_label}\n\n7. Digite o **Nome da Parte** (Ex: PDT DIRETÓRIO RJ):")
    bot.register_next_step_handler(message, obter_parte_nome, tribunal, pid, numero, url, classe, parte_label)

def obter_parte_nome(message, tribunal, pid, numero, url, classe, parte_label):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    parte_nome = message.text.strip()
    bot.send_message(message.chat.id, f"Nome da parte definido: {parte_nome}\n\n8. Digite o **Resumo Base Inicial** do processo:")
    bot.register_next_step_handler(message, obter_resumo, tribunal, pid, numero, url, classe, parte_label, parte_nome)

def obter_resumo(message, tribunal, pid, numero, url, classe, parte_label, parte_nome):
    if message.text.lower() == 'cancelar':
        bot.send_message(message.chat.id, "❌ Cadastro cancelado.")
        return
    resumo = message.text.strip()
    
    try:
        conn = sqlite3.connect('memoria_vigilante.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO processos (pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo_inicial)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo))
        conn.commit()
        conn.close()
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>Processo cadastrado com sucesso!</b>\n\n"
            f"📌 <b>ID:</b> {pid}\n"
            f"🏛 <b>Tribunal:</b> {tribunal}\n"
            f"⚖️ <b>Número:</b> {numero}",
            parse_mode="HTML"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro ao salvar processo no banco: {e}")

@bot.message_handler(commands=['resumo', 'ia', 'listar', 'remover', 'adicionar'])
def comandos_digitados(message):
    if str(message.chat.id) not in CHATS_ESPECTADORES: return
    try:
        partes = message.text.split()
        comando = partes[0].lower()
        
        if "/listar" in comando:
            listar_processos_telegram(message)
            return
            
        if "/adicionar" in comando:
            iniciar_cadastro_processo(message)
            return

        if len(partes) < 2:
            bot.reply_to(message, "⚠️ Use: /resumo ID, /ia ID ou /remover ID")
            return
            
        pid = partes[1].upper()
        
        if "/remover" in comando:
            remover_processo_telegram(message, pid)
            return
            
        proc = get_processo_db(pid)
        if not proc:
            bot.reply_to(message, f"❌ ID {pid} não encontrado no banco de dados.")
            return

        if "/resumo" in comando:
            texto_resumo = proc.get("resumo", "⚠️ Resumo manual não cadastrado.")
            bot.send_message(message.chat.id, f"📖 <b>Resumo do BD ({pid}):</b>\n\n{texto_resumo}", parse_mode="HTML")
            
        elif "/ia" in comando:
            bot.send_message(message.chat.id, f"🔍 <b>IA</b> processando histórico de {pid}...", parse_mode="HTML")
            threading.Thread(target=tarefa_ia_resumo, args=(message, pid, proc)).start()
            
    except Exception as e:
        print(f"Erro no comando: {e}")
        bot.reply_to(message, "⚠️ Ocorreu um erro ao processar o comando.")

# ==========================================
# 8. MOTOR DE MONITORAMENTO PRINCIPAL
# ==========================================
FALHAS_CONSECUTIVAS = {}

def comparar_e_enfileirar(proc, tribunal, txt, img):
    pid = proc['id']
    if not txt:
        print(f"      ❌ {pid}: Falha na leitura.")
        FALHAS_CONSECUTIVAS[pid] = FALHAS_CONSECUTIVAS.get(pid, 0) + 1
        if FALHAS_CONSECUTIVAS[pid] == 5:
            msg = (
                f"⚠️ <b>ALERTA DE CAPTURA ({tribunal})</b>\n\n"
                f"O processo <code>{proc['numero']}</code> ({pid}) falhou ao ser capturado por 5 ciclos consecutivos.\n"
                f"O layout do site pode ter mudado ou o serviço está instável."
            )
            try: bot.send_message(ADMIN_ID, msg, parse_mode="HTML")
            except: pass
        return
    
    FALHAS_CONSECUTIVAS[pid] = 0
    print(f"   🔍 {pid}: Comparando histórico...")
    txt_novo = txt.strip()
    
    txt_antigo = proc.get("ultimo_andamento")
    if txt_antigo:
        txt_antigo = txt_antigo.strip()
    
    if not txt_antigo:
        try:
            conn = sqlite3.connect('memoria_vigilante.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE processos SET ultimo_andamento = ? WHERE pid = ?", (txt_novo, pid))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao atualizar estado inicial no SQLite: {e}")
        print(f"      📁 {pid}: Base inicial salva no Banco de Dados.")
        return

    if txt_novo != txt_antigo:
        print(f"      🚨 {pid}: MUDANÇA DETECTADA!")
        
        threading.Thread(target=atualizar_resumo_no_bd, args=(pid, txt_novo)).start()
        fila_saida.put({"tribunal": tribunal, "conteudo": txt_novo, "proc": proc, "img": img})
        
        try:
            conn = sqlite3.connect('memoria_vigilante.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE processos SET ultimo_andamento = ? WHERE pid = ?", (txt_novo, pid))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao atualizar novo estado no SQLite: {e}")
    else:
        print(f"      ✅ {pid}: Sem novidades.")

def iniciar_vigilancia():
    print("🚀 Vigilante Master v14.0 Inicializando...")
    
    inicializar_banco()
    
    try:
        bot.send_message(ADMIN_ID, "🚀 <b>Vigilante Master v14.0 Online!</b>\nBanco de Dados, IA Evolutiva e Painel Web Ativados.", parse_mode="HTML")
    except: pass
    
    # Inicialização das Threads paralelas de infraestrutura (Telegram e Webserver)
    threading.Thread(target=carteiro_worker, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True), daemon=True).start()
    threading.Thread(target=iniciar_servidor_web, daemon=True).start()
    
    cnt = 0
    while True:
        print(f"\n--- CICLO #{cnt} | {time.strftime('%H:%M:%S')} ---")
        exterminar_zumbis()
        
        processos_tjrj = buscar_processos_do_bd("TJRJ")
        processos_stf = buscar_processos_do_bd("STF")
        processos_tse = buscar_processos_do_bd("TSE")
        
        with sync_playwright() as p:
            for pr in processos_tjrj:
                t, i = extrair_playwright(p, pr['id'], pr['url'])
                comparar_e_enfileirar(pr, "TJRJ", t, i)

        for pr in processos_stf:
            t, i = extrair_stf_stealth(pr['id'], pr['url'])
            comparar_e_enfileirar(pr, "STF", t, i)

        if cnt % 10 == 0:
            def rodar_tse_sequencial(lista_processos):
                for pr in lista_processos:
                    t, i = extrair_tse_stealth(pr['id'], pr['url'], pr['numero'])
                    comparar_e_enfileirar(pr, "TSE", t, i)
                    time.sleep(5)
            
            threading.Thread(target=rodar_tse_sequencial, args=(processos_tse,), daemon=True).start()

        print(f"✅ Ciclo finalizado. Dormindo 2 min...")
        time.sleep(120)
        cnt += 1

# ==========================================
# INÍCIO DO PROGRAMA COM AIRBAG GLOBAL
# ==========================================
if __name__ == "__main__":
    try:
        iniciar_vigilancia()
        
    except Exception as e:
        erro_str = str(e)
        erro_trace = traceback.format_exc()
        
        erro_str_curto = erro_str[:400] + " [...]" if len(erro_str) > 400 else erro_str
        erro_trace_curto = erro_trace[-1000:] if len(erro_trace) > 1000 else erro_trace
        
        erro_motivo_limpo = html.escape(erro_str_curto)
        erro_resumo_limpo = html.escape(erro_trace_curto)
        
        mensagem_alerta = (
            "🚨 <b>VIGILANTE MASTER CAIU!</b> 🚨\n\n"
            "A Máquina Virtual encontrou um Erro Fatal e o script foi interrompido.\n\n"
            f"<b>Motivo:</b> {erro_motivo_limpo}\n\n"
            "<b>Log:</b>\n"
            f"<code>{erro_resumo_limpo}</code>\n\n"
            "⚠️ <i>Acesse a VM para reiniciar o sistema.</i>"
        )
        
        try:
            bot.send_message(ADMIN_ID, mensagem_alerta, parse_mode="HTML")
            print("🚨 Alerta de CRASH enviado com sucesso para o Telegram!")
        except Exception as e_telegram:
            print(f"❌ Falha fatal ao avisar no Telegram. Erro: {e_telegram}")