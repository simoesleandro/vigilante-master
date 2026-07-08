# Plan 002: Gatear comandos privilegiados por ADMIN_ID + parar de vazar exceções ao chat

> **Executor instructions**: Siga passo a passo. Rode cada verificação antes de
> avançar. Em "STOP conditions", pare e reporte. Atualize `plans/README.md` ao
> terminar.
>
> **Drift check**: `git diff --stat 838a309..HEAD -- bot_handlers.py main.py`
> Divergência nos excertos = STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: nenhum
- **Category**: security
- **Planned at**: commit `838a309`, 2026-07-08

## Why this matters

Hoje TODOS os comandos do bot (incluindo `/remover`, `/adicionar`, `/reenviar`
— que mutam a lista de processos) são autorizados apenas por `_autorizado`,
que checa se `chat_id` está em `CHATS_ESPECTADORES`. `ADMIN_ID` é usado só
para `_notify_admin` (alertas). Assim, qualquer chat na lista de espectadores
— se for um grupo, qualquer membro — pode apagar/reenviar processos.
Separadamente, `tarefa_ia_resumo` envia `f"❌ Erro Crítico na IA: {e}"` ao
chat, vazando contexto interno/exceção do SDK Gemini.

## Current state

- `bot_handlers.py` — handlers do Telegram; `register_handlers` (linha 12)
  fecha sobre `bot`, `repo`, `analisador`, `chats_espectadores`.
- `_autorizado` (linhas 19-20):
```python
    def _autorizado(chat_id) -> bool:
        return str(chat_id) in chats_espectadores
```
- Comandos privilegiados (linhas 287-328) todos começam com:
```python
    @bot.message_handler(commands=['resumo', 'ia', 'listar', 'remover', 'adicionar', 'reenviar'])
    def comandos_digitados(message) -> None:
        if not _autorizado(message.chat.id):
            return
```
  Dentro, `/adicionar` (299), `/remover` (322), `/reenviar` (326) mutam estado.
- Callback `processar_clique_botao` (241-285) também só checa `_autorizado`
  (243) e permite `reenviar` (272) por botão.
- Vazamento de exceção — `tarefa_ia_resumo` (linha 48):
```python
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Erro Crítico na IA: {e}")
```
- `ADMIN_ID` é passado? **Não** — `register_handlers` só recebe
  `chats_espectadores`. Será preciso passar `ADMIN_ID` também.
- `main.py:233`: `register_handlers(bot, repo, analisador_ia, CHATS_ESPECTADORES)`
- `main.py:60`: `ADMIN_ID = os.getenv("ADMIN_ID", "").strip().strip("[]").strip('"').strip("'") or None`
- Convenção: mensagens ao chat usam `parse_mode="HTML"` e emojis `❌`/`⚠️`.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Sintaxe | `python -m py_compile bot_handlers.py main.py` | exit 0 |
| Testes  | `python -m pytest tests/ -q` | all pass |

## Scope

**In scope**:
- `bot_handlers.py` (signature de `register_handlers`, `_autorizado`, novo `_eh_admin`, handlers, `tarefa_ia_resumo`)
- `main.py` (apenas a chamada `register_handlers(...)` na linha 233)

**Out of scope**:
- `carteiro.py`, `web_panel.py`, `repo.py`, `scrapers.py`, `analisador.py`
- Read-only commands (`/listar`, `/resumo`, `/ia`) continuam só com `_autorizado`
  (espectadores podem ler/analizar; só admin muta). **Não** bloqueie leitura.

## Git workflow

- Branch: `advisor/002-authz-admin-id`
- Commit: `fix: gatear comandos mutativos por ADMIN_ID + parar de vazar excecao IA ao chat`

## Steps

### Step 1: Passar `ADMIN_ID` para `register_handlers`

Em `bot_handlers.py`, mude a signature para receber `admin_id`:
```python
def register_handlers(
    bot: telebot.TeleBot,
    repo: ProcessoRepo,
    analisador: AnalisadorJuridico,
    chats_espectadores: list,
    admin_id,                       # NOVO (str ou None)
) -> None:
```
Em `main.py:233`, passe `ADMIN_ID`:
```python
    register_handlers(bot, repo, analisador_ia, CHATS_ESPECTADORES, ADMIN_ID)
```
Guarde num closure local (perto de `_autorizado`):
```python
    def _eh_admin(chat_id) -> bool:
        return bool(admin_id) and str(chat_id) == str(admin_id)
```

