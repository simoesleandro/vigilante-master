# Plan 003: Mitigar XSS no painel web (`innerHTML` → `textContent`)

> **Executor instructions**: Siga passo a passo. Rode cada verificação antes
> de avançar. Em "STOP conditions", pare e reporte. Atualize `plans/README.md`.
>
> **Drift check**: `git diff --stat 838a309..HEAD -- web_panel.py output_stream.py`
> Divergência = STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: nenhum
- **Category**: security
- **Planned at**: commit `838a309`, 2026-07-08

## Why this matters

O painel web (`localhost:8080`) renderiza cada linha de stdout via SSE sem
escapamento, usando `elemento.innerHTML`. Stdout contém texto de processos e
mensagens de exceção (que podem incluir paths/detalhes). Qualquer linha com
HTML é executada no contexto da página do painel. Trocar `innerHTML` por
`textContent` elimina o sink de XSS sem mudar a aparência (o efeito "digitar"
continua, só sem interpretação de HTML).

## Current state

- `web_panel.py` — painel Flask; o HTML/JS está na string `_HTML_HACKER`
  (linhas 13-131). Servido por `index()` (134-136). SSE em `/stream` (139-148).
- A função JS `digitarTexto` (linhas 87-116) usa `innerHTML`:
```javascript
        function digitarTexto(elemento, htmlCompleto, velocidade = 10) {
            return new Promise(resolve => {
                let i = 0;
                let isTag = false;
                let textoExibido = "";

                elemento.innerHTML = '<span class="cursor"></span>';

                function proximoCaractere() {
                    if (i < htmlCompleto.length) {
                        let char = htmlCompleto.charAt(i);
                        textoExibido += char;
                        elemento.innerHTML = textoExibido + '<span class="cursor"></span>';
                        if (char === '<') isTag = true;
                        if (char === '>') isTag = false;
                        i++;
                        painel.scrollTop = painel.scrollHeight;
                        if (isTag) {
                            proximoCaractere();
                        } else {
                            setTimeout(proximoCaraxim, velocidade);
                        }
                    } else {
                        elemento.innerHTML = textoExibido;
                        resolve();
                    }
                }
                proximoCaractere();
            });
        }
```
- O SSE emite cru (linha 145): `yield f"data: {msg}\n\n"` — `msg` vem de
  `output_stream.py:18-19` sem escape.
- `output_stream.py:18`: `msg_segura = mensagem.replace('\n', '').replace('\r', '')`
  (só remove newlines, não escapa HTML).
- Convenção: o cursor pisca via `<span class="cursor">`. Esse span é o ÚNICO
  HTML legítimo no elemento; o resto deve ser texto puro.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Sintaxe | `python -m py_compile web_panel.py` | exit 0 |
| Testes  | `python -m pytest tests/ -q` | all pass |

## Scope

**In scope**:
- `web_panel.py` (apenas a função JS `digitarTexto` dentro de `_HTML_HACKER`)

**Out of scope**:
- `output_stream.py` — não precisa mudar; fixando o sink no cliente, o payload
  cru do SSE deixa de ser explorável. (Escape no servidor é defesa-in-depth
  opcional, fora deste plano.)
- Rotas Flask, SSE, `iniciar_servidor_web`.

## Git workflow

- Branch: `advisor/003-xss-painel`
- Commit: `fix: mitigar XSS no painel web (innerHTML -> textContent)`

## Steps

### Step 1: Reescrever `digitarTexto` para usar nós de texto, não innerHTML

Substitua a função `digitarTexto` (linhas 87-116) por uma versão que anexa um
nó de texto + o span do cursor via `appendChild`/`textContent`, nunca
`innerHTML`. O cursor continua piscando. Exemplo de shape:
```javascript
        function digitarTexto(elemento, texto, velocidade = 10) {
            return new Promise(resolve => {
                elemento.innerHTML = ''; // limpa uma vez no início
                const txtNode = document.createTextNode("");
                const cursor = document.createElement('span');
                cursor.className = 'cursor';
                elemento.appendChild(txtNode);
                elemento.appendChild(cursor);
                let i = 0;
                function proximoCaractere() {
                    if (i < texto.length) {
                        txtNode.data += texto.charAt(i);
                        i++;
                        painel.scrollTop = painel.scrollHeight;
                        setTimeout(proximoCaraxim, velocidade);
                    } else {
                        resolve();
                    }
                }
                proximoCaractere();
            });
        }
```
Note: remova a lógica `isTag` (não há mais tags para pular). O parâmetro foi
renomeado `htmlCompleto`→`texto` para clareza; o caller em `evento.onmessage`
(linha 122) passa `">> " + event.data` — mantenha esse caller.

**Verify**: `python -m py_compile web_panel.py` → exit 0 (só checa Python;
o JS é string, mas garante que não quebrou a sintaxe Python da string).

### Step 2: Confirmar que não há mais `innerHTML` no fluxo de digitação

**Verify**: `grep -n "innerHTML" web_panel.py` → deve retornar **0** matches
(a única atribuição `elemento.innerHTML = ''` no início do Step 1 é
aceitável para limpar; se preferir, troque por `while(elemento.firstChild) elemento.removeChild(elemento.firstChild)` para zero `innerHTML`).

Se mantiver `elemento.innerHTML = ''`, tudo bem — é uma limpeza, não um sink
de conteúdo externo. O ponto é que **nenhum dado do SSE** chega ao `innerHTML`.

### Step 3: Rodar testes

**Verify**: `python -m pytest tests/ -q` → all pass.

## Test plan

- Sem teste automatizado de JS neste repo. Verificação manual pós-merge:
  - Abra `http://localhost:8080` com o `main.py` rodando.
  - Dispare um log que contenha `<b>teste</b>` ou `<img src=x onerror=alert(1)>`
    (ex: via `/ia` que imprime exceção, ou um `print("<b>x</b>")` temporário).
  - Confirme: o texto aparece literalmente (`<b>teste</b>` visível como texto),
    não é interpretado como HTML. O cursor pisca normalmente.

## Done criteria

- [ ] `python -m py_compile web_panel.py` exit 0
- [ ] `grep -n "innerHTML" web_panel.py` não retorna atribuições de conteúdo do SSE
- [ ] `python -m pytest tests/ -q` all pass
- [ ] Nenhum arquivo fora de `web_panel.py` modificado
- [ ] `plans/README.md` status row atualizado

## STOP conditions

- `_HTML_HACKER` ou `digitarTexto` não batem com os excertos (drift).
- A quebra do efeito "digitar" que comprometa a usabilidade do painel
  (cursor some, texto não aparece) — reporte antes de ajustar mais.
- A string Python `_HTML_HACKER` ficar com aspas/sintaxe quebrada (py_compile
  pega isso).

## Maintenance notes

- O span `.cursor` é o único elemento filho legítimo. Se alguém re-adicionar
  `innerHTML` no futuro para "renderizar cores", reabre o sink — prefira
  spans com `textContent` por cor.
- Defesa-in-depth opcional (não neste plano): escapar no SSE server-side
  (`web_panel.py:145`) trocando `<`/``>` por entidades. Mas com `textContent`
  no cliente, o sink está fechado.
