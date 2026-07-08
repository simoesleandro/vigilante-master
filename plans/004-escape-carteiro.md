# Plan 004: Escapar campos HTML no carteiro + validar scheme da URL

> **Executor instructions**: Siga passo a passo. Rode cada verificação antes
> de avançar. Em "STOP conditions", pare e reporte. Atualize `plans/README.md`.
>
> **Drift check**: `git diff --stat 838a309..HEAD -- carteiro.py`
> Divergência = STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: nenhum
- **Category**: security
- **Planned at**: commit `838a309`, 2026-07-08

## Why this matters

`carteiro.py` monta a mensagem HTML do Telegram escapando só o `texto_bruto`
(o andamento). Os campos de metadados do processo (`numero`, `tribunal`,
`classe`, `parte_label`, `parte_nome`) e a `url` são interpolados crus. Esses
campos vêm do wizard `/adicionar` (input do operador) e o resumo evoluído pela
IA pode conter HTML. A `url` entra em `<a href='{p['url']}'>` — uma aspa
simples no valor quebra o atributo. Escapar tudo + validar o scheme é
defesa-in-depth barata.

## Current state

- `carteiro.py` — worker que consome `fila_saida` e envia ao Telegram.
- `html` já é importado (linha 1: `import html`).
- Excerto (linhas 21-40):
```python
            texto_bruto = t['conteudo']
            truncado = len(texto_bruto) > 250
            if truncado:
                texto_bruto = texto_bruto[:250] + "..."

            texto_extraido_seguro = html.escape(texto_bruto)
            if truncado:
                texto_extraido_seguro += "\n<i>[Texto cortado — use os botões abaixo]</i>"

            texto_html = (
                f"🏛 <b>NOVA MOVIMENTAÇÃO DETECTADA</b>\n"
                f"📌 <b>Processo:</b> <code>{p['numero']}</code>\n"
                f"⚖️ <b>Tribunal:</b> {t['tribunal']}\n"
                f"📋 <b>Classe:</b> {p['classe']}\n"
                f"👤 <b>{p['parte_label']}:</b> {p['parte_nome']}\n"
                f"📅 <b>Alerta:</b> {agora}\n\n"
                f"🔍 <b>Andamentos Recentes:</b>\n"
                f"<blockquote>🟡 <b>ATUALIZAÇÃO:</b>\n{texto_extraido_seguro}</blockquote>\n"
                f"🔗 <a href='{p['url']}'>Abrir no Tribunal</a>"
            )
```
- Convenção: `parse_mode="HTML"`, emojis no início das linhas, `<code>` para
  números, `<b>` para labels.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Sintaxe | `python -m py_compile carteiro.py` | exit 0 |
| Testes  | `python -m pytest tests/ -q` | all pass |

## Scope

**In scope**:
- `carteiro.py` (apenas a construção de `texto_html`, linhas ~30-40)

**Out of scope**:
- `bot_handlers.py` (seus `listar_processos`/`/resumo` também interpolam crus
  — será tratado em plano separado; não expanda o escopo aqui).
- `repo.py`, `scrapers.py`, `main.py`.

## Git workflow

- Branch: `advisor/004-escape-carteiro`
- Commit: `fix: escapar campos HTML no carteiro + validar scheme da URL`

## Steps

### Step 1: Escapar os campos de metadados

Logo antes de montar `texto_html`, crie variáveis escapadas para cada campo:
```python
            numero_seg = html.escape(str(p.get('numero', '')))
            tribunal_seg = html.escape(str(t.get('tribunal', '')))
            classe_seg = html.escape(str(p.get('classe', '')))
            parte_label_seg = html.escape(str(p.get('parte_label', '')))
            parte_nome_seg = html.escape(str(p.get('parte_nome', '')))
```
Então use essas variáveis no f-string (mantenha `<code>` em volta de
`numero_seg` — `<code>` é tag Telegram legítima, o conteúdo interno é que
precisa escapado).

**Verify**: `python -m py_compile carteiro.py` → exit 0

### Step 2: Validar o scheme da URL antes de embeddar em href

Antes do `texto_html`, valide a URL:
```python
            from urllib.parse import urlparse
            url_raw = str(p.get('url', ''))
            parsed = urlparse(url_raw)
            url_seg = html.escape(url_raw, quote=True)
            href_seguro = url_seg if parsed.scheme in ('http', 'https') else ''
            link_html = f"🔗 <a href='{href_seguro}'>Abrir no Tribunal</a>" if href_seguro else "🔗 (URL inválida)"
```
Use `link_html` no lugar da linha `🔗 <a href='{p['url']}'>...`. O
`html.escape(..., quote=True)` escapa aspas simples, fechando o breakout do
atributo. O check de scheme rejeita `javascript:` etc.

**Verify**: `python -m py_compile carteiro.py` → exit 0

### Step 3: Rodar testes

**Verify**: `python -m pytest tests/ -q` → all pass.

## Test plan

- Sem teste de carteiro hoje (Fase 6). Verificação manual pós-merge:
  - Adicione um processo de teste com `parte_nome = "Teste <b>bold</b> 'aspas'"`
    e `url = "https://exemplo.com/?x=1'y=2"` via `/adicionar`.
  - Dispare um reenvio (`/reenviar <pid>`). Confirme: o `<b>bold</b>` aparece
    como texto literal (não negrito), a URL abre o site corretamente, e a
    mensagem não quebra o parse HTML do Telegram.
- Após Fase 6, adicionar `tests/test_carteiro.py` parametrizado (long text,
  chars especiais, URL inválida) — anotar no maintenance note.

## Done criteria

- [ ] `python -m py_compile carteiro.py` exit 0
- [ ] `grep -n "p\['numero'\]\|p\['classe'\]\|p\['parte_nome'\]\|p\['url'\]" carteiro.py` não retorna uso cru dentro do f-string de `texto_html`
- [ ] `python -m pytest tests/ -q` all pass
- [ ] Nenhum arquivo fora de `carteiro.py` modificado
- [ ] `plans/README.md` status row atualizado

## STOP conditions

- `carteiro.py:21-40` não bate com o excerto (drift).
- O `parse_mode="HTML"` do Telegram deixar de renderizar as tags legítimas
  (`<b>`, `<code>`, `<blockquote>`, `<a>`) — se a mensagem chegar como texto
  cru com tags visíveis, o escape está escapando demais (escape só o conteúdo,
  não as tags estruturais do template).
- Uma URL legítima de tribunal (longa, com `&` e `=`) ser rejeitada pelo
  check de scheme — só rejeite se o scheme NÃO for http/https.

## Maintenance notes

- `bot_handlers.py` (`listar_processos` linha 78-80, `/resumo` 339) tem o
  mesmo padrão de interpolar campos crus — replicar este fix lá num plano
  futuro (não expanda o escopo aqui).
- O resumo evoluído pela IA (`analisador.resumo_evolutivo`) é instruído a usar
  HTML (`analisador.py:58`). Ele NÃO passa pelo carteiro (vai direto ao chat
  via `/resumo`), então este plano não o cobre — decidir conscientemente se
  sanitizar o resumo da IA é desejado (trade-off: pode quebrar formatação
  legítima).
