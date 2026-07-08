# ADR 0001 — Abstração de Tribunal plugável

- **Status**: PROPOSED (spike; implementação pendente de aceite)
- **Date**: 2026-07-08
- **Deciders**: Leandro (operador) + agente
- **Related plan**: `plans/015-spike-tribunal-plugavel.md`

## Context

O roadmap promete "Suporte a novos tribunais (TRF, TRT)" mas a arquitetura é
totalmente hardcoded. Hoje, três tribunais são tratados em três lugares
distintos, sem interface comum:

- `bot_handlers.py:137` — `if tribunal not in ["TJRJ", "STF", "TSE"]: ...`
  rejeita qualquer tribunal fora dessa lista literal.
- `main.py:275-310` — três branches bespoke no loop quente, um por tribunal.
- `scrapers.py` — três funções sem contrato compartilhado
  (`extrair_playwright_batch`, `extrair_stf_stealth_batch`,
  `extrair_tse_stealth_batch`).

Adicionar TRF ou TRT hoje exige editar os três módulos em lockstep, sem
garantia de que a nova string `"TRF"` esteja em todos os sites esperados.
Esse é o anti-pattern "missing abstraction where the same change touches
N files" (Sandi Metz). Refatorar depois de já existir um quarto tribunal é
mais caro do que definir o contrato antes de precisar.

Por que um spike (e não um build): o objetivo é destravar a direção de
expansão de tribunais, sem assumir que os 3 tribunais atuais vão continuar
estáveis como estão. O spike produz o contrato + o registry; a
implementação vira planos separados após o aceite.

## Decision drivers

- O loop quente (`main.py:257-321`) não pode quebrar. Qualquer refator
  precisa preservar o comportamento atual (cadências, captcha, cleanup).
- TSE tem peculiaridades que STF/TJRJ não têm (headed, captcha manual,
  thread separada, cadência 15 ciclos). O contrato precisa acomodar isso
  sem forçar os outros tribunais a pagar o custo.
- O operador já tentou Playwright no STF e reportou detecção
  (navigator.webdriver exposto). Manter `undetected_chromedriver` no STF
  é mandatório; a escolha browser fica por tribunal, não é global.
- `bot_handlers` precisa validar tribunais dinamicamente (sem lista
  literal) para que adicionar um tribunal novo não exija editar o wizard.
- A Fase 6 introduziu testes — o próximo refator precisa de rede
  (testes existentes + fixtures HTML para adapters novos).

## Peculiaridades por tribunal (estado atual)

Documentado a partir de `main.py:275-310`, `scrapers.py:1-298` e
`bot_handlers.py:114-237`:

| Tribunal | Browser / modo | Headless | Captcha | Cadência | Seletor principal | Cadência cleanup |
|----------|---------------|----------|---------|----------|-------------------|------------------|
| TJRJ | Playwright Chromium (`sync_playwright`) | `headless=False` + `--headless=new` (contraditório, ver nota) | não | 1 ciclo (1× a cada 2 min) | `table:has(th:has-text('Data'))` → primeira linha após header | `_limpar_temp_playwright()` a cada ciclo |
| STF | `undetected_chromedriver` (Selenium) | `headless=new` (verdadeiramente headless) | não | 1 ciclo (1× a cada 2 min) | `.andamento-item, app-andamento` (WebDriverWait 15s + scroll fallback) | `_limpar_temp_playwright()` a cada ciclo |
| TSE | `undetected_chromedriver` (Selenium) | não (headed — janela visível) | sim (manual via Telegram, 5 min timeout) | 15 ciclos (~30 min) — alterado em jun/2026 para reduzir triggers | `.tramitacao-card` (loop 3s até `len(text) > 50`) | `_limpar_temp_playwright()` no `finally` |

Notas:

- TJRJ e STF rodam inline no ciclo. TSE roda em thread separada, com
  guard `tse_thread.is_alive()` para não empilhar (linhas 301-317).
- Os três tribunais passam pelo mesmo `_despachar(detector, repo, bot,
  analisador, proc, tribunal, txt, img)` (`main.py:185-219`) — o que
  prova que o dispatch downstream **já** é genérico; o que falta é
  generalizar o *fetch* upstream.
- `lock_navegador` (`scrapers.py:12`) já é global e compartilhado entre
  as três funções — sinal claro de que os scrapers sabem que disputam o
  mesmo recurso. A abstração formaliza isso.

## Proposed contract

### Protocolo `Tribunal`

