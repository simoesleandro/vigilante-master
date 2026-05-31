import os
import time
import requests
import threading
import ssl
import telebot
import google.generativeai as genai
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
genai.configure(api_key=API_KEY_GEMINI)

# Mudamos para o identificador mais robusto da biblioteca atual
model_ia = genai.GenerativeModel('gemini-1.5-flash-latest') 

bot = telebot.TeleBot(TOKEN_TELEGRAM)

# ... (Listas de PROCESSOS_TJRJ, STF e TSE permanecem as mesmas) ...
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
# 2. FUNÇÕES DE IA E NOTIFICAÇÃO
# ==========================================
def gerar_analise_ia(historico_bruto, tribunal, numero):
    if not historico_bruto: return "⚠️ Histórico vazio."
    
    print(f"🧠 Consultando IA para {numero}...")
    prompt = f"Analise este histórico do {tribunal} (Processo {numero}) e resuma o que aconteceu em Maio de 2026:\n{historico_bruto}"
    
    try:
        # Tentativa com o novo método de chamada de 2026
        response = model_ia.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Erro IA: {e}")
        return "⚠️ Erro ao gerar resumo (Verificar API Key ou Modelo)."

def enviar_alerta_captcha(tribunal, numero):
    try: bot.send_message(ADMIN_ID, f"⚠️ <b>CAPTCHA {tribunal}</b>\nProcesso: {numero}\nResolva na VM e aperte ENTER.", parse_mode="HTML")
    except: pass

def enviar_relatorio_premium(tribunal, conteudo, proc, print_path=None, chat_especifico=None, analise_ia=None):
    texto = f"🏛 <b>{tribunal} - ATUALIZAÇÃO</b>\n📌 {proc['numero']}\n👤 {proc['parte_nome']}\n\n"
    if analise_ia: texto += f"💡 <b>RESUMO IA:</b>\n<blockquote>{analise_ia}</blockquote>"
    else: texto += f"🔍 <b>MOVIMENTOS:</b>\n<blockquote>{conteudo}</blockquote>"
    
    destinos = [chat_especifico] if chat_especifico else CHATS_ESPECTADORES
    for chat in destinos:
        try:
            if print_path and os.path.exists(print_path):
                with open(print_path, 'rb') as p: bot.send_photo(chat, p, caption=texto, parse_mode="HTML")
            else: bot.send_message(chat, texto, parse_mode="HTML")
        except: pass

# ==========================================
# 3. EXTRAÇÃO (COM CORREÇÃO DE DATA TSE)
# ==========================================
def extrair_playwright(p_instance, id_nome, url, tribunal_label):
    nav = p_instance.chromium.launch(headless=False, args=['--disable-gpu'])
    pag = nav.new_page(viewport={'width': 1280, 'height': 1024})
    try:
        pag.goto(url, timeout=60000, wait_until="networkidle")
        if tribunal_label == "TJRJ":
            tabela = pag.locator("table:has(th:has-text('Data'))").first
            tabela.scroll_into_view_if_needed()
            print_path = f"print_{id_nome}.png"
            pag.screenshot(path=print_path, clip={'x': 0, 'y': 200, 'width': 800, 'height': 600})
            # Pegamos os andamentos (Geralmente os primeiros são os mais novos no eproc)
            linhas = tabela.locator("tr").all()
            txt = "\n".join([l.inner_text().strip() for l in linhas[1:6]])
            return txt, print_path
    except: return None, None
    finally: nav.close()

def extrair_stf_stealth(id_nome, url, numero):
    ssl._create_default_https_context = ssl._create_unverified_context
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        driver = uc.Chrome(options=options, version_main=147)
        driver.get(url)
        time.sleep(7)
        driver.execute_script("window.scrollBy(0, 700)")
        print_path = f"print_{id_nome}.png"
        driver.save_screenshot(print_path)
        items = driver.find_elements(By.CSS_SELECTOR, ".andamento-item, .processo-detalhe-andamento tr")
        # STF costuma ter o mais novo no topo
        txt = "\n".join([i.text.strip() for i in items[:8]])
        return txt, print_path
    except: return None, None
    finally:
        if driver: driver.quit()

