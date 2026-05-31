# 👁️ Vigilante Master

> Monitor autônomo de processos judiciais com IA evolutiva, scraping multi-tribunal e alertas em tempo real via Telegram.

---

## 📌 Sobre o Projeto

O **Vigilante Master** é uma ferramenta de monitoramento contínuo de processos judiciais desenvolvida como projeto de portfólio durante minha transição de carreira para a área de tecnologia, com foco em Análise e Desenvolvimento de Sistemas (FIAP).

O sistema roda 24/7 em background, rastreando movimentações em múltiplos tribunais (TJRJ, STF, TSE), comparando o estado atual com o histórico salvo em banco de dados local e disparando alertas inteligentes via Telegram assim que uma mudança é detectada — com análise estratégica gerada por IA.

---

## ⚙️ Arquitetura e Funcionamento

```
┌─────────────────────────────────────────────────┐
│                  MOTOR PRINCIPAL                │
│         Loop de ciclos a cada 2 minutos         │
└──────────┬──────────────┬───────────────────────┘
           │              │
    ┌──────▼──────┐  ┌────▼────────┐
    │  SCRAPERS   │  │  TELEGRAM   │
    │  Playwright │  │  Bot + IA   │
    │  Selenium   │  │  Gemini API │
    └──────┬──────┘  └─────────────┘
           │
    ┌──────▼──────┐
    │   SQLite    │
    │  Memória    │
    │  Evolutiva  │
    └─────────────┘
```

### Fluxo de execução

1. A cada ciclo, o motor busca os processos cadastrados no SQLite
2. Os scrapers acessam os portais dos tribunais (Playwright para TJRJ, Selenium stealth para STF e TSE)
3. O texto extraído é comparado com o último andamento salvo no banco
4. Se houver mudança: a IA (Gemini) atualiza o resumo evolutivo do processo e envia alerta via Telegram com análise estratégica
5. O painel web (Flask + SSE) espelha todos os logs em tempo real no navegador

---

## 🧠 Funcionalidades

- **Monitoramento multi-tribunal** — TJRJ (Playwright), STF e TSE (Selenium undetected)
- **Resumo evolutivo por IA** — o Gemini reescreve automaticamente o resumo do processo a cada nova movimentação
- **Análise estratégica interativa** — o bot responde a comandos com análise jurídica cruzando histórico + andamentos recentes
- **Memória persistente** — contexto e anotações do advogado salvas em SQLite com histórico por processo
- **Painel web hacker** — interface terminal verde com streaming SSE dos logs em tempo real
- **Airbag global** — qualquer crash envia alerta automático com traceback para o Telegram
- **Cadastro dinâmico via bot** — adicionar, remover e consultar processos direto pelo chat do Telegram

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.x |
| Scraping | Playwright, Selenium + undetected-chromedriver |
| IA | Google Gemini API (`google-genai`) |
| Bot | pyTelegramBotAPI (telebot) |
| Banco de Dados | SQLite3 (nativo) |
| Web Server | Flask + Server-Sent Events (SSE) |
| Concorrência | threading, queue (Producer-Consumer) |

---

## 🚀 Como Executar Localmente

### Pré-requisitos

- Python 3.10+
- Google Chrome instalado
- Conta no Telegram com um bot criado via [@BotFather](https://t.me/BotFather)
- Chave de API do [Google AI Studio](https://aistudio.google.com/)

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/simoesleandro/vigilante-master.git
cd vigilante-master

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Instale os navegadores do Playwright
playwright install chromium

# 5. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais
```

### Configuração do `.env`

```env
TOKEN_TELEGRAM=seu_token_do_bot_aqui
ADMIN_ID=seu_chat_id_aqui
CHATS_ESPECTADORES=id1,id2
API_KEY_GEMINI=sua_chave_aqui
```

### Execução

```bash
python main.py
```

O painel web estará disponível em `http://localhost:8080`

---

## 📂 Estrutura do Projeto

```
vigilante-master/
├── main.py                  # Entrypoint principal
├── .env                     # Credenciais (não versionado)
├── .env.example             # Template de variáveis
├── .gitignore
├── requirements.txt
├── README.md
└── arquivo_historico/       # Versões anteriores do script
```

---

## 💡 Decisões de Arquitetura

**Por que Producer-Consumer com `queue.Queue`?**
O envio de mensagens para o Telegram é desacoplado da extração dos dados. O scraper produz alertas na fila; o `carteiro_worker` consome de forma sequencial. Isso evita race conditions e respeita os rate limits da API do Telegram.

**Por que SQLite e não um banco em memória?**
O histórico de andamentos precisa sobreviver a reinicializações do script. O SQLite garante persistência sem a complexidade de um servidor de banco de dados externo — decisão adequada para o escopo de um projeto pessoal de produção.

**Por que threads separadas para o bot, o web server e o motor?**
Cada subsistema tem seu próprio ciclo de vida. O bot precisa responder a comandos em tempo real enquanto o motor dorme 2 minutos entre ciclos. Threads daemon garantem que o processo principal controla o ciclo de vida de todos.

---

## 👨‍💻 Autor

**Leandro** — Desenvolvedor em transição de carreira, estudante de Análise e Desenvolvimento de Sistemas (FIAP 2026).

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Leandro%20Sim%C3%B5es-blue?logo=linkedin)](https://www.linkedin.com/in/leandro-sim%C3%B5es-7a0b3537b/)
[![GitHub](https://img.shields.io/badge/GitHub-simoesleandro-black?logo=github)](https://github.com/simoesleandro)

---

## ⚠️ Aviso Legal

Este projeto foi desenvolvido para monitoramento de processos públicos disponíveis nos portais oficiais dos tribunais. O uso é estritamente pessoal e educacional.
