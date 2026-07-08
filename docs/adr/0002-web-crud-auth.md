# ADR 0002 — Web CRUD com autenticação (painel hoje é só log)

- **Status**: PROPOSED (spike; implementação pendente de aceite + decisão de auth)
- **Date**: 2026-07-08
- **Deciders**: Leandro (operador) + agente
- **Related plan**: `plans/016-spike-web-crud-auth.md`

## Context

O `web_panel.py` expõe apenas duas rotas GET (`/` e `/stream`,
`web_panel.py:126-140`) e serve exclusivamente o log SSE. O Flask roda
em `127.0.0.1:8080` (`web_panel.py:154`), então o loopback é a única
proteção hoje.

Mas a `service layer` em `repo.py` já oferece CRUD completo:
`add_processo` (linha 271), `delete_processo` (297), `save_andamento`
(230), `get_historico_contexto` (323), `list_todos` (215),
`get_processo` (168). E o bot tem um wizard de 8 passos por processo
(`bot_handlers.py:119-242`) para cadastrar — tedioso para o operador
adicionar vários de uma vez.

Isso é o "adjacent possible" (Seth Godin): a infra de persistência
existe, falta só rota+template+auth para o operador ter uma interface
mais rápida que o bot.

**Por que um spike e não um build**: adicionar rotas POST mutativas
sem autenticação em Flask expõe mutação a qualquer coisa no
localhost. O spike define o modelo de auth ANTES de criar a primeira
rota de escrita, evitando o anti-pattern de "primeiro faço, depois
tranco" (toda rota escrita antes do auth exige retrofit).

## Decision drivers

- O painel atual (`/`) é decorativo (terminal verde, SSE). CRUD é
  funcional — não precisa da mesma estética. São páginas separadas.
- O operador roda localmente, sem rede exposta, mas mesmo assim
  qualquer processo local (extensão do Chrome, malware, dev server
  exposto por engano) conseguiria mutar o banco. Auth reduz a
  superfície de ataque a "algo com o token".
- O `TOKEN_TELEGRAM` é altamente sensível (compromete toda a
  operação). Não pode ser o mesmo token usado no navegador
  (cookies/logs).
- Flask não tem CSRF por padrão. Rotas POST sem CSRF token são
  vulneráveis a form-submission forjada de outro site. Mesmo em
  loopback, isso é higiene mínima.
- Fase 6 (DX + testes) já criou rede para testar `web_panel` —
  os planos de implementação pós-ADR já podem incluir testes E2E
  com `Flask` test client.

## Current state (evidência)

- `web_panel.py:126-140` — 2 rotas GET (`/`, `/stream`). Sem
  `POST`/`PUT`/`DELETE`.
- `web_panel.py:154` — `app.run(host='127.0.0.1', port=...)`. Loopback.
- `repo.py:271-307` — `add_processo` e `delete_processo` prontos.
- `bot_handlers.py:119-242` — wizard de 8 passos para cadastrar
  (8 mensagens por processo).
- `web_panel.py:11` — `app = Flask(__name__)` sem `SECRET_KEY` nem
  `session` configurado. Estado de auth (cookie de sessão) não é
  viável sem essa config.

Não há nenhuma rota escondida — `Select-String -Path web_panel.py
-Pattern "@app.route"` retorna apenas as 2 GETs.

## Rotas propostas

### Read-only (próximo plano de implementação, sem auth ainda)

| Método | Rota | O que faz | Lê de |
|--------|------|-----------|-------|
| GET | `/` | Terminal SSE (status quo) | — |
| GET | `/stream` | SSE log (status quo) | `fila_web` |
| GET | `/processos` | Lista todos os processos (tabela) | `repo.list_todos()` |
| GET | `/processos/<pid>` | Detalhe + histórico de contexto | `repo.get_processo(pid)` + `repo.get_historico_contexto(pid)` |

`/processos` é seguro sem auth: é read-only, e hoje o `web_panel.py`
já é só read-only. Adicionar uma rota GET não muda a superfície de
ataque.

### Write (BLOQUEADO até auth + CSRF)

| Método | Rota | O que faz | Chama |
|--------|------|-----------|-------|
| POST | `/processos/add` | Form → cria processo | `repo.add_processo(...)` |
| POST | `/processos/<pid>/edit` | Form → edita campos permitidos | `repo.update_processo(pid, **campos)` (Plano 017) |
| POST | `/processos/<pid>/delete` | Remove processo + histórico | `repo.delete_processo(pid)` — **BLOQUEADO até auth+CSRF+teste** |

A rota `/processos/<pid>/delete` é listada aqui apenas para marcar
**explicitamente** que está fora de escopo até:

1. Auth middleware existir e ter teste.
2. CSRF token (sincronizado ou via `Flask-WTF`) existir e ter teste.
3. Plano de testes E2E cobrir pelo menos o caminho "login → delete".

