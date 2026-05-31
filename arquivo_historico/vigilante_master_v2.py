import os
import time
import requests
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
API_KEY_GEMINI     = os.getenv("API_KEY_GEMINI")

def enviar_relatorio_premium(nome_tribunal, conteudo, link, numero, print_path=None):
    url_photo = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendPhoto"
    agora = time.strftime('%d/%m/%Y %H:%M')
    
    # Layout visualmente limpo com bloco de destaque
    texto_html = (
        f"🏛 <b>NOVA MOVIMENTAÇÃO DETECTADA</b>\n"
        f"--------------------------------------------------\n"
        f"📌 <b>Processo:</b> <code>{numero}</code>\n"
        f"⚖️ <b>Tribunal:</b> {nome_tribunal}\n"
        f"📅 <b>Alerta gerado em:</b> {agora}\n\n"
        f"🔍 <b>Últimos Andamentos:</b>\n"
        f"<blockquote>🟡 <b>ATUALIZAÇÃO:</b>\n{conteudo}</blockquote>\n"
        f"🔗 <a href='{link}'>Clique aqui para abrir o processo</a>\n\n"
        f"✅ <i>Vigilante 6.4</i>"
    )

    try:
        if print_path and os.path.exists(print_path):
            with open(print_path, 'rb') as photo:
                payload = {"chat_id": CHAT_ID, "caption": texto_html, "parse_mode": "HTML"}
                requests.post(url_photo, data=payload, files={"photo": photo})
        else:
            url_text = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
            requests.post(url_text, json={"chat_id": CHAT_ID, "text": texto_html, "parse_mode": "HTML", "disable_web_page_preview": False})
    except Exception as e:
        print(f"❌ Erro Telegram: {e}")

def alertar_sistema_ativo():
    url_text = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    texto = "🚀 <b>Vigilante Master v6.4 Ativado!</b>\nO monitoramento dos processos do STF, TJRJ e TSE está em execução."
    try:
        requests.post(url_text, json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "HTML"})
        print("✅ Alerta de sistema ativo enviado.")
    except: pass

# ==========================================
# 2. MÓDULO TJRJ (PARSING DE DADOS LIMPOS)
# ==========================================
def extrair_tjrj_stf(playwright_instance, id_nome, url_processo, numero):
    print(f"📡 Iniciando captura silenciosa TJRJ...")
    navegador = playwright_instance.chromium.launch(headless=False)
    contexto = navegador.new_context(viewport={'width': 1280, 'height': 1200}, device_scale_factor=2)
    pagina = contexto.new_page()
    try:
        pagina.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        pagina.goto(url_processo, timeout=90000, wait_until="load")
        
        tabela_eventos = pagina.locator("table:has(th:has-text('Data')):has(th:has-text('Evento'))").first
        pagina.wait_for_timeout(3000)
        tabela_eventos.scroll_into_view_if_needed()
        
        # Tirar o Print
        primeira_linha = tabela_eventos.locator("tr").nth(1)
        box = primeira_linha.bounding_box()
        print_path = f"print_{id_nome}.png"
        pagina.screenshot(path=print_path, clip={'x': box['x'], 'y': box['y'] - 5, 'width': 580, 'height': 500})
        
        # EXTRAÇÃO DE TEXTO LIMPO (Data e Descrição)
        linhas_html = tabela_eventos.locator("tr").all()
        texto_limpo = ""
        
        # Pula o cabeçalho (índice 0) e pega os 3 andamentos mais recentes
        for linha in linhas_html[1:9]:
            celulas = linha.locator("td").all()
            if len(celulas) >= 3:
                # Limpa espaços extras e quebras de linha indesejadas
                data_hora = " ".join(celulas[1].inner_text().split())
                descricao = " ".join(celulas[2].inner_text().split())
                texto_limpo += f"🔸 <b>{data_hora}</b>\n{descricao}\n\n"
        
        print(f"✅ TJRJ extraído e formatado com sucesso!")
        return texto_limpo.strip(), print_path
    except Exception as e:
        print(f"❌ Erro TJRJ: {e}")
        return None, None
    finally: navegador.close()