**Verify**: `python -m py_compile bot_handlers.py main.py` → exit 0

### Step 2: Gatear comandos mutativos por admin

Em `comandos_digitados`, logo após o check de `_autorizado` existente, adicione
um gate de admin para os comandos que mutam. Mantenha `/listar`, `/resumo`,
`/ia` acessíveis a espectadores. Exemplo de shape:
```python
        if not _autorizado(message.chat.id):
            return
        partes = message.text.split()
        comando = partes[0].lower()

        # comandos mutativos: só admin
        if any(c in comando for c in ("/remover", "/adicionar", "/reenviar")) \
                and not _eh_admin(message.chat.id):
            bot.send_message(message.chat.id, "⛔ Apenas o administrador pode executar este comando.")
            return
```
No callback `processar_clique_botao` (linha 241-285), o botão `reenviar`
(272) também é mutativo — gateie da mesma forma:
```python
            elif acao == "reenviar":
                if not _eh_admin(call.message.chat.id):
                    bot.answer_callback_query(call.id, "⛔ Só admin.")
                    return
                reenviar_notificacao(call.message, pid)
```

**Verify**: `python -m py_compile bot_handlers.py` → exit 0

### Step 3: Parar de vazar exceção da IA ao chat

Em `tarefa_ia_resumo` (linha 47-48), troque:
```python
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Erro Crítico na IA: {e}")
```
por:
```python
        except Exception as e:
            print(f"❌ Erro na IA ({pid}): {e}")  # log servidor
            bot.send_message(message.chat.id, "❌ Erro interno na IA. Verifique os logs.")
```
Faça o mesmo em `comandos_digitados` (linha 351-352): troque
`bot.reply_to(message, f"⚠️ Ocorreu um erro...")` por mensagem genérica e
mantenha o `print(f"Erro no comando: {e}")`.

**Verify**: `python -m py_compile bot_handlers.py` → exit 0

### Step 4: Rodar testes

**Verify**: `python -m pytest tests/ -q` → all pass.

## Test plan

- Não há teste de bot hoje (Fase 6). Verificação manual pós-merge:
  - De um chat que NÃO é admin mas está em `CHATS_ESPECTADORES`: `/remover X`
    → responde "⛔ Apenas o administrador...". `/listar` → funciona.
  - Do chat admin: `/remover X` → executa normalmente.
- Antigo `tests/test_repo.py`/`test_detector.py` não cobrem bot; só confirmam
  que a mudança de signature não quebrou imports.

## Done criteria

- [ ] `python -m py_compile bot_handlers.py main.py` exit 0
- [ ] `python -m pytest tests/ -q` all pass
- [ ] `grep -n "Erro Crítico na IA: {e}" bot_handlers.py` retorna vazio
- [ ] Nenhum arquivo fora de `bot_handlers.py`, `main.py` modificado
- [ ] `plans/README.md` status row atualizado

## STOP conditions

- `bot_handlers.py` ou a chamada em `main.py:233` não batem com os excertos.
- Quebrar a chain `register_next_step_handler` do wizard (se um step parar de
  chamar o próximo) — o wizard `/adicionar` ainda deve completar 8 passos.
- `ADMIN_ID` vir `None` (não configurado) faz `_eh_admin` sempre `False`:
  nesse caso **nenhum** comando mutativo funciona. Isso é intencional
  (fail-closed). Se o operador relatar que admin não consegue mutar,
  verifique se `ADMIN_ID` está setado no `.env` — NÃO remova o gate.

## Maintenance notes

- Se futuramente adicionar um comando mutativo novo, lembre de incluí-lo no
  filtro do Step 2 (ou criar um decorador `_admin_only`).
- `ADMIN_ID` deve ser o chat_id numérico do operador (string comparada com
  `str(chat_id)`). Grupos não devem ser admin (qualquer membro mutaria).
