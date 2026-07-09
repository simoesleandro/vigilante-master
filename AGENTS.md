# Vigilante Master - Contexto do Projeto

## Ambiente
- Roda direto no desktop Windows do Leandro (não usa mais VM)
- Python 3.12 com Playwright (TJRJ), undetected-chromedriver (STF/TSE), Flask, google-genai
- Telegram bot para notificações
- SQLite local (`memoria_vigilante.db`)
- Web panel em `http://localhost:<FLASK_PORT>` (default 5000 — ver Pendências)

## Decisões Tomadas

### Limpeza de Disco (jun/2026)
- Playwright criava perfis órfãos no %TEMP% a cada ciclo (~720/dia)
- undetected_chromedriver (STF/TSE) criava `tmp*` que nunca eram limpos (principal vilão)
- `_LIMPEZA_PADROES` inclui: `playwright_*`, `chrome_drag*`, `tmp*`, `scoped_dir*`
- `_limpar_temp_playwright()` roda no `finally` de TJRJ, STF e TSE
- STF/TSE usam funções batch que reutilizam 1 driver por tribunal em vez de 1 por processo
- `_limpar_screenshots_antigos()` remove PNGs com +24h
- `_limpar_chrome_cache()` limpa caches do Chrome a cada 500 ciclos
- Limpeza periódica: 30 ciclos (TEMP), 60 ciclos (screenshots), 500 ciclos (Chrome)
- Guard de disco: aborta ciclo se < 2 GB livres (configurável via `DISCO_MIN_GB`)

### Frequência TSE (jun/2026)
- Alterado de 10 para 15 ciclos (~30 min) para reduzir triggers de CAPTCHA
- CAPTCHA do TSE é manual via Telegram (risco alto de bloqueio de IP)

### Smart App Control + Chrome (jul/2026)
- Chrome auto-atualiza; `VERSAO_CHROME_VM` em `scrapers.py` precisa acompanhar (ex: 150)
- `undetected_chromedriver` patcha o `chromedriver.exe` (remove vars `cdc_`), quebrando a assinatura digital
- Smart App Control (SAC) do desktop bloqueia binários não-assinados → WinError 4551
- SAC desativado: registro `HKLM\...\CI\Policy\VerifiedAndReputablePolicyState = 0` + `CiTool --refresh` (elevado)
- SAC é irreversível (não reativa sem resetar Windows) — tradeoff aceito pois o `undetected_chromedriver` exige
- Se após reboot o chromedriver voltar a ser bloqueado (WinError 4551), rodar elevado: `CiTool --refresh` (registro já está em 0)
- STF roda headless (invisível) com `--window-position=-32000,-32000` como safety-net; TSE roda headed (reCAPTCHA manual via Telegram)

### Melhorias aplicadas (jul/2026) — 7 fases, 8 commits

**Fase 1 — Segurança** (`685ead8`)
- TLS reativado: removido `ssl._create_default_https_context = _create_unverified_context` (certifi patch basta; smoke test: Telegram + Gemini conectam com verificação real)
- Comandos mutativos (`/remover`, `/adicionar`, `/reenviar`, `/editar`, `/exportar`) gateados por `ADMIN_ID`; espectadores só leem
- XSS no painel web fechado: `digitarTexto` usa `createTextNode`/`appendChild` (zero `innerHTML`)
- Carteiro: escape de `numero`/`tribunal`/`classe`/`parte_label`/`parte_nome` + validação de scheme da URL (rejeita `javascript:`)
- Vazamento de exceção IA no chat → log servidor + mensagem genérica

**Fase 2 — Persistência** (`e9adbe5`)
- SQLite: `PRAGMA journal_mode=WAL` + `busy_timeout=5s` em todas as conexões
- Todos os 10 métodos + `_inicializar_banco` refatorados para `try/finally` (fecha conexão sempre)
- Resumo protegido: coluna `resumo_evolutivo` separada (humano em `resumo_inicial` imutável); `get_processo` retorna `resumo` = evoluto ou inicial
- Guard anti-vazio em `save_resumo`: se Gemini falha, resumo anterior preservado
- Fila web (`fila_web`) com `maxsize=2000` + `put_nowait` (descarta quando cheia, sem bloquear o produtor)

