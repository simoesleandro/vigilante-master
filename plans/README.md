# Implementation Plans

Gerados pela skill `improve` em 2026-07-08 contra o commit `838a309`.
Execute na ordem por fase (dependências indicadas). Cada plano é auto-contido:
um executor sem contexto da sessão consegue seguir lendo só o arquivo + o repo.

Os planos são **aditivos** — não mexem no que funciona (STF headless,
TSE headed+captcha, TJRJ Playwright). Buscam segurança e eficiência máximas.

## Ordem de execução & status

### Fase 1 — Hardening de Segurança (P1)

| Plano | Título | Esforço | Risco | Depende de | Status |
|-------|--------|---------|-------|------------|--------|
| 001   | Reativar verificação TLS (remover `_create_unverified_context`) | S | MED | — | DONE |
| 002   | Gatear comandos privilegiados por ADMIN_ID + parar de vazar exceções ao chat | S | LOW | — | DONE |
| 003   | Mitigar XSS no painel web (`innerHTML`→`textContent`) | S | LOW | — | DONE |
| 004   | Escapar campos HTML no carteiro + validar scheme da URL | S | LOW | — | DONE |

### Fase 2 — Proteção do Resumo + Confiabilidade SQLite (P1)

| Plano | Título | Esforço | Risco | Depende de | Status |
|-------|--------|---------|-------|------------|--------|
| 006   | Confiabilidade SQLite: WAL + `busy_timeout` + `try/finally` | M | LOW | — | DONE |
| 005   | Proteger resumo: guard anti-vazio + coluna `resumo_evolutivo` separada | M | LOW/MED | 006 | DONE |
| 007   | Limitar `fila_web` (queue com `maxsize`) | S | LOW | — | DONE |

### Fase 3 — Robustez do Bot (P2)

| Plano | Título | Esforço | Risco | Depende de | Status |
|-------|--------|---------|-------|------------|--------|
| 008   | Robustez bot — wizard guard não-texto + retry polling + is_alive TSE | S | LOW | — | DONE |

### Fase 4 — Eficiência do Scraping (P2)

| Plano | Título | Esforço | Risco | Depende de | Status |
|-------|--------|---------|-------|------------|--------|
| 009   | TJRJ batch — reusar 1 Chromium para todos os processos | M | LOW-MED | — | DONE |
| 010   | WebDriverWait no STF + cadência do `exterminar_zombis` | S | LOW | — | DONE |

### Fase 5 — Tech Debt + Docs (P2)

| Plano | Título | Esforço | Risco | Depende de | Status |
|-------|--------|---------|-------|------------|--------|
| 011   | Limpeza tech debt — deletar scrapers single mortos + mover `arquivo_historico/` | S | LOW | 009 | DONE |
| 012   | Corrigir docs — README env vars + `.env.example` + AGENTS.md módulos/porta | S | LOW | — | DONE |

### Fase 6 — DX + Testes (P2)

| Plano | Título | Esforço | Risco | Depende de | Status |
|-------|--------|---------|-------|------------|--------|
| 013   | DX — adicionar ruff (lint+format) + config pytest + gate documentado | M | LOW | 011 | DONE |
| 014   | Teste do carteiro (escaping/truncation) — o caminho security-sensitive | S | LOW | 004 | DONE |

### Fase 7 — Direções (P3, spikes/design)

| Plano | Título | Esforço | Risco | Depende de | Status |
|-------|--------|---------|-------|------------|--------|
| 015   | Spike — abstração de Tribunal plugável (desbloqueia TRF/TRT) | L (spike M) | MED | 008,009,014 | TODO |
| 016   | Spike — Web CRUD com auth (painel hoje é só log) | M (spike S) | MED | 013 | TODO |
| 017   | `update_processo` + export/import (preenche o bulk-add perdido) | M | LOW | 006,002 | DONE |
| 018   | Limpar wording "VM" + spike WinSW (deploy como serviço Windows) | S+M | LOW/MED | — | TODO |

Status: TODO | IN PROGRESS | DONE | BLOCKED (motivo) | REJECTED (motivo)

## Notas de dependência

- **006 antes de 005**: ambos tocam `repo.py` (WAL/try-finally + coluna
  `resumo_evolutivo`); 006 primeiro evita conflito e garante que as novas
  escritas já rodem com WAL.
- **009 antes de 011**: 009 reorganiza `scrapers.py` (TJRJ batch); 011
  deleta os singles — ordem evita merge conflito.
- **011 antes de 013**: 013 não deve lintar código morto que 011 remove.
- **004 antes de 014**: o teste do carteiro documenta o comportamento pós-004
  (campos escapados); sem 004, os testes falham.
- **002, 006 antes de 017**: `/editar`/`/exportar`/`/importar` são admin-only
  (002) e usam o padrão try/finally (006).
- **008, 009, 014 antes de 015**: o spike de abstração de Tribunal só faz
  sentido após robustez + batch + testes (refatorar o dispatcher é arriscado
  sem rede).
- Independentes (paralelizáveis): 001, 002, 003, 004, 007, 008, 010, 012, 018.

## Achados considerados e rejeitados

- **TECH-23** (fazer `repo.py` propagar exceções em vez de engolir em
  `print`): adiado — mudar o contrato de exceção é observável por todos os
  callers (bot anuncia "cadastrado" sem persistir). Plano 006 faz só a parte
  segura (WAL + try/finally); a propagação fica como follow-up após Fase 6.
- **PERF-07** (headless contraditório do TJRJ: `headless=False` + `--headless=new`):
  adiado — interage com o Plan 009 (TJRJ batch copia os args) e a intenção é
  ambígua (TJRJ deveria ser headless? confirmar com o operador se aparece
  janela). Decidir depois de 009 mergeado. Registado no maintenance note do 010.
- **TECH-03** (god function `register_handlers` 340 linhas): refator grande,
  adiado para após Fase 6 (testes) — sem rede, quebrar o wizard é fácil.
- **DEPS-01/02** (requirements.txt = pip freeze; 4 libs websocket): migração
  para `requirements.in` + lock gerado é útil mas barulhenta; fazer após 013
  (ruff/DX) estar no lugar para não adicionar ruído. Não planejado por agora.
- **DOCS-04** (sem ADRs): parcialmente resolvido pelos spikes 015/016/018 que
  criam `docs/adr/`. Backfill de ADRs para SAC/TSE/desktop como follow-up.
