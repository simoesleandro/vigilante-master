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

PROCESSOS_TJRJ = [
    {"id": "TJRJ_1", "numero": "3004566-28.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_nome_parte_publica&acao_retorno=processo_consulta_nome_parte_publica&num_processo=30045662820268190000&num_chave=&hash=b33f48b0cc0ad69e5cd182e3751fd64e&num_chave_documento="},
    {"id": "TJRJ_2", "numero": "3004326-39.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30043263920268190000&num_chave=&num_chave_documento=&hash=2ad7164906ea016a598e771470c6a7fb"},
    {"id": "TJRJ_3", "numero": "3004629-53.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30046295320268190000&num_chave=&num_chave_documento=&hash=85afa7fb1115618798dc54ecb979febd"},
    {"id": "TJRJ_4", "numero": "3006257-77.2026.8.19.0000", "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30062577720268190000&num_chave=&num_chave_documento=&hash=da8242e844340fbe2106c1a341df9b82"}
]

PROCESSOS_STF = [
    {"id": "STF_1", "numero": "Incidente 7531465", "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7531465"},
    {"id": "STF_2", "numero": "Incidente 7547470", "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7547470"},
    {"id": "STF_3", "numero": "Incidente 7569263", "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7569263"}
]

PROCESSOS_TSE = [
    {"id": "TSE_1", "numero": "0603507-14.2022.6.19.0000", "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0603507-14.2022.6.19.0000"},
    {"id": "TSE_2", "numero": "0606570-47.2022.6.19.0000", "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0606570-47.2022.6.19.0000"}
]

# ==========================================
# 2. SISTEMA DE NOTIFICAÇÕES
# ==========================================
def enviar_alerta_captcha(tribunal, numero):
    url_text = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    texto = (
        f"⚠️ <b>INTERVENÇÃO NECESSÁRIA</b>\n"
        f"--------------------------------------------------\n"
        f"🤖 O robô parou na verificação de segurança.\n"
        f"⚖️ <b>Tribunal:</b> {tribunal}\n"
        f"📌 <b>Processo:</b> {numero}\n\n"
        f"👉 Por favor, resolva o desafio no navegador e aperte ENTER no VS Code."
    )
    try: requests.post(url_text, json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "HTML"})
    except: pass

def enviar_relatorio_premium(nome_tribunal, conteudo, link, numero, print_path=None):
    url_photo = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendPhoto"
    agora = time.strftime('%d/%m/%Y %H:%M')
    
    texto_html = (
        f"🏛 <b>NOVA MOVIMENTAÇÃO DETECTADA</b>\n"
        f"--------------------------------------------------\n"
        f"📌 <b>Processo:</b> <code>{numero}</code>\n"
        f"⚖️ <b>Tribunal:</b> {nome_tribunal}\n"
        f"📅 <b>Alerta gerado em:</b> {agora}\n\n"
        f"🔍 <b>Últimos Andamentos:</b>\n"
        f"<blockquote>🟡 <b>ATUALIZAÇÃO:</b>\n{conteudo}</blockquote>\n"
        f"🔗 <a href='{link}'>Clique aqui para abrir o processo</a>\n\n"
        f"✅ <i>Vigilante Master - FAPERJ</i>"
    )

    try:
        if print_path and os.path.exists(print_path):
            with open(print_path, 'rb') as photo:
                requests.post(url_photo, data={"chat_id": CHAT_ID, "caption": texto_html, "parse_mode": "HTML"}, files={"photo": photo})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage", json={"chat_id": CHAT_ID, "text": texto_html, "parse_mode": "HTML"})
    except Exception as e: print(f"❌ Erro Telegram: {e}")