**Fase 3 — Robustez do bot** (`1c80bb0`)
- Wizard `/adicionar`: guard `if not message.text:` nos 8 steps (evita crash em foto/sticker)
- Polling Telegram: backoff 5s→300s em erros não-409 com reset em sucesso (antes: `break` matava o bot)
- TSE thread: guard `is_alive()` antes de startar novo thread (evita empilhar batches lentas)

**Fase 4 — Eficiência do scraping** (`565af30`)
- TJRJ batch: `extrair_playwright_batch(processos)` reusa 1 Chromium para todos os processos (antes: 1 Chromium por processo = 4 cold-starts/ciclo)
- STF: `WebDriverWait(15)` no seletor `.andamento-item, app-andamento` (antes: `time.sleep(10)` fixo)
- `exterminar_zumbis()` gated em `cnt % 30 == 0 and cnt > 0` (antes: todo ciclo)

**Fase 5 — Tech debt + Docs** (`57a283c`)
- Removidos `extrair_stf_stealth` e `extrair_tse_stealth` (mortos, ~80 linhas)
- `git rm -r arquivo_historico/` (10 arquivos v2-v13, ~3.9k linhas, preservados no histórico git)
- `README.md`: badges Python 3.12 + Gemini 3.1 Flash Lite, tabela de env vars reais (6), nota sobre processos via bot
- `.env.example`: removido `TELEGRAM_CHAT_ID` morto, adicionados `ADMIN_ID` e `FLASK_PORT`
- `AGENTS.md`: 9 módulos (era 6), porta 8080

**Fase 6 — DX + Testes** (`eb5b9c5`)
- `pyproject.toml` novo: `[tool.ruff]` (select E/F/W/I/UP/B/SIM, ignore E501, quote-style preserve) + `[tool.pytest.ini_options]` (testpaths=tests, addopts=-q)
- `ruff --fix --select F` corrigiu F401 (imports não usados) + F541 (f-strings sem placeholders) reais
- `montar_mensagem` extraído de `carteiro_worker` (função pura testável, urlparse movido pro top)
- `tests/test_carteiro.py` novo: 6 testes (truncation, chars especiais, parte_nome com HTML, sem/com foto)

**Fase 7 — Direções + features** (`943b6b6`)
- `repo.update_processo(pid, **campos)` com whitelist (numero/url/tribunal/parte_label/parte_nome/classe)
- `repo.exportar()` + `repo.importar(dados)` (idempotente, preserva contexto)
- Bot: `/editar`, `/exportar` (send_document), `/importar` (document handler) — todos admin-only
- Wording crash: "A Máquina Virtual/Acesse a VM" → "O monitor/Reinicie `python main.py` no desktop"
- 3 ADRs novos: `docs/adr/0001-tribunal-abstraction.md` (desbloqueia TRF/TRT), `0002-web-crud-auth.md`, `0003-deploy-winsw.md` (design pendente de decisão)

**Fix STF off-screen** (`f4c02e1`)
- `_criar_driver_stf`: adicionado `--window-position=-32000,-32000` (garantia de invisibilidade mesmo se `--headless=new` falhar)

## Estado Operacional

- **main branch** em `f4c02e1` (todos os 8 commits mergeados e pushed)
- **27 testes passando** (16 originais + 6 carteiro + 3 update/export/import + 2 save_resumo)
- **9 módulos** em produção
- **Sistema validado** com 100+ ciclos contínuos (~3.5h+ uptime sem crash)
- **Smart App Control desativado** (tradeoff aceito pelo undetected_chromedriver)

## Comandos Úteis

### Verificação / Verify
```bash
# Lint (ruff)
ruff check .

# Testes
python -m pytest tests/ -q
```

### Diagnóstico
```bash
# SAC: confirmar desativado
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -Name VerifiedAndReputablePolicyState
# Esperado: 0

# Se o chromedriver for bloqueado (WinError 4551) após reboot:
# Elevado: CiTool --refresh
```

### Limpeza manual emergencial (no desktop)
```powershell
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
pip cache purge
$chromeData = "$env:LOCALAPPDATA\Google\Chrome\User Data"
@("GrShaderCache","ShaderCache","GPUCache","component_crx_cache","extensions_crx_cache","optimization_guide_model_store") | ForEach-Object {
    Remove-Item "$chromeData\$_" -Recurse -Force -ErrorAction SilentlyContinue
}
Clear-RecycleBin -Force -ErrorAction SilentlyContinue
Dism.exe /online /Cleanup-Image /StartComponentCleanup /ResetBase
```

