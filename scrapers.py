import hashlib
import json
import os
import re
import time
import threading
from pathlib import Path
from typing import Optional, Tuple

import undetected_chromedriver as uc
from playwright.sync_api import PlaywrightContextManager, sync_playwright
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

lock_navegador = threading.Lock()
VERSAO_CHROME_VM = 150
LOG_DIAG_DIR = Path("logs_tse_diag")
# Perfil persistente do Chrome pro TSE: sessao "nova" (pasta temp descartada a
# cada ciclo) e um sinal forte de automacao pro hCaptcha. Reusar um perfil com
# cookies/historico acumulados ao longo do tempo parece mais com um usuario real.
PERFIL_TSE_DIR = Path("chrome_profile_tse")
# Data no formato exibido pelo TSE: "DD/MM/YYYY, HH:MM:SS" (com virgula entre data e hora)
_DATA_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4},\s\d{2}:\d{2}:\d{2}$")


def exterminar_zumbis():
    try:
        os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
        cmd_ps = (
            'powershell -Command "'
            'Get-CimInstance Win32_Process -Filter \\"name = \'chrome.exe\'\\" | '
            'Where-Object {$_.CommandLine -like \'*--remote-debugging-port*\' -or $_.CommandLine -like \'*--headless*\'} | '
            'ForEach-Object {Stop-Process $_.ProcessId -Force -ErrorAction SilentlyContinue}'
            '"'
        )
        os.system(cmd_ps)
        time.sleep(2)
    except Exception:
        pass


def extrair_playwright(
    p_instance: PlaywrightContextManager,
    id_nome: str,
    url: str,
) -> Tuple[Optional[str], Optional[str]]:
    with lock_navegador:
        print(f"   📡 {id_nome}: Acessando TJRJ...")

        nav = None
        pag = None
        try:
            nav = p_instance.chromium.launch(
                headless=False,
                args=[
                    '--headless=new', '--disable-gpu', '--window-size=1920,1080',
                    '--disable-blink-features=AutomationControlled',
                ],
            )
            ctx = nav.new_context(
                viewport={'width': 1280, 'height': 1200},
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            pag = ctx.new_page()

            pag.goto(url, timeout=60000, wait_until='domcontentloaded')
            tabela = pag.locator("table:has(th:has-text('Data'))").first
            pag.wait_for_timeout(2000)
            tabela.scroll_into_view_if_needed()

            primeira_linha = tabela.locator('tr').nth(1)
            box = primeira_linha.bounding_box()
            print_path = f'print_{id_nome}.png'
            pag.screenshot(
                path=print_path,
                clip={'x': box['x'], 'y': box['y'] - 5, 'width': 650, 'height': 600},
            )

            linhas = tabela.locator('tr').all()
            txt = '\n'.join([l.inner_text().strip() for l in linhas[1:15]])
            return txt.strip(), print_path

        except Exception as e:
            print(f'   ❌ Erro ao extrair {id_nome}: {e}')
            if pag is not None:
                try:
                    pasta_atual = os.path.dirname(os.path.abspath(__file__))
                    caminho_erro = os.path.join(pasta_atual, f'DEBUG_ERRO_{id_nome}.png')
                    pag.screenshot(path=caminho_erro, full_page=True)
                except Exception:
                    pass
            return None, None
        finally:
            if nav is not None:
                try:
                    nav.close()
                except Exception:
                    pass


def _raspar_tjrj(pag, id_nome: str, url: str) -> Tuple[Optional[str], Optional[str]]:
    print(f"   📡 {id_nome}: Acessando TJRJ...")
    try:
        pag.goto(url, timeout=60000, wait_until='domcontentloaded')
        tabela = pag.locator("table:has(th:has-text('Data'))").first
        pag.wait_for_timeout(2000)
        tabela.scroll_into_view_if_needed()
        primeira_linha = tabela.locator('tr').nth(1)
        box = primeira_linha.bounding_box()
        print_path = f'print_{id_nome}.png'
        pag.screenshot(path=print_path, clip={'x': box['x'], 'y': box['y'] - 5, 'width': 650, 'height': 600})
        linhas = tabela.locator('tr').all()
        txt = '\n'.join([l.inner_text().strip() for l in linhas[1:15]])
        return txt.strip(), print_path
    except Exception as e:
        print(f'   ❌ Erro ao extrair {id_nome}: {e}')
        try:
            pag.screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), f'DEBUG_ERRO_{id_nome}.png'), full_page=True)
        except Exception:
            pass
        return None, None


