import os
import time
import threading
import queue
import ssl
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton # <--- NOVA IMPORTAÇÃO PARA OS BOTÕES
from google import genai
from playwright.sync_api import sync_playwright
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import html
import traceback
from dotenv import load_dotenv

load_dotenv()


def exterminar_zumbis():
    """Força o Windows da VM a matar qualquer Chrome fantasma travado na memória"""
    try:
        import os, time
        os.system("taskkill /f /im chrome.exe /t >nul 2>&1")
        os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
        time.sleep(2) # Dá 2 segundos para o processador da VM respirar
    except:
        pass

# ==========================================
# 🛡️ CONFIGURAÇÕES, SSL E VERSÃO
# ==========================================
ssl._create_default_https_context = ssl._create_unverified_context
lock_navegador = threading.Lock() 
ia_lock = threading.Lock() # <--- NOVA CATRACA PARA A API DO GOOGLE 
VERSAO_CHROME_VM = 147 

TOKEN_TELEGRAM     = os.getenv("TOKEN_TELEGRAM")
ADMIN_ID           = os.getenv("ADMIN_ID")
CHATS_ESPECTADORES = os.getenv("CHATS_ESPECTADORES", "").split(",")
API_KEY_GEMINI     = os.getenv("API_KEY_GEMINI")
client = genai.Client(api_key=API_KEY_GEMINI)

bot = telebot.TeleBot(TOKEN_TELEGRAM)
fila_saida = queue.Queue() 

