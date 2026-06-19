# Vigilante Master - Contexto do Projeto

## Ambiente
- Roda em VM VirtualBox (Windows) no host do Leandro
- Disco VDI dinâmico: `C:\Users\stife\VirtualBox VMs\vigilante-windows\vigilante-windows.vdi`
- Python com Playwright (TJRJ), undetected-chromedriver (STF/TSE)
- Telegram bot para notificações

## Decisões Tomadas

### Limpeza de Disco (jun/2026)
- Playwright criava perfis órfãos no %TEMP% a cada ciclo (~720/dia)
- Implementado `_limpar_temp_playwright()` roda no `finally` do bloco TJRJ
- Implementado `_limpar_screenshots_antigos()` remove PNGs com +24h
- Limpeza periódica: a cada 30 ciclos (TEMP) e 60 ciclos (screenshots)
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
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
pip cache purge
Remove-Item "$env:LOCALAPPDATA\Google\Chrome\User Data\*\Cache\*" -Recurse -Force -ErrorAction SilentlyContinue
```

## Estrutura
- `main.py` - Loop principal e orquestração
- `scrapers.py` - Extração de dados (TJRJ/STF/TSE)
- `detector.py` - Detecção de mudanças
- `analisador.py` - Análise com Gemini IA
- `carteiro.py` - Fila de envio Telegram
- `web_panel.py` - Painel Flask em localhost:5000
- `arquivo_historico/` - Versões antigas (v2-v13)