def extrair_playwright_batch(processos: list) -> list:
    with lock_navegador:
        n = len(processos)
        print(f'   📡 TJRJ: Abrindo navegador para {n} processo(s)...')
        nav = None
        resultados = [(None, None)] * n
        try:
            with sync_playwright() as p:
                nav = p.chromium.launch(
                    headless=False,
                    args=[
                        '--headless=new', '--disable-gpu', '--window-size=1920,1080',
                        '--disable-blink-features=AutomationControlled',
                    ],
                )
                ctx = nav.new_context(
                    viewport={'width': 1280, 'height': 1200},
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/124.0.0.0 Safari/537.36'
                    ),
                )
                ctx.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                for idx, pr in enumerate(processos):
                    pag = ctx.new_page()
                    try:
                        resultados[idx] = _raspar_tjrj(pag, pr['id'], pr['url'])
                    finally:
                        try:
                            pag.close()
                        except Exception:
                            pass
        except Exception as e:
            print(f'   ❌ Erro fatal TJRJ batch: {e}')
        finally:
            if nav:
                try:
                    nav.close()
                except Exception:
                    pass
        return resultados


# ── STF ─────────────────────────────────────────────────────────────────────
# Lógica de scraping compartilhada entre o modo single e o modo batch.

def _criar_driver_stf():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return uc.Chrome(options=options, version_main=VERSAO_CHROME_VM)


def _raspar_stf(driver, id_nome: str, url: str) -> Tuple[Optional[str], Optional[str]]:
    print(f'   📡 {id_nome}: Acessando STF...')
    # A pagina abre por padrao na aba "Informacoes"; sem o hash abaixo a aba
    # "Andamentos" so fica ativa apos clique, e o find_elements no final
    # sempre retorna vazio -> FalhaCaptura constante.
    url_andamentos = url if '#andamentos' in url else url + '#andamentos'
    driver.get(url_andamentos)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.andamento-item, app-andamento'))
        )
    except Exception:
        pass  # timeout: segue pro fallback de scroll (abaixo)

    try:
        alvo = driver.find_element(By.CSS_SELECTOR, '.andamento-item, app-andamento')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", alvo)
        time.sleep(2)
    except Exception:
        driver.execute_script('window.scrollTo(0, 700)')

    print_path = f'print_{id_nome}.png'
    driver.save_screenshot(print_path)

    items = driver.find_elements(
        By.CSS_SELECTOR, '.andamento-item, .processo-detalhe-andamento tr'
    )
    txt = '\n'.join([i.text.strip() for i in items[:15] if len(i.text) > 10])
    return txt.strip(), print_path


def extrair_stf_stealth_batch(
    processos: list,
) -> list:
    with lock_navegador:
        n = len(processos)
        print(f'   📡 STF: Abrindo navegador para {n} processo(s)...')
        driver = None
        resultados = [(None, None)] * n
        try:
            driver = _criar_driver_stf()
            for idx, (id_nome, url) in enumerate(processos):
                try:
                    resultados[idx] = _raspar_stf(driver, id_nome, url)
                except Exception as e:
                    err_msg = str(e).lower()
                    if any(k in err_msg for k in ['no such window', 'web view not found', 'target window already closed']):
                        print(f'   ⚠️ STF ({id_nome}): janela/DevTools desconectado. Recriando driver...')
                        if driver:
                            try:
                                driver.quit()
                            except Exception:
                                pass
                        driver = _criar_driver_stf()
                        try:
                            resultados[idx] = _raspar_stf(driver, id_nome, url)
                        except Exception as e2:
                            print(f'   ❌ Erro detalhado no STF ({id_nome}) após retry: {e2}')
                    else:
                        print(f'   ❌ Erro detalhado no STF ({id_nome}): {e}')
        except Exception as e:
            print(f'   ❌ Erro fatal STF batch: {e}')
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        return resultados


# ── TSE ─────────────────────────────────────────────────────────────────────

def _esperar_card_estavel(card, timeout: int = 30, poll: float = 2.0, leituras: int = 3) -> bool:
    """Espera o conteudo do card parar de mudar (N leituras consecutivas identicas).

    A SPA do TSE renderiza andamentos de forma incremental apos o captcha:
    comeca com 1-2 itens visiveis e vai adicionando os demais. Sem essa
    espera, o `card.text` no momento da extracao captura um estado parcial
    (1, 3, 5, 7 itens) que varia entre ciclos -> o Detector compara 7 itens
    contra 5 e dispara Mudanca falsa.

    Por padrao exige 3 leituras consecutivas identicas (era 2 ate jul/2026
    mas ainda gerava falsos positivos esporadicos).

    Retorna True se estabilizou dentro do timeout, False se atingiu o limite
    (nesse caso o caller ainda pode usar o ultimo texto lido, com cautela).
    """
    t_inicio = time.time()
    texto_anterior = None
    contador_estavel = 0
    while time.time() - t_inicio < timeout:
        try:
            texto_atual = card.text
        except Exception:
            return False
        if (
            texto_anterior is not None
            and texto_atual == texto_anterior
            and len(texto_atual.strip()) > 50
        ):
            contador_estavel += 1
            if contador_estavel >= leituras - 1:
                return True
        else:
            contador_estavel = 0
        texto_anterior = texto_atual
        time.sleep(poll)
    return False