Razão do bloqueio: `delete_processo` é irreversível e remove também
o histórico de contexto. Aberto a mutação por qualquer coisa no
localhost, o risco de exclusão acidental (extensão, dev server
exposto, devtools) é inaceitável.

### Esqueleto (apenas ilustração, NÃO commit)

```python
# web_panel.py (ilustrativo — não commitar este código)
from functools import wraps
from flask import abort, request, session, redirect, url_for

WEB_PANEL_TOKEN = os.getenv("WEB_PANEL_TOKEN")  # novo; ver §Auth
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "change-me")

def _require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Token via header OU sessão de cookie
        token = request.headers.get("X-Auth-Token") or session.get("authed")
        if not token or token != WEB_PANEL_TOKEN:
            abort(401)
        return f(*args, **kwargs)
    return wrapper

@app.route("/processos")
def listar_processos():
    processos = repo.list_todos()
    return render_template("processos_lista.html", processos=processos)

@app.route("/processos/<pid>")
def detalhe_processo(pid):
    proc = repo.get_processo(pid)
    if not proc:
        abort(404)
    historico = repo.get_historico_contexto(pid)
    return render_template("processo_detalhe.html", proc=proc, historico=historico)

# BLOQUEADO até auth + CSRF
# @app.route("/processos/<pid>/delete", methods=["POST"])
# @_require_auth
# def deletar_processo(pid):
#     repo.delete_processo(pid)
#     return redirect(url_for("listar_processos"))
```

## Modelo de autenticação

### Opções

(a) **Token via header `X-Auth-Token` comparado a `WEB_PANEL_TOKEN`
(env)**:
- Prós: zero estado no servidor (stateless), trivial de testar com
  `Flask.test_client()`, protege contra qualquer coisa no localhost
  que não tenha o token, simples de implementar (`@_require_auth`
  decorator), fácil de revogar (rotacionar env).
- Contras: precisa ser passado manualmente em cada request (não
  funciona com `<form>` HTML tradicional sem JS). Solução:
  cookie de sessão após "login" inicial (login = `POST /login` com
  token → seta cookie de sessão).
- **Recomendação**: token via env + cookie de sessão após login.
  O token fica em env (não em cookie); o cookie é assinado pelo
  `SECRET_KEY` do Flask (já tem como rodar assim).

(b) **Basic Auth com `WEB_PANEL_PASSWORD` (env)**:
- Prós: trivial; browser mostra prompt nativo; nenhum JS necessário.
- Contras: senha trafega em header (TLS local é OK mas o costume é
  ruim); browser pode cachear a credencial; revogação exige mudar
  env e reabrir o navegador em todo lugar.
- Não recomendado: a UX do prompt nativo do browser é hostil, e
  "esquecer a senha" não tem fluxo de recovery.

(c) **Loopback-only sem auth (status quo)**:
- Prós: zero código.
- Contras: qualquer processo local pode mutar o banco. Mesmo com
  o operador sendo o único usuário, o custo do auth é baixo e o
  benefício é alto. **Não recomendado**.

### Decisão recomendada: (a)

`X-Auth-Token` via env (`WEB_PANEL_TOKEN`) + cookie de sessão após
login manual (`POST /login` com token). `SECRET_KEY` do Flask vem de
`FLASK_SECRET` (separado de `WEB_PANEL_TOKEN`).

## Open questions (bloqueiam implementação)

1. **[B]** Auth reusa `ADMIN_ID`/`TOKEN_TELEGRAM` ou token novo
   (`WEB_PANEL_TOKEN`)?
   - Reusar: operador decora menos envs; mas `TOKEN_TELEGRAM` no
     browser = desastre (qualquer XSS rouva o bot inteiro).
   - **Recomendação**: novo (`WEB_PANEL_TOKEN`). Separação de
     superfície: token do bot fica só no servidor; token do painel
     só no navegador. Comprometimento de um não afeta o outro.

2. **[B]** Templates: manter o aesthetic "terminal verde" ou página
   CRUD separada?
   - Manter: uma página só, visual coerente; mas CRUD fica ilegível
     (terminal mono-espaçado não combina com tabela).
   - **Recomendação**: página CRUD separada (`/processos`,
     `/processos/<pid>`), visual funcional (Bootstrap básico ou
     HTML cru). O terminal verde continua em `/`. São páginas
     diferentes, esperam-se UX diferentes.

3. **[B]** CSRF via `Flask-WTF` ou token sincronizado manual?
   - `Flask-WTF`: lib externa, depende de `SECRET_KEY`, protege
     forms HTML automaticamente.
   - Token manual: injetar `<input type="hidden" name="csrf_token"
     value="{{ session.csrf }}">` em cada form, validar no handler.
   - **Recomendação**: começar com token manual (zero deps novas);
     trocar para `Flask-WTF` se o nº de forms crescer.

