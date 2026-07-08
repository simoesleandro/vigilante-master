<div align="center">

<img src="docs/screenshot.png" alt="Vigilante Master — Monitor de Processos Judiciais" width="100%">

<br/>

# Vigilante Master

**PT:** Monitor autônomo de processos judiciais — TJRJ, STF e TSE — com IA evolutiva, resumos automáticos e alertas via Telegram.  
**EN:** Autonomous judicial process monitor — TJRJ, STF and TSE — with evolutionary AI, automatic summaries and Telegram alerts.

<br/>

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-scraping-45ba4b?style=flat-square)](https://playwright.dev)
[![Selenium](https://img.shields.io/badge/Selenium-stealth-43B02A?style=flat-square&logo=selenium&logoColor=white)](https://selenium.dev)
[![Gemini](https://img.shields.io/badge/Gemini-3.1--Flash--Lite-4285F4?style=flat-square&logo=google)](https://aistudio.google.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/simoesleandro/vigilante-master?style=flat-square&color=8b5cf6)](https://github.com/simoesleandro/vigilante-master/commits)

<br/>

[🐛 Reportar bug](https://github.com/simoesleandro/vigilante-master/issues) &nbsp;·&nbsp;
[💡 Sugerir feature](https://github.com/simoesleandro/vigilante-master/issues)

</div>

---

## 📋 Índice / Table of Contents

- [Sobre](#-sobre--about)
- [Funcionalidades](#-funcionalidades--features)
- [Tribunais monitorados](#️-tribunais-monitorados--monitored-courts)
- [Stack](#-stack)
- [Arquitetura](#-arquitetura--architecture)
- [Instalação](#-instalação--setup)
- [Variáveis de Ambiente](#-variáveis-de-ambiente--environment-variables)
- [Roadmap](#-roadmap)
- [Autor](#-autor--author)

---

## 📌 Sobre / About

**PT:**  
Vigilante Master monitora processos judiciais nos principais tribunais brasileiros de forma autônoma. Usa Playwright e Selenium Stealth para scraping das páginas processuais, Gemini para gerar resumos evolutivos dos andamentos e Telegram Bot para notificações em tempo real quando há novos movimentos. Arquitetura modular com 9 módulos especializados.

**EN:**  
Vigilante Master autonomously monitors judicial processes in Brazil's major courts. Uses Playwright and Selenium Stealth for scraping procedural pages, Gemini to generate evolutionary summaries of case updates and Telegram Bot for real-time notifications when new movements occur. Modular architecture with 9 specialized modules.

---

## ✨ Funcionalidades / Features

- ✅ **Monitoramento autônomo** — ciclos automáticos de verificação por processo
- ✅ **Multi-tribunal** — TJRJ, STF e TSE em um único sistema
- ✅ **Scraping anti-detecção** — Playwright + Selenium Stealth para sites com proteção
- ✅ **Resumos com IA** — Gemini gera resumos evolutivos dos andamentos processuais
- ✅ **Alertas Telegram** — notificação imediata de novos movimentos
- ✅ **Screenshots automáticos** — captura visual de cada movimentação detectada
- ✅ **Histórico persistente** — SQLite com todos os andamentos e resumos
- ✅ **Web panel** — painel web para acompanhamento dos processos monitorados
- ✅ **Arquitetura modular** — 9 módulos independentes e testáveis

---

## ⚖️ Tribunais monitorados / Monitored Courts

| Tribunal | Cobertura |
|----------|-----------|
| **TJRJ** | Tribunal de Justiça do Estado do Rio de Janeiro |
| **STF** | Supremo Tribunal Federal |
| **TSE** | Tribunal Superior Eleitoral |

---

## 🛠 Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.12+ |
| Scraping | Playwright · Selenium Stealth |
| IA | Gemini 3.1 Flash Lite (resumos evolutivos) |
| Notificações | Telegram Bot API |
| Banco | SQLite |
| Web Panel | Flask + HTML/CSS |
| Automação | Loop autônomo com intervalos configuráveis |

---

## 🏗 Arquitetura / Architecture

```
vigilante-master/
├── main.py                # Entry point — loop principal
├── detector.py            # Detecção de novos andamentos
├── analisador.py          # Análise e resumo com Gemini
├── scrapers.py            # Scraping TJRJ / STF / TSE
├── carteiro.py            # Envio de alertas Telegram
├── repo.py                # Persistência SQLite
├── bot_handlers.py        # Handlers do bot Telegram
├── output_stream.py       # Stream de saída unificado
├── web_panel.py           # Painel web Flask
└── arquivo_historico/     # Versões anteriores arquivadas no histórico git (git log -- arquivo_historico/)
```

**Fluxo principal:**

```
Loop autônomo (intervalo configurável)
      ↓
scrapers.py — acessa tribunal via Playwright/Selenium
      ↓
detector.py — compara andamentos com histórico SQLite
      ↓
analisador.py — Gemini gera resumo evolutivo
      ↓
carteiro.py — envia alerta Telegram + screenshot
      ↓
repo.py — persiste andamento no banco
```

---

## 🚀 Instalação / Setup

### Pré-requisitos / Prerequisites

- Python 3.12+
- Playwright instalado — `playwright install chromium`
- Chave Gemini (gratuita em [aistudio.google.com](https://aistudio.google.com))
- Bot Telegram configurado

### Instalação / Installation

```bash
# Clone o repositório
git clone https://github.com/simoesleandro/vigilante-master
cd vigilante-master

# Instale as dependências
pip install -r requirements.txt
playwright install chromium

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves e números de processo

# Rode o monitor
python main.py
```

### Verificar / Verify

```bash
# Lint (ruff)
ruff check .

# Testes / Tests
python -m pytest tests/ -q
```

---

## 🔐 Variáveis de Ambiente / Environment Variables

| Variável | Descrição |
|----------|-----------|
| `TOKEN_TELEGRAM` | Token do bot Telegram (alertas) |
| `ADMIN_ID` | `chat_id` numérico do administrador (comandos mutativos só este chat) |
| `CHATS_ESPECTADORES` | IDs de destinatários só-leitura + IA, separados por vírgula |
| `API_KEY_GEMINI` | Chave do Google Gemini (resumos evolutivos) |
| `DISCO_MIN_GB` | Espaço mínimo em disco (GB) — aborta ciclos se abaixo disso (default 2) |
| `FLASK_PORT` | Porta do painel web Flask (default 8080) |

> Lista completa em: [`.env.example`](.env.example)

**Nota:** Processos são gerenciados via bot Telegram (`/adicionar`, `/remover`)
e persistidos em SQLite; o intervalo entre ciclos é fixo (2 min).

---

## 🗺 Roadmap

- [x] Monitoramento TJRJ, STF e TSE
- [x] Scraping com Playwright + Selenium Stealth
- [x] Resumos evolutivos com Gemini
- [x] Alertas Telegram com screenshots
- [x] Arquitetura modular (9 módulos)
- [x] Web panel para acompanhamento
- [ ] Suporte a novos tribunais (TRF, TRT)
- [ ] Interface web completa de gestão
- [ ] Relatório mensal por processo
- [ ] Deploy como serviço Windows (WinSW)

---

## 👤 Autor / Author

<div align="center">

**Leandro Simões**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/leandro-sim%C3%B5es-7a0b3537b)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/simoesleandro)
[![Portfolio](https://img.shields.io/badge/Portfolio-06b6d4?style=flat-square&logo=safari&logoColor=white)](https://simoesleandro.github.io/portfolio)

*Fullstack · IA Aplicada · Civic Tech*

</div>

---

<div align="center">

Feito com ☕ e IA em / Made with ☕ and AI in 🇧🇷 Rio de Janeiro

</div>