def alertar_sistema_ativo():
    texto = f"🚀 <b>Vigilante Master Ativado!</b>\nMonitorando {len(PROCESSOS_TJRJ)} do TJRJ, {len(PROCESSOS_STF)} do STF (a cada 2 min) e {len(PROCESSOS_TSE)} do TSE (a cada 12 min)."
    try: requests.post(f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage", json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "HTML"})
    except: pass

# ==========================================
# 3. MÓDULOS DE EXTRAÇÃO (TJRJ, STF, TSE) 
# ==========================================
def extrair_playwright(p_instance, id_nome, url, tribunal_label):
    print(f"📡 Capturando {tribunal_label}: {id_nome}...")
    
    nav = p_instance.chromium.launch(
        headless=False,
        args=['--window-position=-32000,-32000']
    )
    
    ctx = nav.new_context(viewport={'width': 1280, 'height': 1200}, device_scale_factor=1)
    pag = ctx.new_page()
    
    try:
        pag.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        pag.goto(url, timeout=45000, wait_until="domcontentloaded") 
        
        # --- LÓGICA ESPECÍFICA TJRJ ---
        if tribunal_label == "TJRJ":
            tabela = pag.locator("table:has(th:has-text('Data')):has(th:has-text('Evento'))").first
            pag.wait_for_timeout(2000)
            tabela.scroll_into_view_if_needed()
            
            primeira_linha = tabela.locator("tr").nth(1)
            box = primeira_linha.bounding_box()
            print_path = f"print_{id_nome}.png"
            
            pag.screenshot(path=print_path, clip={'x': box['x'], 'y': box['y'] - 5, 'width': 650, 'height': 600})
            
            linhas = tabela.locator("tr").all()
            txt = ""
            for l in linhas[1:4]:
                c = l.locator("td").all()
                if len(c) >= 3:
                    data = " ".join(c[1].inner_text().split())
                    desc = " ".join(c[2].inner_text().split())
                    txt += f"🔸 <b>{data}</b>\n{desc}\n\n"
            return txt.strip(), print_path
            
        # --- LÓGICA ESPECÍFICA STF ---
        elif tribunal_label == "STF":
            print("👇 Localizando as movimentações mais recentes...")
            try:
                pag.wait_for_selector("text='Andamentos', .andamento-item", timeout=10000)
            except:
                pag.wait_for_timeout(2000) 
            
            pag.evaluate("window.scrollBy(0, 600)")
            pag.wait_for_timeout(500)
            
            print_path = f"print_{id_nome}.png"
            pag.screenshot(path=print_path)
            
            items = pag.locator(".andamento-item, .processo-detalhe-andamento tr, app-andamento").all()
            txt = ""
            if items:
                for i in items[:3]:
                    bruto = " ".join(i.inner_text().split())
                    if len(bruto) > 10:
                        txt += f"🔸 {bruto}\n\n"
            
            if not txt:
                txt = "Movimentação identificada visualmente. Verifique o print para detalhes."
                
            return txt.strip(), print_path

    except Exception as e:
        print(f"❌ Erro {tribunal_label}: {e}")
        return None, None
    finally:
        nav.close()

def extrair_tse_stealth(id_nome, url, numero):
    driver = None
    try:
        print(f"📡 Iniciando Motor Stealth para TSE: {numero}")
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1280,800")
        driver = uc.Chrome(options=options, version_main=147)
        driver.get(url)
        
        enviar_alerta_captcha("TSE", numero)
        print("\n=======================================================")
        input(f"⚠️  Resolva o desafio do TSE no Chrome e aperte ENTER aqui...") 
        print("=======================================================")

        cards = driver.find_elements(By.CLASS_NAME, "tramitacao-card")
        card_alvo = next((c for c in cards if "Movimentos" in c.text), None)
        if not card_alvo: return None, None

        print_path = f"print_{id_nome}.png"
        card_alvo.screenshot(print_path)
        
        linhas = [l.strip() for l in card_alvo.text.split('\n') if len(l.strip()) > 3]
        if "Movimentos" in linhas[0]: linhas = linhas[1:]
        
        texto_limpo = ""
        for linha in linhas[:5]:
            texto_limpo += f"🔸 {linha}\n"
            
        return texto_limpo.strip(), print_path
    except Exception as e:
        print(f"❌ Erro TSE: {e}")
        return None, None
    finally:
        if driver: 
            try: driver.quit()
            except: pass

# ==========================================
# 4. GERADOR DE DASHBOARD ESTÁTICO (HTML/Tailwind)
# ==========================================
def gerar_dashboard():
    print("🌐 Gerando nova versão do painel HTML...")
    agora = time.strftime('%d/%m/%Y às %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Monitoramento - FAPERJ</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <meta http-equiv="refresh" content="120">
    </head>
    <body class="bg-slate-50 font-sans antialiased p-6">
        <div class="max-w-7xl mx-auto">
            <header class="mb-8 flex flex-col md:flex-row justify-between items-start md:items-end border-b border-slate-200 pb-4 gap-4">
                <div>
                    <h1 class="text-3xl font-bold text-slate-800">Painel de Monitoramento Legal</h1>
                    <p class="text-slate-500 mt-1">Projeto de Pesquisa Automacional</p>
                </div>
                <div class="text-sm text-slate-600 bg-white px-4 py-2 rounded-full shadow-sm border border-slate-200 flex items-center gap-2">
                    <span class="relative flex h-3 w-3">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                    </span>
                    Última leitura do robô: <span class="font-bold text-slate-800">{agora}</span>
                </div>
            </header>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    """

    todos_processos = [
        ("TJRJ", "bg-blue-100 text-blue-800 border-blue-200", PROCESSOS_TJRJ),
        ("STF", "bg-slate-200 text-slate-800 border-slate-300", PROCESSOS_STF),
        ("TSE", "bg-emerald-100 text-emerald-800 border-emerald-200", PROCESSOS_TSE)
    ]

    for tribunal, cor_badge, lista in todos_processos:
        for proc in lista:
            id_proc = proc['id']
            numero = proc['numero']
            link = proc['url']
            
            arquivo_txt = f"estado_{id_proc}.txt"
            
            if os.path.exists(arquivo_txt):
                with open(arquivo_txt, "r", encoding="utf-8") as f:
                    andamentos = f.read()
                    andamentos_html = andamentos.replace('\n', '<br>')
            else:
                andamentos_html = "<div class='text-slate-400 italic text-center mt-4'>⏳ Aguardando primeira captura do robô...</div>"

            html_content += f"""
                <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow duration-200 flex flex-col h-80">
                    <div class="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center shrink-0">
                        <span class="px-2.5 py-1 rounded-md text-xs font-bold border tracking-wider {cor_badge}">{tribunal}</span>
                        <a href="{link}" target="_blank" class="text-sm text-blue-600 hover:text-blue-800 font-medium truncate ml-3 flex items-center gap-1" title="Abrir no tribunal">
                            {numero} ↗
                        </a>
                    </div>
                    <div class="p-5 text-sm text-slate-700 leading-relaxed overflow-y-auto grow custom-scrollbar">
                        {andamentos_html}
                    </div>
                </div>
            """

    html_content += """
            </div>
        </div>
    </body>
    </html>
    """

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ Dashboard atualizado! Abra o arquivo 'dashboard.html' no navegador.")

# ==========================================
# 5. MOTOR PRINCIPAL
# ==========================================
def verificar_e_notificar(id_arq, nome_exib, txt_novo, print_p, link, num):
    if not txt_novo: return
    arq = f"estado_{id_arq}.txt"
    
    if not os.path.exists(arq):
        with open(arq, "w", encoding="utf-8") as f: f.write(txt_novo)
        print(f"📁 {id_arq}: Primeira leitura salva como base.")
        return
        
    with open(arq, "r", encoding="utf-8") as f: txt_antigo = f.read()
    
    if txt_novo != txt_antigo:
        print(f"🚨 ALERTA: Nova movimentação em {id_arq}! Enviando relatório...")
        enviar_relatorio_premium(nome_exib, txt_novo, link, num, print_p)
        with open(arq, "w", encoding="utf-8") as f: f.write(txt_novo)
    else:
        print(f"🔎 {id_arq}: Nenhuma movimentação nova.")

def iniciar_vigilancia():
    print("🚀 Iniciando Vigilante Master...")
    alertar_sistema_ativo()
    
    cnt = 0
    while True:
        print(f"\n=======================================================")
        print(f"🕒 INICIANDO CICLO #{cnt} | {time.strftime('%H:%M:%S')}")
        print(f"=======================================================")
        
        # 1. Varredura TJRJ
        with sync_playwright() as p:
            for proc in PROCESSOS_TJRJ:
                txt, img = extrair_playwright(p, proc['id'], proc['url'], "TJRJ")
                verificar_e_notificar(proc['id'], "TJRJ", txt, img, proc['url'], proc['numero'])

        # 2. Varredura STF
        with sync_playwright() as p:
            for proc in PROCESSOS_STF:
                txt, img = extrair_playwright(p, proc['id'], proc['url'], "STF")
                verificar_e_notificar(proc['id'], "STF", txt, img, proc['url'], proc['numero'])

        # 3. Varredura TSE (A cada 12 minutos)
        if cnt % 6 == 0:
            print("\n⏰ Hora da varredura do TSE...")
            for proc in PROCESSOS_TSE:
                txt, img = extrair_tse_stealth(proc['id'], proc['url'], proc['numero'])
                verificar_e_notificar(proc['id'], "TSE", txt, img, proc['url'], proc['numero'])
        
        # 4. GERA O DASHBOARD HTML COM OS DADOS FRESCOS
        gerar_dashboard()
        
        print("\n⏳ Ciclo finalizado. O robô vai dormir por 2 minutos...")
        time.sleep(120)
        cnt += 1

if __name__ == "__main__":
    iniciar_vigilancia()