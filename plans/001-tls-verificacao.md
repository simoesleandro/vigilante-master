# Plan 001: Reativar verificação TLS (remover `_create_unverified_context`)

> **Executor instructions**: Siga o plano passo a passo. Rode cada comando de
> verificação e confirme o resultado antes de avançar. Se algo em "STOP
> conditions" ocorrer, pare e reporte — não improvise. Ao terminar, atualize
> a linha de status em `plans/README.md`.
>
> **Drift check (rodar primeiro)**: `git diff --stat 838a309..HEAD -- main.py`
> Se `main.py` mudou desde este plano, compare os excertos em "Current state"
> com o código vivo antes de prosseguir; em divergência, trate como STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MED
- **Depends on**: nenhum
- **Category**: security
- **Planned at**: commit `838a309`, 2026-07-08

## Why this matters

`main.py:32` substitui o contexto HTTPS default do processo inteiro por um
contexto **sem verificação de certificado**. Isso roda antes dos imports de
rede, então TODA chamada HTTPS — Gemini (que carrega `API_KEY_GEMINI` no
header) e Telegram (carrega `TOKEN_TELEGRAM`) — fica vulnerável a MITM na rede.
O patch de `certifi` nas linhas 29-31 é correto e suficiente; a linha 32 é um
marromelo que desativa a verificação global. Removê-la reativa a verificação
mantendo o workaround de cert store do Windows (linhas 19-31).

## Current state

- `main.py` — entry point; contém os patches SSL nas linhas 16-32.
- Excerto exato (linhas 16-32):
```python
# ── SSL patches ── devem rodar antes de qualquer import de rede ─────────────
_original_load_verify = ssl.SSLContext.load_verify_locations

def _patched_load_verify(self, cafile=None, capath=None, cadata=None):
    if cafile and not cadata:
        try:
            with open(cafile, 'r', encoding='utf-8') as f:
                cadata = f.read()
            cafile = None
        except Exception:
            pass
    return _original_load_verify(self, cafile=cafile, capath=capath, cadata=cadata)

ssl.SSLContext.load_verify_locations = _patched_load_verify
ssl.SSLContext.load_default_certs = lambda self, purpose=ssl.Purpose.SERVER_AUTH: \
    self.load_verify_locations(cafile=certifi.where())
ssl._create_default_https_context = ssl._create_unverified_context
```
- Convenção: o projeto usa `print(...)` para log em stdout (sem `logging`).
  Mensagens de erro seguem o padrão `print(f"⚠️ ...")`. Mantenha esse estilo.
- O `certifi` (linhas 12, 30-31) é a fonte de CAs pretendida.

## Commands you will need

| Purpose    | Command                          | Expected on success |
|------------|----------------------------------|---------------------|
| Sintaxe    | `python -m py_compile main.py`   | exit 0              |
| Testes     | `python -m pytest tests/ -q`     | all pass            |
| Smoke TLS  | `python -c "import ssl; print(ssl._create_default_https_context.__name__)"` (ver abaixo) | imprime `_create_default_https_context` ou `create_default_context` (NÃO `_create_unverified_context`) |

## Scope

**In scope**:
- `main.py` (apenas a linha 32 e arredores imediatos)

**Out of scope**:
- `scrapers.py`, `bot_handlers.py`, `repo.py`, `web_panel.py`, `analisador.py`
- Os patches `certifi`/`_patched_load_verify` (linhas 19-31) — mantenha-os.
- Qualquer mudança em como o Telegram/Gemini são chamados.

## Git workflow

- Branch: `advisor/001-tls-verificacao`
- Commit por unidade lógica; estilo: `fix: reativar verificacao TLS (remover _create_unverified_context)`
- NÃO faça push nem PR sem instrução.

## Steps

### Step 1: Remover a linha que desativa a verificação

Apague a linha `ssl._create_default_https_context = ssl._create_unverified_context`
(linha 32 de `main.py`). Mantenha as linhas 29-31 (o patch `certifi`).
Mantenha o comentário `# ── SSL patches ── devem rodar antes de qualquer import de rede`.

**Verify**: `python -m py_compile main.py` → exit 0

### Step 2: Confirmar que o contexto default agora verifica

**Verify**: `python -c "import ssl; c=ssl._create_default_https_context(); print(c.verify_mode)"` →
deve imprimir `2` (=`ssl.CERT_REQUIRED`). Se imprimir `0` (=`CERT_NONE`), a
remoção não teve efeito — STOP e reporte.

### Step 3: Smoke test de rede (Telegram + Gemini)

Rode um script mínimo que conecta aos dois serviços sem chamar o loop inteiro:

```python
import main  # aplica os patches SSL agora corretos
import telebot
from google import genai, os as gos
b = telebot.TeleBot(main.TOKEN_TELEGRAM)
print("Telegram get_me:", b.get_me().first_name)
c = genai.Client(api_key=main.API_KEY_GEMINI)
r = c.models.generate_content(model="models/gemini-3.1-flash-lite", contents="ping")
print("Gemini ok:", bool(r.text))
```

**Verify**: imprime o nome do bot e `Gemini ok: True`. Qualquer `SSLError` /
`CERTIFICATE_VERIFY_FAILED` → o patch `certifi` (linhas 29-31) NÃO está
suficiente sozinho; NÃO restaure a linha 32. Vá para STOP conditions.

### Step 4: Rodar a suíte de testes

**Verify**: `python -m pytest tests/ -q` → all pass (test_detector + test_repo).

## Test plan

- Não há teste novo de TLS (mockar TLS é frágil). A verificação é o smoke de
  rede no Step 3 + o `verify_mode == CERT_REQUIRED` no Step 2.
- Após merge, um ciclo real do `main.py` confirma Telegram online + uma
  análise Gemini (disparar `/ia <pid>` via bot).

## Done criteria

- [ ] `python -m py_compile main.py` exit 0
- [ ] `python -c "...verify_mode..."` imprime `2`
- [ ] Smoke Telegram + Gemini no Step 3 retorna sucesso
- [ ] `python -m pytest tests/ -q` all pass
- [ ] Nenhum arquivo fora de `main.py` modificado (`git status`)
- [ ] `plans/README.md` status row atualizado

## STOP conditions

Pare e reporte (não improvise) se:
- O código em `main.py:16-32` não bate com o excerto em "Current state"
  (drift desde a escrita do plano).
- Após remover a linha 32, o Telegram OU o Gemini falham com erro de
  certificado (`SSLError`, `CERTIFICATE_VERIFY_FAILED`). **NÃO restaure**
  `ssl._create_unverified_context` — isso reabre o buraco de segurança.
  Em vez disso, investigue por que o patch `certifi` (linhas 29-31) não está
  sendo aplicado às bibliotecas, e reporte.
- Um passo falha 2× após tentativa razoável de correção.

## Maintenance notes

- Esta linha quase certamente foi adicionada como workaround de um erro de
  cert no Windows. Se o erro voltar após esta mudança, a raiz é o carregamento
  de CA (linhas 29-31), não a verificação em si — não desative a verificação.
- Após merge, considere rotacionar `TOKEN_TELEGRAM` e `API_KEY_GEMINI` se
  houver suspeita de tráfego interceptado no período em que a verificação
  esteve desativada.
