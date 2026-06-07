# 👁️ Vigilante Master

> Autonomous judicial process monitor with evolutionary AI, multi-court scraping, and real-time Telegram alerts.

---

## 📌 About

**Vigilante Master** is a continuous judicial process monitoring tool built as a portfolio project during my career transition into tech, with a focus on Systems Analysis and Development (FIAP).

The system runs 24/7 in the background, tracking case updates across multiple Brazilian courts (TJRJ, STF, TSE), comparing the current state against a locally stored history, and firing intelligent Telegram alerts the moment a change is detected — with AI-generated strategic analysis.

---

## ⚙️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   MAIN ENGINE                   │
│          Polling loop every 2 minutes           │
└──────────┬──────────────┬───────────────────────┘
           │              │
    ┌──────▼──────┐  ┌────▼────────┐
    │   SCRAPERS  │  │  TELEGRAM   │
    │  Playwright │  │  Bot + AI   │
    │  Selenium   │  │  Gemini API │
    └──────┬──────┘  └─────────────┘
           │
    ┌──────▼──────┐
    │   SQLite    │
    │  Evolutionary│
    │   Memory    │
    └─────────────┘
```

### Execution Flow

1. Each cycle fetches the monitored cases from SQLite
2. Scrapers access the court portals (Playwright for TJRJ, Selenium stealth for STF and TSE)
3. Extracted text is compared against the last saved update in the database
4. If a change is detected: Gemini AI updates the case's evolutionary summary and sends a Telegram alert with strategic analysis
5. The web dashboard (Flask + SSE) mirrors all logs in real time in the browser

---

## 🧠 Features

- **Multi-court monitoring** — TJRJ (Playwright), STF and TSE (undetected Selenium)
- **AI-powered evolutionary summaries** — Gemini automatically rewrites the case summary on every new update
- **Interactive strategic analysis** — the bot responds to commands with legal analysis crossing historical data and recent updates
- **Persistent memory** — case context and lawyer annotations stored in SQLite with full history per case
- **Hacker-style web dashboard** — green terminal interface with real-time SSE log streaming
- **Global airbag** — any crash triggers an automatic alert with full traceback to Telegram
- **Dynamic case registration via bot** — add, remove, and query cases directly from Telegram chat

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.x |
| Scraping | Playwright, Selenium + undetected-chromedriver |
| AI | Google Gemini API (`google-genai`) |
| Bot | pyTelegramBotAPI (telebot) |
| Database | SQLite3 (built-in) |
| Web Server | Flask + Server-Sent Events (SSE) |
| Concurrency | threading, queue (Producer-Consumer) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Google Chrome installed
- A Telegram bot created via [@BotFather](https://t.me/BotFather)
- A [Google AI Studio](https://aistudio.google.com/) API key

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/simoesleandro/vigilante-master.git
cd vigilante-master

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

```env
TOKEN_TELEGRAM=your_bot_token_here
ADMIN_ID=your_chat_id_here
CHATS_ESPECTADORES=id1,id2
API_KEY_GEMINI=your_api_key_here
```

### Running

```bash
python main.py
```

The web dashboard will be available at `http://localhost:8080`

---

## 📂 Project Structure

```
vigilante-master/
├── main.py                  # Application entrypoint
├── .env                     # Credentials (not versioned)
├── .env.example             # Environment variables template
├── .gitignore
├── requirements.txt
├── README.md                # Portuguese version
├── README.en.md             # English version
└── arquivo_historico/       # Previous script versions
```

---

## 💡 Architecture Decisions

**Why Producer-Consumer with `queue.Queue`?**
Telegram message delivery is decoupled from data extraction. The scraper produces alerts into the queue; the `carteiro_worker` consumes them sequentially. This prevents race conditions and respects the Telegram API rate limits.

**Why SQLite instead of an in-memory store?**
The case update history needs to survive script restarts. SQLite provides persistence without the overhead of an external database server — the right call for a personal production-grade project.

**Why separate threads for the bot, web server, and engine?**
Each subsystem has its own lifecycle. The bot must respond to commands in real time while the engine sleeps between 2-minute polling cycles. Daemon threads ensure the main process controls the lifecycle of all subsystems.

---

## 👤 Author

**Leandro Simões** — Developer transitioning into tech, studying Systems Analysis and Development (FIAP 2026).

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Leandro%20Sim%C3%B5es-blue?logo=linkedin)](https://www.linkedin.com/in/leandro-sim%C3%B5es-7a0b3537b/)
[![GitHub](https://img.shields.io/badge/GitHub-simoesleandro-black?logo=github)](https://github.com/simoesleandro)

---

## ⚠️ Legal Notice

This project was built for monitoring publicly available case data on official court portals. Usage is strictly personal and educational.