4. Login flow: página `/login` com campo único de token, ou login
   via URL `?token=...` (one-shot, registra cookie)?
   - Form: precisa de form + CSRF (boomerang).
   - URL param: simples, mas o token fica em histórico/logs.
   - **Recomendação**: form simples (campo de token + botão
     "Entrar"). Cookie de sessão expira em 7 dias, sem "remember
     me" (operador é único usuário; basta abrir o navegador de
     novo).

5. Onde guardar o token de sessão? `Flask.session` padrão (cookie
   assinado) ou token próprio em DB? **Recomendação**: `Flask.session`
   padrão. Stateless e suficiente para 1 usuário.

6. Rate-limit no `/login`? Brute-force do token é viável se o token
   for curto. **Recomendação**: token ≥32 chars random
   (`secrets.token_urlsafe(32)`); sem rate-limit explícito (loopback
   + token de 32 chars = 128 bits = inviável brute-force).

7. Logout? Botão "Sair" no header ou timeout puro? **Recomendação**:
   botão "Sair" simples (`POST /logout` que limpa sessão). Útil se
   o operador compartilhar a máquina.

## Risks

- **Risco de expor o `TOKEN_TELEGRAM` no browser**: mitigado pela
  decisão de `WEB_PANEL_TOKEN` separado. Documentar em `.env.example`
  que são tokens diferentes.
- **Risco de session fixation**: o `SECRET_KEY` do Flask precisa ser
  fixo entre reboots, senão todas as sessões caem a cada restart.
  Solução: `FLASK_SECRET` em env, com fallback explícito para erro
  (não usar default fraco silencioso).
- **Risco de CSRF em form de delete**: enquanto `/delete` está
  bloqueado, o risco é zero. Quando destravar, CSRF é
  pré-requisito.
- **Risco de `SECRET_KEY` fraco**: Flask avisa em dev se for a string
  padrão. Em prod, o operador precisa gerar um (`python -c "import
  secrets; print(secrets.token_hex(32))"`).

## Consequences

### Positivas

- Operador cadastra processos via form (3 cliques vs 8 mensagens no
  bot).
- Service layer (`repo.py`) já está pronta e testada — a UI é só
  a camada fina por cima.
- O modelo de auth (token + sessão) é genérico e pode ser estendido
  para outras rotas de admin no futuro (ex: rota para forçar ciclo
  de scraping, rota para ver logs com mais granularidade).

### Negativas

- Mais código em `web_panel.py` (já tem 146 linhas; vai crescer).
- `SECRET_KEY` é uma env nova para o operador configurar.
- `/delete` continua bloqueado por design, o que limita o "CRUD
  completo" prometido pelo título. (Intencional.)

### Neutras

- Templates vão precisar de assets (CSS). Hoje o painel inteiro é
  HTML inline; as páginas CRUD podem usar `templates/` separado
  ou inline com `<style>`. Decisão de estilo fica no plano de
  implementação.

## Implementation plan (próximos planos, fora deste spike)

1. **Plano 016a** (read-only + auth scaffold): adicionar
   `WEB_PANEL_TOKEN` e `FLASK_SECRET` ao `.env.example`; implementar
   `_require_auth` (decorator); criar `GET /login`, `POST /login`,
   `POST /logout`; criar `GET /processos` e `GET /processos/<pid>`.
   Testes com `Flask.test_client` cobrindo: auth sucesso, auth
   falha, lista vazia, lista com 1 processo, detalhe 404, detalhe
   sucesso.
2. **Plano 016b** (CSRF + write): adicionar CSRF manual (token na
   sessão + campo hidden no form); criar `POST /processos/add` (form
   completo: pid, numero, url, tribunal, parte_label, parte_nome,
   classe, resumo). NÃO criar `/delete`. Teste E2E cobrindo
   "login → add → ver na lista".
3. **Plano 016c** (delete, opcional, pós-Fase 7): só após o operador
   confirmar que auth + CSRF + add funcionam por ≥1 semana em
   produção. Teste de delete (com cleanup).

## References

- `web_panel.py:126-140` — 2 rotas GET atuais
- `web_panel.py:154` — loopback, porta 8080
- `repo.py:271-307` — `add_processo` e `delete_processo`
- `repo.py:215-228` — `list_todos` (usado em `/processos`)
- `repo.py:168-190` — `get_processo` (usado em `/processos/<pid>`)
- `repo.py:323-336` — `get_historico_contexto` (usado em
  `/processos/<pid>`)
- `bot_handlers.py:119-242` — wizard de cadastro (referência para o
  form)
- `plans/017-update-export-import.md` — adiciona `update_processo`
  (usado em `/processos/<pid>/edit`)