### Banco de dados
```bash
# Verificar WAL ativo
sqlite3 memoria_vigilante.db "PRAGMA journal_mode"
# Esperado: wal
```

## Estrutura

### Módulos de produção
- `main.py` - Loop principal e orquestração (288→340 linhas após Fase 7)
- `scrapers.py` - Extração TJRJ/STF/TSE (com batch + `_raspar_tjrj` helper + `WebDriverWait` STF)
- `detector.py` - Detecção de mudanças (limite_alerta=5 falhas consecutivas)
- `analisador.py` - Análise com Gemini IA (modelos: `gemini-3.1-flash-lite`, `gemini-flash-latest`)
- `carteiro.py` - Fila de envio Telegram (com `montar_mensagem` extraído)
- `repo.py` - Persistência SQLite (WAL, try/finally, update/export/import)
- `bot_handlers.py` - Handlers do bot Telegram (com admin gate + wizard guard + export/import)
- `output_stream.py` - Stream de saída unificado (UTF-8 forçado, `fila_web` com maxsize=2000)
- `web_panel.py` - Painel Flask (loopback 127.0.0.1, `textContent` sem XSS)

### Configuração e testes
- `pyproject.toml` - ruff + pytest config
- `tests/test_detector.py` - 7 testes (detector)
- `tests/test_repo.py` - 14 testes (repo, incluindo update/export/import + save_resumo round-trip)
- `tests/test_carteiro.py` - 6 testes (carteiro escaping/truncation)

### Design docs (ADRs — pendentes de decisão)
- `docs/adr/0001-tribunal-abstraction.md` - Protocolo `Tribunal` plugável (desbloqueia TRF/TRT do roadmap)
- `docs/adr/0002-web-crud-auth.md` - Web CRUD com auth (painel hoje é só log)
- `docs/adr/0003-deploy-winsw.md` - Deploy como serviço Windows (WinSW)

## Planos de Referência

Os **18 planos `.md`** que documentam cada mudança em detalhe (Current state, Steps, Verify, STOP conditions) estão em **dois lugares**:

1. **Working notes local** (preservado, NÃO commitado no repo): `C:\Meus_projetos\vigilante-plans-backup\` (19 arquivos, incluindo README) — pode deletar quando não precisar mais (1-2 semanas de cooldown recomendado)
2. **Histórico git** (permanente, no `main`): os 8 commits das fases (685ead8..f4c02e1) contam a história completa. O `plans/001-004 + plans/README.md` está commitado no `main` (parte do Fase 1); os 005-018 são working notes e não estão no repo.

Para inspecionar uma fase específica: `git log --oneline 685ead8..f4c02e1` ou `git show <commit>`.

## Pendências (decisão do Leandro)

1. **`.env` vs default de porta**: o `web_panel.py` default é `FLASK_PORT=8080`, mas o `.env` local tem `FLASK_PORT=5000` (resíduo histórico). Para alinhar com AGENTS.md/default: mudar `.env` para `FLASK_PORT=8080` e reiniciar o `main.py`.

2. **3 ADRs pendentes** (`docs/adr/`): tribunal plugável (0001), web CRUD+auth (0002), WinSW (0003) — são **designs**, não código. Quando decidir o que implementar, viram planos separados.

3. **2 issues menores do ruff** (relatados pelo `ruff check .` no `advisor/fase-7`, não corrigidos no escopo da Fase 6):
   - `bot_handlers.py:276` SIM105 — `try/except: pass` poderia usar `contextlib.suppress(Exception)`
   - `carteiro.py:1` I001 — import order não está sorted
   - Não-bloqueantes, podem ser fixados num commit de polimento.

4. **Backup dos plans** (`C:\Meus_projetos\vigilante-plans-backup\`): 19 arquivos de working notes. Deletar quando não precisar mais.

5. **`VERSAO_CHROME_VM` em `scrapers.py:11`**: constante com "VM" no nome (cosmético). Pode ser renomeado para `VERSAO_CHROME` num commit de polimento.
