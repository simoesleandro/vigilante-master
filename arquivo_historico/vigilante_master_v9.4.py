import os
import time
import threading
import queue
import ssl
import telebot
from google import genai
from playwright.sync_api import sync_playwright
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

load_dotenv()
# ==========================================
# 1. CONFIGURAÇÕES 
# ==========================================
TOKEN_TELEGRAM     = os.getenv("TOKEN_TELEGRAM")
ADMIN_ID           = os.getenv("ADMIN_ID")
CHATS_ESPECTADORES = os.getenv("CHATS_ESPECTADORES", "").split(",")
API_KEY_GEMINI     = os.getenv("API_KEY_GEMINI")"
client = genai.Client(api_key=API_KEY_GEMINI)

bot = telebot.TeleBot(TOKEN_TELEGRAM)
fila_saida = queue.Queue() 

PROCESSOS_TJRJ = [
    {"id": "TJRJ_1", "numero": "3004566-28.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_nome_parte_publica&acao_retorno=processo_consulta_nome_parte_publica&num_processo=30045662820268190000&num_chave=&hash=b33f48b0cc0ad69e5cd182e3751fd64e&num_chave_documento=", "parte_label": "Impetrante", "parte_nome": "PDT - PARTIDO DEMOCRÁTICO TRABALHISTA DIRETÓRIO RJ", "classe": "Mandado de Segurança Cível (Órgão Especial)"},
    {"id": "TJRJ_2", "numero": "3004326-39.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30043263920268190000&num_chave=&num_chave_documento=&hash=2ad7164906ea016a598e771470c6a7fb", "parte_label": "Impetrante", "parte_nome": "LUIZ PAULO CORRÊA DA ROCHA", "classe": "Mandado de Segurança Cível (Órgão Especial)"},
    {"id": "TJRJ_3", "numero": "3004629-53.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30046295320268190000&num_chave=&num_chave_documento=&hash=85afa7fb1115618798dc54ecb979febd", "parte_label": "Impetrante", "parte_nome": "LUIZ PAULO CORRÊA DA ROCHA", "classe": "Mandado de Segurança Cível (Órgão Especial)"},
    {"id": "TJRJ_4", "numero": "3006257-77.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30062577720268190000&num_chave=&num_chave_documento=&hash=da8242e844340fbe2106c1a341df9b82", "parte_label": "Requerente", "parte_nome": "PARTIDO DEMOCRÁTICO TRABALHISTA", "classe": "Tutela Cautelar Antecedente (Órgão Especial)"}
]

PROCESSOS_STF = [
    {"id": "STF_1", "numero": "ADI 7942", "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7531465", "parte_label": "Impetrante", "parte_nome": "PARTIDO SOCIAL DEMOCRÁTICO - PSD DIRETÓRIO NACIONAL", "classe": "Ação Direta de Inconstitucionalidade"},
    {"id": "STF_2", "numero": "RLC 92644", "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7547470", "parte_label": "Reclamante", "parte_nome": "DIRETÓRIO ESTADUAL DO PARTIDO SOCIAL DEMOCRÁTICO DO RIO DE JANEIRO - PSD/RJ", "classe": "Reclamação"},
    {"id": "STF_3", "numero": "ADPF 1319", "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7569263", "parte_label": "Requerente", "parte_nome": "PARTIDO DEMOCRÁTICO TRABALHISTA – PDT", "classe": "Arguição de Descumprimento de Preceito Fundamental"}
]

PROCESSOS_TSE = [
    {"id": "TSE_1", "numero": "0603507-14.2022.6.19.0000", "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0603507-14.2022.6.19.0000", "parte_label": "Recorrente", "parte_nome": "COLIGAÇÃO A VIDA VAI MELHORAR / MARCELO RIBEIRO FREIXO", "classe": "Recurso Ordinário Eleitoral"},
    {"id": "TSE_2", "numero": "0606570-47.2022.6.19.0000", "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0606570-47.2022.6.19.0000", "parte_label": "Recorrente", "parte_nome": "MINISTÉRIO PÚBLICO ELEITORAL", "classe": "Recurso Ordinário Eleitoral"}
]

# ==========================================
# 2. CARTEIRO (ENVIO ASYNC - LAYOUT 8.2)
# ==========================================
def carteiro_worker():
    while True:
        t = fila_saida.get()
        if t is None: break
        try:
            p = t['proc']
            agora = time.strftime('%d/%m/%Y %H:%M')
            texto_html = (
                f"🏛 <b>NOVA MOVIMENTAÇÃO DETECTADA</b>\n"
                f"--------------------------------------------------\n"
                f"📌 <b>Processo:</b> <code>{p['numero']}</code>\n"
                f"⚖️ <b>Tribunal:</b> {t['tribunal']}\n"
                f"📋 <b>Classe:</b> {p['classe']}\n"
                f"👤 <b>{p['parte_label']}:</b> {p['parte_nome']}\n"
                f"📅 <b>Alerta em:</b> {agora}\n\n"
                f"🔍 <b>Andamentos Recentes:</b>\n"
                f"<blockquote>🟡 <b>ATUALIZAÇÃO:</b>\n{t['conteudo']}</blockquote>\n"
                f"🔗 <a href='{p['url']}'>Abrir no Tribunal</a>\n\n"
                f"✅ <i>Vigilante Master</i>"
            )
            for chat in CHATS_ESPECTADORES:
                if t['img'] and os.path.exists(t['img']):
                    with open(t['img'], 'rb') as f:
                        bot.send_photo(chat, f, caption=texto_html, parse_mode="HTML")
                else:
                    bot.send_message(chat, texto_html, parse_mode="HTML")
        except: pass
        fila_saida.task_done()
        time.sleep(1)

