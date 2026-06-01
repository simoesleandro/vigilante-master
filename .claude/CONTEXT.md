# Vigilante Master — Domain Glossary

## Terms

**Processo**
A judicial case under active monitoring. Identified by a short `pid` (e.g. `TJRJ_1`), a `tribunal`, a public case number, and a portal URL. Stored in the `processos` table.
_Avoid_: "case", "lawsuit" (use Processo).

**Andamento**
A captured text snapshot of the most recent movements extracted from a tribunal's portal for a Processo. The latest captured Andamento is stored in `ultimo_andamento`.
_Avoid_: "update", "event" (use Andamento).

**Andamento Inicial**
The very first Andamento captured for a Processo. Stored to establish a baseline; does NOT trigger a notification.

**Mudança**
A detected difference between the current Andamento and the previously stored one. Triggers a Carteiro notification and an AI Resumo Evolutivo update.
_Avoid_: "change", "diff" (use Mudança).

**Resumo Evolutivo**
An AI-maintained HTML summary of a Processo's current status. Updated automatically by the AnalisadorJuridico after each Mudança. Stored in `resumo_inicial`.

**Tribunal**
A court with its own scraping strategy:
- `TJRJ` — scraped with Playwright
- `STF` — scraped with undetected Chrome (stealth)
- `TSE` — scraped with undetected Chrome + manual Captcha resolution

**Captcha**
An anti-bot verification on the TSE portal requiring human intervention. Signaled to the operator via Telegram while the scraper waits (up to 5 minutes).

**Histórico de Contexto**
Lawyer-provided notes stored in the `historico_contexto` table. Injected into AI prompts to enrich strategic analysis.

**Vigilância**
The main monitoring loop: polls each Tribunal on a cycle, compares Andamentos, and dispatches effects on Mudança.

**Carteiro**
The Telegram dispatch worker. Reads from `fila_saida`, formats HTML notifications with inline keyboard, and sends to `CHATS_ESPECTADORES`.

**Falha de Captura**
A scraping failure for a specific Processo. After 5 consecutive failures, an admin alert is sent via Telegram.

## Module names introduced during refactoring

**ProcessoRepo**
The deep module encapsulating all Processo state in the SQLite database. Interface: named methods (`get_processo`, `save_andamento`, etc.). No caller opens a raw sqlite3 connection.

**Detector**
The pure comparison engine. Receives a `(proc, tribunal, txt, img)` tuple and returns one of: `Mudanca`, `AndamentoInicial`, `FalhaCaptura`, or `None`.

**AnalisadorJuridico**
The AI analysis module. Builds prompts from Processo context + Andamento + Histórico de Contexto, calls Gemini, returns clean text. Does not touch the database or Telegram.

## Relationships

- A **Tribunal** hosts many **Processos**
- A **Processo** has one current **Andamento** and one **Resumo Evolutivo**
- A **Processo** accumulates many **Histórico de Contexto** entries
- A **Mudança** is detected by the **Detector** and consumed by the **Vigilância** loop
- The **Carteiro** dispatches notifications triggered by **Mudanças**
- The **AnalisadorJuridico** is invoked on every **Mudança** to update the **Resumo Evolutivo**
