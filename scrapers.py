import os
import time
import threading
from typing import Callable, Optional, Tuple

import undetected_chromedriver as uc
from playwright.sync_api import PlaywrightContextManager
from selenium.webdriver.common.by import By

lock_navegador = threading.Lock()
VERSAO_CHROME_VM = 148


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
    driver.get(url)
    time.sleep(10)

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


def extrair_stf_stealth(
    id_nome: str,
    url: str,
) -> Tuple[Optional[str], Optional[str]]:
    with lock_navegador:
        driver = None
        try:
            driver = _criar_driver_stf()
            return _raspar_stf(driver, id_nome, url)
        except Exception as e:
            print(f'   ❌ Erro detalhado no STF ({id_nome}): {e}')
            return None, None
        finally:
            if driver:
                driver.quit()


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
                    print(f'   ❌ Erro detalhado no STF ({id_nome}): {e}')
        except Exception as e:
            print(f'   ❌ Erro fatal STF batch: {e}')
        finally:
            if driver:
                driver.quit()
        return resultados


# ── TSE ─────────────────────────────────────────────────────────────────────

def extrair_tse_stealth(
    id_nome: str,
    url: str,
    numero: str,
    on_captcha: Callable[[str], None] = lambda n: None,
) -> Tuple[Optional[str], Optional[str]]:
    with lock_navegador:
        print(f'   📡 {id_nome}: Acessando TSE...')
        driver = None
        try:
            options = uc.ChromeOptions()
            options.add_argument('--disable-gpu')
            options.page_load_strategy = 'none'
            driver = uc.Chrome(options=options, version_main=VERSAO_CHROME_VM)

            on_captcha(numero)
            driver.get(url)

            card_alvo = None
            tempo_limite = 300
            tempo_inicial = time.time()

            print(f'      [!] Aguardando resolução do captcha na tela (limite 5 min)...')
            while time.time() - tempo_inicial < tempo_limite:
                try:
                    cards = driver.find_elements(By.CLASS_NAME, 'tramitacao-card')
                    card_alvo = next(
                        (c for c in cards if 'Movimentos' in c.text and 'Documentos' not in c.text),
                        None,
                    )
                    if card_alvo and len(card_alvo.text.strip()) > 50:
                        print(f'      ✅ {id_nome}: Dados carregados após resolução do captcha!')
                        break
                except Exception:
                    pass
                time.sleep(3)

            if not card_alvo:
                print(f'      ❌ {id_nome}: Tempo esgotado aguardando resolução do captcha.')
                return None, None

            time.sleep(2)
            print_path = f'print_{id_nome}.png'
            card_alvo.screenshot(print_path)

            linhas = [
                l.strip()
                for l in card_alvo.text.split('\n')
                if len(l.strip()) > 3 and l.strip().lower() != 'autorenew'
            ]
            return '\n'.join(linhas[:15]), print_path

        except Exception as e:
            print(f'   ❌ Erro ao extrair TSE ({id_nome}): {e}')
            return None, None
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass


def extrair_tse_stealth_batch(
    processos: list,
    on_captcha=None,
) -> list:
    with lock_navegador:
        n = len(processos)
        print(f'   📡 TSE: Abrindo navegador para {n} processo(s)...')
        driver = None
        resultados = [(None, None)] * n
        try:
            options = uc.ChromeOptions()
            options.add_argument('--disable-gpu')
            options.page_load_strategy = 'none'
            driver = uc.Chrome(options=options, version_main=VERSAO_CHROME_VM)

            for idx, (id_nome, url, numero) in enumerate(processos):
                print(f'   📡 {id_nome}: Acessando TSE...')
                try:
                    if on_captcha:
                        on_captcha(numero)
                    driver.get(url)

                    card_alvo = None
                    tempo_limite = 300
                    tempo_inicial = time.time()

                    print(f'      [!] Aguardando resolucao do captcha na tela (limite 5 min)...')
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

                    time.sleep(2)
                    print_path = f'print_{id_nome}.png'
                    card_alvo.screenshot(print_path)

                    linhas = [
                        l.strip()
                        for l in card_alvo.text.split('\n')
                        if len(l.strip()) > 3 and l.strip().lower() != 'autorenew'
                    ]
                    resultados[idx] = ('\n'.join(linhas[:15]), print_path)
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
