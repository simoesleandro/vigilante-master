# Vigilante Master - Contexto do Projeto

## Ambiente
- Roda em VM VirtualBox (Windows) no host do Leandro
- Disco VDI dinâmico: `C:\Users\stife\VirtualBox VMs\vigilante-windows\vigilante-windows.vdi`
- Python com Playwright (TJRJ), undetected-chromedriver (STF/TSE)
- Telegram bot para notificações

## Decisões Tomadas

### Limpeza de Disco (jun/2026)
- Playwright criava perfis órfãos no %TEMP% a cada ciclo (~720/dia)
- undetected_chromedriver (STF/TSE) criava `tmp*` que nunca eram limpos (principal vilão)
- `_LIMPEZA_PADROES` inclui: `playwright_*`, `chrome_drag*`, `tmp*`, `scoped_dir*`
- `_limpar_temp_playwright()` roda no `finally` de TJRJ, STF e TSE
- STF/TSE usam funções batch (`extrair_stf_stealth_batch`, `extrair_tse_stealth_batch`) que reutilizam 1 driver por tribunal em vez de 1 por processo
- `_limpar_screenshots_antigos()` remove PNGs com +24h
- `_limpar_chrome_cache()` limpa caches do Chrome a cada 500 ciclos
- Limpeza periódica: 30 ciclos (TEMP), 60 ciclos (screenshots), 500 ciclos (Chrome)
- Guard de disco: aborta ciclo se < 2 GB livres (configurável via DISCO_MIN_GB)

### Frequência TSE (jun/2026)
- Alterado de 10 para 15 ciclos (~30 min) para reduzir triggers de CAPTCHA
- CAPTCHA do TSE é manual via Telegram (risco alto de bloqueio de IP)

## Comandos Úteis

### Compactar VDI (no host, VM desligada)
```powershell
# 1. Na VM: zerar espaço livre
sdelete -z C:

# 2. No host: compactar
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" modifymedium --compact "C:\Users\stife\VirtualBox VMs\vigilante-windows\vigilante-windows.vdi"
```

### Limpeza manual emergencial (na VM)
```powershell
# Limpa tudo no TEMP
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

# Cache pip
pip cache purge

# Caches do Chrome (shaders, extensões, modelos)
$chromeData = "$env:LOCALAPPDATA\Google\Chrome\User Data"
@("GrShaderCache","ShaderCache","GPUCache","component_crx_cache","extensions_crx_cache","optimization_guide_model_store") | ForEach-Object {
    Remove-Item "$chromeData\$_" -Recurse -Force -ErrorAction SilentlyContinue
}

# Lixeira do Windows
Clear-RecycleBin -Force -ErrorAction SilentlyContinue

# Windows Update cleanup (libera vários GB)
Dism.exe /online /Cleanup-Image /StartComponentCleanup /ResetBase
```

## Estrutura
- `main.py` - Loop principal e orquestração
- `scrapers.py` - Extração de dados (TJRJ/STF/TSE)
- `detector.py` - Detecção de mudanças
- `analisador.py` - Análise com Gemini IA
- `carteiro.py` - Fila de envio Telegram
- `web_panel.py` - Painel Flask em localhost:5000
- `arquivo_historico/` - Versões antigas (v2-v13)