```python
from typing import Protocol, Callable, List, Optional, Tuple

class Tribunal(Protocol):
    """Contrato de adapter para um tribunal.

    Cada tribunal implementa sua própria extração e declara seus
    requisitos de browser / cadência / captcha.
    """

    @property
    def nome(self) -> str:
        """Chave canônica: 'TJRJ', 'STF', 'TSE', futuro 'TRF1' etc."""
        ...

    @property
    def HEADLESS(self) -> bool:
        """Se True, roda invisível. TSE=False (headed, captcha manual)."""
        ...

    @property
    def precisa_captcha(self) -> bool:
        """Se True, o dispatcher deve passar on_captcha e reservar cadência."""
        ...

    @property
    def cadencia_ciclos(self) -> int:
        """Chamar este tribunal a cada N ciclos. TJRJ/STF=1, TSE=15."""
        ...

    def extrair(
        self,
        processos: list[dict],
        on_captcha: Optional[Callable[[str], None]] = None,
    ) -> List[Tuple[Optional[str], Optional[str]]]:
        """Extrai (txt, img_path) por processo. Preserva ordem."""
        ...
```

### Registry

```python
# tribunais/__init__.py (novo módulo)
from typing import Dict
from .tjrj import TJRJ
from .stf import STF
from .tse import TSE

TRIBUNAIS: Dict[str, Tribunal] = {
    "TJRJ": TJRJ(),
    "STF":  STF(),
    "TSE":  TSE(),
}

__all__ = ["Tribunal", "TRIBUNAIS"]
```

### Dispatcher unificado (substitui `main.py:275-310`)

```python
from tribunais import TRIBUNAIS, Tribunal

# Dentro do loop principal:
for nome, adapter in TRIBUNAIS.items():
    if cnt % adapter.cadencia_ciclos != 0:
        continue
    if nome == "TSE":
        # TSE precisa de thread dedicada por causa do captcha bloqueante
        if tse_thread is not None and tse_thread.is_alive():
            print(f"⚠️ {nome} anterior ainda rodando — pulando este disparo.")
            continue
        processos = repo.list_processos(nome)
        tse_thread = threading.Thread(
            target=_rodar_adapter,
            args=(adapter, processos, detector, repo, bot, analisador, _notify_admin),
            daemon=True,
        )
        tse_thread.start()
    else:
        processos = repo.list_processos(nome)
        _rodar_adapter(adapter, processos, detector, repo, bot, analisador, _notify_admin)


def _rodar_adapter(adapter, processos, detector, repo, bot, analisador, notify):
    """Wrapper: extrai, despacha, limpa. Substitui os try/except/finally
    idênticos em main.py:279-299 e main.py:305-316."""
    try:
        on_cap = (lambda n: notify(bot, f"🔑 Resolva {adapter.nome}: {n}")
                  if adapter.precisa_captcha else None)
        resultados = adapter.extrair(processos, on_captcha=on_cap)
        for pr, (t, i) in zip(processos, resultados):
            _despachar(detector, repo, bot, analisador, pr, adapter.nome, t, i)
            if adapter.precisa_captcha:
                time.sleep(5)
    except Exception as e:
        print(f"   ⚠️ Ciclo {adapter.nome} abortado, seguindo: {e}")
    finally:
        _limpar_temp_playwright()
```

Mudança no wizard (`bot_handlers.py:137`):

```python
# antes
if tribunal not in ["TJRJ", "STF", "TSE"]:
    ...
# depois
from tribunais import TRIBUNAIS
if tribunal not in TRIBUNAIS:
    ...
```

E o `_notify_admin` precisa ser passado para dentro do wrapper, já que
TSE usa `lambda` que captura o bot. Hoje ele já é uma closure em
`main.py:309` — o adapter não muda isso, só padroniza o ponto de
injeção.

## Open questions (bloqueiam implementação)

Marcadas com **[B]** quando bloqueiam a Fase de implementação.

1. **[B]** O callback de captcha (`on_captcha` → Telegram) é
   responsabilidade do adapter ou do dispatcher?
   - Pro adapter: encapsula toda a peculiaridade de TSE no adapter
     (pergunta o `notify_admin` no construtor).
   - Pro dispatcher: dispatcher conhece o mecanismo de notificação,
     adapter só recebe o callable.
   - **Recomendação**: adapter recebe `on_captcha` por parâmetro
     (injetado pelo dispatcher). Mantém o adapter puro (testável sem
     Telegram).

2. **[B]** STF em Playwright funciona ou ainda é detectado?
   - Hoje STF usa `undetected_chromedriver` (não Playwright) justamente
     porque o operador relatou detecção no passado.
   - Decisão: a escolha Playwright-vs-undetected_chromedriver fica
     **dentro do adapter STF**, não global. O adapter STF continua
     usando `undetected_chromedriver` na primeira versão.
   - Validar antes de mover STF para Playwright: testar com
     `navigator.webdriver` + fingerprint.

3. **[B]** `cadencia_ciclos` (TSE=15) vive no adapter ou em config?
   - **Recomendação**: no adapter como `@property`, com override por
     env opcional (`TSE_CADENCIA_CICLOS=15`). Permite tuning sem mudar
     código, mas o default sensato está no adapter.