# ==========================================
# 3. MÓDULO TSE
# ==========================================
def extrair_tse(id_nome, url_processo):
    driver = None
    try:
        print(f"📡 Iniciando Motor Stealth para o TSE...")
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1280,800")
        driver = uc.Chrome(options=options, version_main=147)
        
        driver.get(url_processo)
        print("\n=======================================================")
        print("💡 Resolva o desafio se aparecer e aperte ENTER quando os movimentos surgirem.")
        print("=======================================================")
        input("Aguardando seu ENTER...") 

        print("📸 Capturando imagem e lendo os dados...")
        cards = driver.find_elements(By.CLASS_NAME, "tramitacao-card")
        card_alvo = next((c for c in cards if "Movimentos" in c.text), None)
                
        if not card_alvo: 
            return None, None

        print_path = f"print_{id_nome}.png"
        card_alvo.screenshot(print_path)
        
        linhas = [l.strip() for l in card_alvo.text.split('\n') if len(l.strip()) > 3]
        if "Movimentos" in linhas[0]: linhas = linhas[1:]
        
        # Formatação do TSE
        texto_limpo = ""
        for linha in linhas[:5]:
            texto_limpo += f"🔸 {linha}\n"
            
        print("✅ TSE extraído com sucesso!")
        return texto_limpo.strip(), print_path
    except Exception as e:
        print(f"❌ Erro TSE: {e}")
        return None, None
    finally:
        if driver:
            try: driver.quit()
            except: pass

# ==========================================
# 4. MOTOR DE VIGILÂNCIA E COMPARAÇÃO
# ==========================================
# Note que adicionei o parâmetro 'nome_exibicao' para controlar o título da mensagem
def verificar_mudanca(id_arquivo, nome_exibicao, texto_novo, print_path, link, numero):
    if not texto_novo or len(texto_novo.strip()) < 10: return
        
    arquivo_estado = f"estado_{id_arquivo}.txt"
    
    if not os.path.exists(arquivo_estado):
        with open(arquivo_estado, "w", encoding="utf-8") as f: f.write(texto_novo)
        print(f"📁 {nome_exibicao}: Primeira leitura salva como base.")
        return
        
    with open(arquivo_estado, "r", encoding="utf-8") as f: texto_antigo = f.read()
    
    if texto_novo != texto_antigo:
        print(f"🚨 ALERTA: Nova movimentação no {nome_exibicao}! Enviando relatório...")
        enviar_relatorio_premium(nome_exibicao, texto_novo, link, numero, print_path)
        with open(arquivo_estado, "w", encoding="utf-8") as f: f.write(texto_novo)
    else:
        print(f"🔎 {nome_exibicao}: Nenhuma movimentação nova.")

def iniciar_vigilancia():
    alertar_sistema_ativo()
    
    num_tjrj = "3004566-28.2026.8.19.0000"
    url_tjrj = "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&num_processo=30045662820268190000&num_chave=&hash=b33f48b0cc0ad69e5cd182e3751fd64e&num_chave_documento="
    
    num_tse = "0606570-47.2022.6.19.0000"
    url_tse = "https://consultaunificadapje.tse.jus.br/#/public/resultado/0606570-47.2022.6.19.0000"
    
    contador = 0
    while True:
        print(f"\n=======================================================")
        print(f"🕒 INICIANDO CICLO #{contador} | {time.strftime('%H:%M:%S')}")
        print(f"=======================================================")
        
        # TJRJ
        with sync_playwright() as p:
            # Passamos a ID do arquivo separada do Nome Amigável ("TJRJ")
            txt_tj, foto_tj = extrair_tjrj_stf(p, "TJRJ_Simoes", url_tjrj, num_tjrj)
            verificar_mudanca("TJRJ_Simoes", "TJRJ", txt_tj, foto_tj, url_tjrj, num_tjrj)
        
        # TSE
        if contador % 6 == 0:
            txt_tse, foto_tse = extrair_tse("TSE_Eleitoral", url_tse)
            verificar_mudanca("TSE_Eleitoral", "TSE", txt_tse, foto_tse, url_tse, num_tse)
        
        print("\n⏳ Ciclo finalizado. Dormindo por 2 minutos...")
        time.sleep(120)
        contador += 1

if __name__ == "__main__":
    iniciar_vigilancia()