# ==========================================
# 3. EXTRAÇÃO (LÓGICA ORIGINAL 8.2)
# ==========================================
def extrair_playwright(p_instance, id_nome, url):
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando TJRJ...")
        nav = p_instance.chromium.launch(headless=False, args=['--window-position=-32000,-32000', '--disable-gpu'])
        ctx = nav.new_context(viewport={'width': 1280, 'height': 1200})
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
            txt = "\n".join([l.inner_text().strip() for l in linhas[1:15]]) # 15 linhas para IA
            return txt.strip(), print_path
        except: return None, None
        finally: nav.close()

def extrair_stf_stealth(id_nome, url):
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando STF...")
        driver = None
        try:
            options = uc.ChromeOptions()
            options.add_argument("--disable-gpu")
            driver = uc.Chrome(options=options, version_main=VERSAO_CHROME_VM) 
            driver.get(url)
            time.sleep(10)
            
            # Foco Inteligente STF: Localiza a tabela real
            try:
                alvo = driver.find_element(By.CSS_SELECTOR, ".andamento-item, app-andamento")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", alvo)
                time.sleep(2)
            except: driver.execute_script("window.scrollTo(0, 700)")
            
            print_path = f"print_{id_nome}.png"
            driver.save_screenshot(print_path)
            
            items = driver.find_elements(By.CSS_SELECTOR, ".andamento-item, .processo-detalhe-andamento tr")
            txt = "\n".join([i.text.strip() for i in items[:15] if len(i.text) > 10])
            return txt.strip(), print_path
        except: return None, None
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
# 4. BOT INTERATIVO (IA SEM 404 - SDK 2026)
# ==========================================
def tarefa_ia_resumo(message, pid, proc):
    try:
        arq = f"estado_{pid}.txt"
        if not os.path.exists(arq):
            bot.send_message(message.chat.id, "⚠️ Sem dados locais para análise.")
            return

        with open(arq, "r", encoding="utf-8") as f:
            historico = f.read()

        prompt = f"Analise este histórico jurídico ({proc['numero']}) e resuma de forma simples os eventos de Maio de 2026:\n\n{historico}"
        
        # Chamada direta e estável
        try:
            analise = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        except Exception as e1:
            print(f"Erro no modelo 2.0: {e1}")
            try:
                analise = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
            except Exception as e2:
                print(f"Erro no modelo 1.5: {e2}")
                bot.send_message(message.chat.id, f"❌ Erro na IA: Falha ao gerar conteúdo. {e2}")
                return
            
        import html
        texto_seguro = html.escape(analise.text)
        # Tenta converter negrito do markdown para HTML básico
        texto_seguro = texto_seguro.replace("**", "<b>").replace("</b><b>", "") # workaround for bold
        # As tags ** foram trocadas por <b>, então precisamos corrigir o fechamento
        import re
        texto_seguro = re.sub(r'<b>(.*?)<b>', r'<b>\1</b>', texto_seguro)
        
        # Para ser mais seguro contra falhas de parse do Telegram, apenas escapamos o texto base
        texto_base = html.escape(analise.text)
        
        try:
            bot.send_message(message.chat.id, f"🧠 <b>ANÁLISE IA - {pid}</b>\n\n{texto_base}", parse_mode="HTML")
        except Exception as telegram_err:
            print(f"Erro de formatação HTML, enviando texto puro: {telegram_err}")
            bot.send_message(message.chat.id, f"🧠 ANÁLISE IA - {pid}\n\n{analise.text}")
            
    except Exception as e:
        print(f"Erro geral IA: {e}")
        bot.send_message(message.chat.id, f"❌ Erro na IA: {e}")

@bot.message_handler(commands=['resumo'])
def responder_resumo(message):
    if str(message.chat.id) not in CHATS_ESPECTADORES: return
    try:
        pid = message.text.split()[1].upper()
        proc = next((p for p in PROCESSOS_TJRJ+PROCESSOS_STF+PROCESSOS_TSE if p['id'] == pid), None)
        if proc:
            bot.send_message(message.chat.id, f"🔍 <b>IA</b> lendo histórico de {pid}...")
            threading.Thread(target=tarefa_ia_resumo, args=(message, pid, proc)).start()
    except:
        bot.reply_to(message, "⚠️ Use: /resumo ID")

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
    print("🚀 Vigilante v11.7 Iniciado!")
    try:
        bot.send_message(ADMIN_ID, "🚀 <b>Vigilante Master v11.7 Online!</b>\nMonitorando TJRJ, STF e TSE.", parse_mode="HTML")
    except: pass
    
    threading.Thread(target=carteiro_worker, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    
    cnt = 0
    while True:
        print(f"\n--- CICLO #{cnt} | {time.strftime('%H:%M:%S')} ---")
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

if __name__ == "__main__":
    iniciar_vigilancia()