# ==========================================
# 1. PROCESSOS COM RESUMO MANUAL (HTML)
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
        "resumo": "🗳️ <b>RESUMO TSE_1:</b>\n\n<b>Cerne:</b> Recurso sobre as eleições de 2022 acusando a chapa de Cláudio Castro de conduta vedada a agente público.\n<b>Última Decisão:</b> Acórdão proferido em 23/04/2026. A defesa opôs Embargos de Declaração.\n<b>Status:</b> Publicação de intimações em andamento. Aguarda julgamento dos Embargos pela Min. Isabel Gallotti."
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
# 2. CARTEIRO COM BOTÕES INLINE E LIMITADOR RIGOROSO (250 CHARS)
# ==========================================
def carteiro_worker():
    while True:
        t = fila_saida.get()
        if t is None: break
        try:
            p = t['proc']
            agora = time.strftime('%d/%m/%Y %H:%M')
            
            # 👇 CORTE MAIS RIGOROSO: 250 caracteres garante que os links enormes do TJRJ não estourem o limite de 1024
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
# 3. EXTRAÇÃO (LÓGICA ORIGINAL 8.2)
# ==========================================
def extrair_playwright(p_instance, id_nome, url):
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando TJRJ...")
        
        nav = p_instance.chromium.launch(
            headless=False, 
            args=[
                '--headless=new', 
                '--disable-gpu',
                '--window-size=1920,1080',
                '--disable-blink-features=AutomationControlled' # Oculta a flag de automação nativa
            ]
        )
        
        # 👇 MÁSCARA 1: Falsificando a identidade do Navegador (User-Agent real)
        ctx = nav.new_context(
            viewport={'width': 1280, 'height': 1200},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        
        # 👇 MÁSCARA 2: Apagando a variável que grita "EU SOU UM ROBÔ" pro TJRJ
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
                import os
                # Força o caminho absoluto na pasta do seu script
                pasta_atual = os.path.dirname(os.path.abspath(__file__))
                caminho_erro = os.path.join(pasta_atual, f"DEBUG_ERRO_{id_nome}.png")
                
                pag.screenshot(path=caminho_erro, full_page=True)
                print(f"   📸 Foto do bloqueio salva EXATAMENTE em: {caminho_erro}")
            except Exception as e_foto:
                print(f"   ❌ Falha até pra tirar foto: {e_foto}")
            return None, None
            
        finally: 
            nav.close()

def extrair_stf_stealth(id_nome, url):
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando STF...")
        driver = None
        try:
            options = uc.ChromeOptions()
            # 👇 O DISFARCE E A PROTEÇÃO DA VM
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--no-sandbox") # <--- Essencial para rodar liso em VM
            options.add_argument("--disable-dev-shm-usage") # <--- Evita estouro de memória RAM
            
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
            # 👇 O RASTREADOR: Se der erro, agora o Python vai "gritar" o motivo
            print(f"   ❌ Erro detalhado no STF ({id_nome}): {e}")
            return None, None
            
        finally:
            if driver: driver.quit()

def extrair_tse_stealth(id_nome, url, numero):
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando TSE...")
        driver = None
        try:
            options = uc.ChromeOptions()
            options.add_argument("--disable-gpu")
            options.page_load_strategy = 'none' 
            driver = uc.Chrome(options=options, version_main=VERSAO_CHROME_VM)
            bot.send_message(ADMIN_ID, f"🔑 Resolva TSE: {numero}")
            driver.get(url)
            input(f"      [!] Resolva o TSE e aperte ENTER...")
            time.sleep(4)
            
            cards = driver.find_elements(By.CLASS_NAME, "tramitacao-card")
            card_alvo = next((c for c in cards if "Movimentos" in c.text and "Documentos" not in c.text), None)
            if not card_alvo: return None, None
            
            print_path = f"print_{id_nome}.png"
            card_alvo.screenshot(print_path)
            
            linhas = [l.strip() for l in card_alvo.text.split('\n') if len(l.strip()) > 3 and l.strip().lower() != "autorenew"]
            return "\n".join(linhas[:15]), print_path
        except: return None, None
        finally:
            if driver: driver.quit()

# ==========================================
# 4. RECEBEDOR DE CLIQUES (FIX: RESPOSTA IMEDIATA E FIM DO TIMEOUT)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def processar_clique_botao(call):
    if str(call.message.chat.id) not in CHATS_ESPECTADORES: return
    
    # 👇 AJUSTE VITAL: Responde ao Telegram NA HORA para o ID do botão não expirar
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    try:
        partes = call.data.split('|')
        if len(partes) < 2: return
        
        acao, pid = partes[0], partes[1]
        proc = next((p for p in PROCESSOS_TJRJ+PROCESSOS_STF+PROCESSOS_TSE if p['id'] == pid), None)
        
        if not proc: return

        # 👇 Faltava este IF aqui!
        if acao == "resumo":
            texto_resumo = proc.get("resumo", "⚠️ Resumo manual não cadastrado.")
            bot.send_message(call.message.chat.id, texto_resumo, parse_mode="HTML")
            
        elif acao == "ia":
            bot.send_message(call.message.chat.id, f"🔍 <b>IA</b> processando histórico de {pid}...", parse_mode="HTML")
            threading.Thread(target=tarefa_ia_resumo, args=(call.message, pid, proc)).start()

        elif acao == "ctx":
            msg_pergunta = bot.send_message(
                call.message.chat.id, 
                f"📝 <b>Novo Contexto para {pid}:</b>\n"
                f"Digite ou cole abaixo o resumo do despacho, decisão ou petição que você acabou de ler para eu refazer a análise:", 
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg_pergunta, processar_texto_humano, pid, proc)

    except Exception as e:
        print(f"⚠️ Erro ao processar clique: {e}")

# ==========================================
# 4. TAREFA IA E COMANDOS (VERSÃO UI PREMIUM)
# ==========================================

# 👇 NOVA FUNÇÃO: Pega o seu texto do Telegram e manda pra IA
def processar_texto_humano(message, pid, proc):
    if not message.text:
        bot.send_message(message.chat.id, "⚠️ Eu preciso de um texto para adicionar ao contexto. Tente novamente clicando no botão.")
        return
        
    contexto_humano = message.text
    bot.send_message(message.chat.id, f"🧠 Refazendo a análise de {pid} com as suas observações profissionais...", parse_mode="HTML")
    
    # Chama a mesma IA, mas agora passando o seu texto extra
    threading.Thread(target=tarefa_ia_resumo, args=(message, pid, proc, contexto_humano)).start()

# ==========================================

# 👇 FUNÇÃO DE IA ATUALIZADA (Agora com parâmetro opcional 'contexto_humano')
def tarefa_ia_resumo(message, pid, proc, contexto_humano=None):
    try:
        arq = f"estado_{pid}.txt"
        if not os.path.exists(arq):
            bot.send_message(message.chat.id, "⚠️ Sem dados locais para análise.")
            return

        with open(arq, "r", encoding="utf-8") as f:
            historico = f.read()

        resumo_base = proc.get("resumo", "Contexto base não fornecido no script.")

        modelos_tentativa = ['models/gemini-3.1-flash-lite', 'models/gemini-flash-latest']
        
        # 👇 Lógica Dinâmica do Prompt
        instrucao_extra = ""
        bloco_extra = ""
        
        if contexto_humano:
            instrucao_extra = "O advogado responsável acabou de analisar os autos e trouxe INFORMAÇÕES NOVAS vitais. Incorpore essas informações na sua análise de impacto."
            bloco_extra = f"\n\n--- 🚨 NOVA INFORMAÇÃO DO ADVOGADO (Despacho/Petição):\n{contexto_humano}"

        prompt = (
            f"Você é um consultor jurídico sênior auxiliando um advogado experiente. "
            f"Analise o processo {proc['numero']}.\n"
            "Sua tarefa é cruzar o CONTEXTO BASE da ação com os ANDAMENTOS RECENTES, "
            "explicando como as novidades impactam a tese fundamental do caso.\n"
            f"{instrucao_extra}\n\n"
            "⚠️ REGRAS ESTRITAS DE FORMATAÇÃO (Obrigatório):\n"
            "1. NUNCA use os símbolos '#' ou '*' ou '**' na sua resposta.\n"
            "2. Seja direto, técnico e focado na estratégia processual.\n"
            "3. Estruture a resposta EXATAMENTE com estes 3 tópicos, usando os emojis:\n\n"
            "📌 STATUS ATUAL: (Sintetize a evolução do caso cruzando a base com a novidade)\n\n"
            "⚖️ PONTOS DE ATENÇÃO:\n"
            "- (Item 1 crítico dos andamentos)\n"
            "- (Item 2 crítico dos andamentos)\n\n"
            "💡 RECOMENDAÇÃO: (Qual a próxima peça ou atitude estratégica a tomar)\n\n"
            f"--- CONTEXTO BASE DO PROCESSO (A tese inicial):\n{resumo_base}\n\n"
            f"--- ANDAMENTOS RECENTES CAPTURADOS (As novidades):\n{historico}"
            f"{bloco_extra}" # Injeta o que você digitou aqui no final
        )
        
        analise = None
        for m in modelos_tentativa:
            try:
                analise = client.models.generate_content(model=m, contents=prompt)
                if analise: break
            except:
                continue

        if not analise:
            bot.send_message(message.chat.id, "🛑 <b>Servidores Google Ocupados:</b> Tente em alguns segundos.")
            return

        texto_limpo = analise.text.replace("###", "").replace("##", "").replace("**", "")
        
        # Tag visual pra você saber se a IA leu seu contexto ou fez a análise padrão
        tag_analise = "🧠 ANÁLISE ESTRATÉGICA" if not contexto_humano else "🧠 ANÁLISE COM NOVO CONTEXTO"
        
        mensagem_final = (
            f"🏛 <b>{tag_analise} - {pid}</b>\n"
            f"<code>{proc['numero']}</code>\n"
            f"----------------------------------------\n\n"
            f"{texto_limpo}"
        )
        
        bot.send_message(message.chat.id, mensagem_final, parse_mode="HTML")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro Crítico na IA: {e}")
# Comandos manuais para redundância
@bot.message_handler(commands=['resumo', 'ia'])
def comandos_digitados(message):
    if str(message.chat.id) not in CHATS_ESPECTADORES: return
    try:
        partes = message.text.split()
        if len(partes) < 2:
            bot.reply_to(message, "⚠️ Use: /resumo ID ou /ia ID")
            return
            
        comando = partes[0].lower()
        pid = partes[1].upper()
        
        proc = next((p for p in PROCESSOS_TJRJ+PROCESSOS_STF+PROCESSOS_TSE if p['id'] == pid), None)
        
        if not proc:
            bot.reply_to(message, f"❌ ID {pid} não encontrado na base.")
            return

        if "/resumo" in comando:
            texto_resumo = proc.get("resumo", "⚠️ Resumo manual não cadastrado.")
            bot.send_message(message.chat.id, f"📖 <b>Resumo Cadastrado ({pid}):</b>\n\n{texto_resumo}", parse_mode="HTML")
            
        elif "/ia" in comando:
            bot.send_message(message.chat.id, f"🔍 <b>IA</b> processando histórico de {pid}...", parse_mode="HTML")
            threading.Thread(target=tarefa_ia_resumo, args=(message, pid, proc)).start()
            
    except Exception as e:
        print(f"Erro no comando: {e}")
        bot.reply_to(message, "⚠️ Ocorreu um erro ao processar o comando.")

# ==========================================
# 5. MOTOR DE MONITORAMENTO E LOGS 8.2
# ==========================================
def comparar_e_enfileirar(proc, tribunal, txt, img):
    if not txt:
        print(f"      ❌ {proc['id']}: Falha na leitura.")
        return
    
    print(f"   🔍 {proc['id']}: Comparando histórico...")
    arq = f"estado_{proc['id']}.txt"
    txt_novo = txt.strip()
    
    if not os.path.exists(arq):
        with open(arq, "w", encoding="utf-8") as f: f.write(txt_novo)
        print(f"      📁 {proc['id']}: Base inicial salva.")
        return

    with open(arq, "r", encoding="utf-8") as f:
        txt_antigo = f.read().strip()

    if txt_novo != txt_antigo:
        print(f"      🚨 {proc['id']}: MUDANÇA DETECTADA!")
        fila_saida.put({"tribunal": tribunal, "conteudo": txt_novo, "proc": proc, "img": img})
        with open(arq, "w", encoding="utf-8") as f: f.write(txt_novo)
    else:
        print(f"      ✅ {proc['id']}: Sem novidades.")

def iniciar_vigilancia():
    print("🚀 Vigilante v12.2 Iniciado!")
    try:
        bot.send_message(ADMIN_ID, "🚀 <b>Vigilante Master v12.2 Online!</b>\nPainel Interativo e Mutex Ativados.", parse_mode="HTML")
    except: pass
    
    threading.Thread(target=carteiro_worker, daemon=True).start()
    
    # 👇 A MÁGICA DA FAXINA DO TELEGRAM
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True), daemon=True).start()
    
    cnt = 0
    while True:
        print(f"\n--- CICLO #{cnt} | {time.strftime('%H:%M:%S')} ---")
        
        # 👇 A MÁGICA DA FAXINA DE MEMÓRIA (Mata os zumbis antes de começar!)
        exterminar_zumbis()
        
        with sync_playwright() as p:
            for pr in PROCESSOS_TJRJ:
                t, i = extrair_playwright(p, pr['id'], pr['url'])
                comparar_e_enfileirar(pr, "TJRJ", t, i)

        for pr in PROCESSOS_STF:
            t, i = extrair_stf_stealth(pr['id'], pr['url'])
            comparar_e_enfileirar(pr, "STF", t, i)

        if cnt % 10 == 0:
            for pr in PROCESSOS_TSE:
                t, i = extrair_tse_stealth(pr['id'], pr['url'], pr['numero'])
                comparar_e_enfileirar(pr, "TSE", t, i)

        print(f"✅ Ciclo finalizado. Dormindo 2 min...")
        time.sleep(120)
        cnt += 1

# ==========================================
# INÍCIO DO PROGRAMA COM AIRBAG GLOBAL
# ==========================================
if __name__ == "__main__":
    import traceback
    import html

    try:
        iniciar_vigilancia()
        
    except Exception as e:
        # Pega o erro puro
        erro_str = str(e)
        erro_trace = traceback.format_exc()
        
        # 👇 A GUILHOTINA: Corta sem dó para caber no limite de 4096 do Telegram
        erro_str_curto = erro_str[:400] + " [...]" if len(erro_str) > 400 else erro_str
        erro_trace_curto = erro_trace[-1000:] if len(erro_trace) > 1000 else erro_trace
        
        # Limpa as tags pro Telegram não chorar
        erro_motivo_limpo = html.escape(erro_str_curto)
        erro_resumo_limpo = html.escape(erro_trace_curto)
        
        mensagem_alerta = (
            "🚨 <b>VIGILANTE MASTER CAIU!</b> 🚨\n\n"
            "A Máquina Virtual encontrou um Erro Fatal e o script foi aainterrompido.\n\n"
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