def _fingerprint_itens(linhas_filtradas: list) -> str:
    """Hash MD5 dos itens (pares titulo+data), ignorando header e qualquer linha extra.

    O texto bruto do card pode conter elementos dinamicos (timestamp, ID de
    sessao, etc.) que mudam entre ciclos mas nao representam movimento real.
    Esta funcao extrai apenas os pares titulo+data dos andamentos e calcula
    um hash estavel. O Detector compara o hash, nao o texto bruto.

    O loop para no primeiro par cuja segunda linha nao casa com o padrao de
    data do TSE (DD/MM/YYYY, HH:MM:SS). Isso ignora com seguranca rodapes
    tipo "Ultima consulta: ..." ou "Sessao: ..." que nao sao movimentos.
    """
    itens = []
    pares = linhas_filtradas[1:]  # pula o header "Movimentos"
    i = 0
    while i + 1 < len(pares):
        titulo = pares[i]
        data = pares[i + 1]
        if not _DATA_PATTERN.match(data):
            # Nao parece (titulo, data) -> provavelmente rodape
            break
        itens.append(f"{titulo}|{data}")
        i += 2
    base = "\n".join(itens)
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def _salvar_diag_tse(id_nome: str, texto_card_bruto: str, linhas_filtradas: list,
                     fingerprint: str, mudou: bool) -> None:
    """Salva o texto bruto e o fingerprint em arquivo de log para diagnostico.

    Cada extracao gera um arquivo .jsonl em logs_tse_diag/ com:
    - timestamp
    - pid
    - texto_card_bruto (texto completo do card apos estabilizacao)
    - linhas_filtradas (apos filtro > 3 chars, != autorenew)
    - fingerprint (hash dos itens)
    - mudou (True se o fingerprint difere do anterior)

    Quando o usuario reportar falso positivo, basta comparar os arquivos
    recentes para identificar o que esta variando.
    """
    try:
        LOG_DIAG_DIR.mkdir(exist_ok=True)
        arq = LOG_DIAG_DIR / f"{id_nome}.jsonl"
        registro = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pid": id_nome,
            "texto_bruto_len": len(texto_card_bruto),
            "linhas_filtradas": linhas_filtradas,
            "fingerprint": fingerprint,
            "mudou": mudou,
        }
        with open(arq, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"   ⚠️ Falha ao salvar diag TSE: {e}")


def extrair_tse_stealth_batch(
    processos: list,
    on_captcha=None,
) -> list:
    with lock_navegador:
        n = len(processos)
        print(f'   📡 TSE: Abrindo navegador para {n} processo(s)...')
        driver = None
        resultados = [(None, None, None)] * n
        try:
            PERFIL_TSE_DIR.mkdir(exist_ok=True)
            options = uc.ChromeOptions()
            options.add_argument('--disable-gpu')
            options.page_load_strategy = 'none'
            driver = uc.Chrome(
                options=options,
                version_main=VERSAO_CHROME_VM,
                user_data_dir=str(PERFIL_TSE_DIR.resolve()),
            )

            for idx, (id_nome, url, numero) in enumerate(processos):
                print(f'   📡 {id_nome}: Acessando TSE...')
                try:
                    if on_captcha:
                        on_captcha(numero)
                    driver.get(url)

                    card_alvo = None
                    tempo_limite = 300
                    tempo_inicial = time.time()

                    print('      [!] Aguardando resolucao do captcha na tela (limite 5 min)...')
                    while time.time() - tempo_inicial < tempo_limite:
                        try:
                            cards = driver.find_elements(By.CLASS_NAME, 'tramitacao-card')
                            card_alvo = next(
                                (c for c in cards if 'Movimentos' in c.text and 'Documentos' not in c.text),
                                None,
                            )
                            if card_alvo and len(card_alvo.text.strip()) > 50:
                                print(f'      ✅ {id_nome}: Dados carregados apos resolucao do captcha!')
                                break
                        except Exception:
                            pass
                        time.sleep(3)

                    if not card_alvo:
                        print(f'      ❌ {id_nome}: Tempo esgotado aguardando resolucao do captcha.')
                        continue

                    estabilizou = _esperar_card_estavel(card_alvo, timeout=30, poll=2.0, leituras=3)
                    if not estabilizou:
                        print(f'      ⚠️ {id_nome}: card nao estabilizou em 30s — extraindo mesmo assim.')

                    print_path = f'print_{id_nome}.png'
                    card_alvo.screenshot(print_path)

                    texto_bruto = card_alvo.text
                    linhas = [
                        l.strip()
                        for l in texto_bruto.split('\n')
                        if len(l.strip()) > 3 and l.strip().lower() != 'autorenew'
                    ]
                    fp = _fingerprint_itens(linhas)
                    n_itens = max(0, (len(linhas) - 1) // 2)
                    print(f'   📊 {id_nome}: extraiu {len(linhas)} linhas ({n_itens} itens) fp={fp[:8]}')

                    _salvar_diag_tse(id_nome, texto_bruto, linhas, fp, mudou=False)

                    resultados[idx] = ('\n'.join(linhas[:15]), fp, print_path)
                except Exception as e:
                    print(f'   ❌ Erro ao extrair TSE ({id_nome}): {e}')

        except Exception as e:
            print(f'   ❌ Erro fatal TSE batch: {e}')
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        return resultados