def extrair_tse_stealth(id_nome, url, numero):
    ssl._create_default_https_context = ssl._create_unverified_context
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        driver = uc.Chrome(options=options, version_main=147)
        threading.Thread(target=enviar_alerta_captcha, args=("TSE", numero)).start()
        driver.get(url)
        input(f"⚠️  Resolva o TSE e aperte ENTER...")
        time.sleep(5)
        
        # O PJe do TSE às vezes lista da mais antiga para a mais nova
        cards = driver.find_elements(By.CLASS_NAME, "tramitacao-card")
        
        # Lógica de Inversão: Pegamos todas as linhas e REVERTEMOS para garantir que Maio/2026 venha primeiro
        linhas_brutas = [l.strip() for l in cards[0].text.split('\n') if len(l.strip()) > 5 and "autorenew" not in l.lower()]
        
        # Se a primeira linha contiver "2022" ou "2023", a lista está invertida
        if "2026" not in linhas_brutas[0] and "2026" in linhas_brutas[-1]:
            linhas_brutas.reverse()
            
        txt = "\n".join(linhas_brutas[:12])
        
        print_path = f"print_{id_nome}.png"
        driver.save_screenshot(print_path)
        return txt, print_path
    except: return None, None
    finally:
        if driver: driver.quit()

# ... (Função comando_resumo e iniciar_vigilancia continuam com a mesma estrutura) ...
@bot.message_handler(commands=['resumo'])
def comando_resumo(message):
    if str(message.chat.id) not in CHATS_ESPECTADORES: return
    try:
        pid = message.text.split()[1].upper()
        bot.send_message(message.chat.id, f"🔍 Analisando {pid}...")
        proc = next((p for p in PROCESSOS_TJRJ + PROCESSOS_STF + PROCESSOS_TSE if p['id'] == pid), None)
        
        if "TJRJ" in pid:
            with sync_playwright() as p: txt, img = extrair_playwright(p, proc['id'], proc['url'], "TJRJ")
        elif "STF" in pid: txt, img = extrair_stf_stealth(proc['id'], proc['url'], proc['numero'])
        elif "TSE" in pid: txt, img = extrair_tse_stealth(proc['id'], proc['url'], proc['numero'])
        
        if txt:
            analise = gerar_analise_ia(txt, pid.split('_')[0], proc['numero'])
            enviar_relatorio_premium(pid.split('_')[0], txt, proc, img, message.chat.id, analise)
    except: bot.reply_to(message, "⚠️ Use /resumo ID")

def iniciar_vigilancia():
    bot.send_message(ADMIN_ID, "🚀 <b>Vigilante v9.3 On!</b>", parse_mode="HTML")
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    cnt = 0
    while True:
        print(f"\n# CICLO {cnt} | {time.strftime('%H:%M:%S')}")
        with sync_playwright() as p:
            for pr in PROCESSOS_TJRJ:
                t, i = extrair_playwright(p, pr['id'], pr['url'], "TJRJ")
                if t:
                    arq = f"estado_{pr['id']}.txt"
                    if not os.path.exists(arq) or open(arq, "r", encoding="utf-8").read() != t:
                        ia = gerar_analise_ia(t, "TJRJ", pr['numero'])
                        enviar_relatorio_premium("TJRJ", t, pr, i, analise_ia=ia)
                        with open(arq, "w", encoding="utf-8") as f: f.write(t)

        for pr in PROCESSOS_STF:
            t, i = extrair_stf_stealth(pr['id'], pr['url'], pr['numero'])
            if t:
                arq = f"estado_{pr['id']}.txt"
                if not os.path.exists(arq) or open(arq, "r", encoding="utf-8").read() != t:
                    ia = gerar_analise_ia(t, "STF", pr['numero'])
                    enviar_relatorio_premium("STF", t, pr, i, analise_ia=ia)
                    with open(arq, "w", encoding="utf-8") as f: f.write(t)

        if cnt % 13 == 0:
            for pr in PROCESSOS_TSE:
                t, i = extrair_tse_stealth(pr['id'], pr['url'], pr['numero'])
                if t:
                    ia = gerar_analise_ia(t, "TSE", pr['numero'])
                    enviar_relatorio_premium("TSE", t, pr, i, analise_ia=ia)

        time.sleep(120)
        cnt += 1

if __name__ == "__main__":
    iniciar_vigilancia()