4. **[B]** Como testar um adapter novo sem acesso ao tribunal real?
   - **Recomendação**: cada adapter aceita `fixtures: dict` (mapeando
     `id → (html, png_path)`). Em produção, fixture é vazio (vai pra
     rede). Em teste, fixture é populado com HTML gravado e o adapter
     faz parse offline. Isso depende da Fase 6 (testes) — já feita.

5. O dispatcher deve continuar tratando TSE como thread separada, ou
   o adapter TSE pode se auto-encapsular? **Recomendação**: dispatcher
   continua decidindo (é uma propriedade transversal: bloquearia o
   loop se rodasse inline). Flag `precisa_captcha=True` é a heurística.

6. `bot_handlers:137` deve validar contra `TRIBUNAIS.keys()` ou aceitar
   qualquer string e deixar o dispatcher falhar com mensagem útil?
   - **Recomendação**: validar no wizard (falha cedo, mensagem clara
     ao usuário). O dispatcher confia no registry.

7. Adicionar TRF/TRT exige URL diferente por seção (TRF1 ≠ TRF2).
   Como parametrizamos isso? **Recomendação**: o adapter recebe o
   `repository` e lê os processos já cadastrados; a URL de cada
   processo já está no banco (coluna `url`). Não precisa de registry
   de seções.

## Risks

- **Risco de regressão no loop quente**: o refator toca o caminho mais
  crítico. Mitigação: testes de smoke (Fase 6 já dá rede) + manter o
  comportamento exato do `try/except/finally` + `_limpar_temp_playwright`.
- **Risco de acoplar adapter a `repo`/`bot`**: o adapter idealmente
  recebe `processos: list[dict]` e devolve `list[(txt, img)]` — não
  conhece `repo` nem `bot`. Isso preserva testabilidade.
- **Risco de canonização de nomes**: o registry é a fonte da verdade
  para a string `"TJRJ"`. `bot_handlers` e `repo.list_processos(...)`
  precisam consumir o mesmo registry. Mitigação: importar `TRIBUNAIS`
  de um único módulo, nunca hardcodar.

## Consequences

### Positivas

- Adicionar TRF/TRT vira "escrever um adapter + uma linha no registry",
  sem editar 3 módulos.
- O contrato documenta a fronteira entre "fetch" (adapter) e
  "processamento" (`_despachar`, hoje já genérico).
- Testes de adapter ficam triviais: fixture HTML → parse offline.
- Cadência e captcha viram propriedades explícitas, não convenções
  implícitas no `if cnt % 15 == 0`.

### Negativas

- Mais uma camada de indireção para os 3 tribunais atuais que já
  funcionam.
- Exige migração cuidadosa dos 3 fluxos em `main.py` — um erro de
  copy-paste no `_rodar_adapter` pode afetar todos os tribunais.
- O registry vira ponto único de falha: se `TRIBUNAIS` não importa
  (ex: erro de sintaxe em qualquer adapter), o loop inteiro cai.

### Neutras

- O dispatch downstream (`_despachar`) já é genérico. Esta mudança só
  generaliza o upstream.
- O `lock_navegador` continua sendo global e usado pelos 3 adapters.
  Pode evoluir para "lock por adapter" no futuro, mas não é exigido.

## Implementation plan (próximos planos, fora deste spike)

Quando o operador aceitar este ADR, a implementação vira 3 a 4 planos:

1. **Plano 015a**: criar `tribunais/__init__.py` com os 3 adapters
   (wrappers finos sobre as funções existentes em `scrapers.py`,
   sem mudar comportamento). Trocar `bot_handlers.py:137` para usar
   `TRIBUNAIS.keys()`. Adicionar testes de registry vazio.
2. **Plano 015b**: refatorar `main.py:275-310` para o loop sobre
   `TRIBUNAIS` com `_rodar_adapter`. Manter `tse_thread` como
   ramificação explícita. Verificar que STF/TJRJ/TSE rodam idêntico
   ao baseline (logs de teste).
3. **Plano 015c**: testes de adapter com fixture HTML (TJRJ, STF) —
   TSE fica sem teste offline por causa do captcha.
4. **Plano 015d** (futuro): adicionar TRF1 como quarto adapter
   (exemplo canônico de "como adicionar um tribunal novo"). Este é o
   plano que valida o design.

## References

- `main.py:275-310` (dispatcher atual, 3 branches)
- `main.py:301-317` (TSE thread especial)
- `scrapers.py:121-164` (TJRJ batch + `_raspar_tjrj`)
- `scrapers.py:170-227` (STF batch + `_raspar_stf`)
- `scrapers.py:232-298` (TSE batch com captcha)
- `bot_handlers.py:119-242` (wizard de cadastro)
- `bot_handlers.py:137` (validação literal `["TJRJ","STF","TSE"]`)
- AGENTS.md §"Frequência TSE" — cadência 15 ciclos
