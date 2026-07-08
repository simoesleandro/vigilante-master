# ADR 0003 — Deploy como serviço Windows (WinSW)

- **Status**: PROPOSED (spike; implementação pendente de aceite)
- **Date**: 2026-07-08
- **Deciders**: Leandro (operador) + agente
- **Related plan**: `plans/018-wording-vm-winsw.md`

## Context

O Vigilante Master roda hoje como `python main.py` num terminal do
desktop. Isso significa:

1. Se o terminal fechar (Ctrl+C, crash do explorer, reboot), o
   processo morre. Sem auto-restart.
2. O operador precisa reabrir o terminal e digitar o comando após
   qualquer reboot.
3. A notificação de crash (`main.py:333-340`) já é enviada ao
   Telegram, mas a recuperação é manual.

O roadmap (`README.md:186`) lista "Deploy como serviço Windows
(WinSW)" como item unchecked. A `AGENTS.md:5` já diz "Roda direto no
desktop Windows do Leandro (não usa mais VM)", o que reforça que o
deploy é desktop — e desktop = serviço Windows faz sentido (sobrevive
a reboot, logoff, e crash).

**Por que um spike e não um build**: o WinSW como serviço roda em
conta `SYSTEM` por padrão, o que muda o ambiente de execução
(`%USERPROFILE%`, paths, perfil do Chrome/Playwright). Antes de
empacotar e instalar o serviço de fato, é preciso decidir **como** ele
roda (SYSTEM vs conta de usuário) e como conviver com
`undetected_chromedriver` (que precisa de perfil). Spike define
contrato + tradeoffs; implementação vira plano separado.

## Decision drivers

- O operador quer que o vigilante **sobreviva a reboot** e
  **auto-restarte** em crash. Isso é o mínimo que o serviço precisa
  entregar.
- O `undetected_chromedriver` (STF/TSE) cria perfil de Chrome em
  `%TEMP%`/`%LOCALAPPDATA%`. Se o serviço rodar como `SYSTEM`, esses
  paths apontam para `C:\Windows\System32\config\systemprofile\` — o
  que pode (a) funcionar (Chrome cria perfil lá), (b) exigir flags
  `--user-data-dir`, ou (c) falhar por permissão. **Tem que ser
  testado**.
- O Playwright (TJRJ) também cria perfil em `%TEMP%` (`playwright_*`
  é limpo pelo `_limpar_temp_playwright` a cada ciclo, então
  resiliência é maior). Mas a detecção de `navigator.webdriver` pode
  mudar de comportamento em SYSTEM.
- O Telegram crash-alert já existe (`main.py:333-340`). O WinSW
  restart é uma camada adicional: ele reinicia mesmo que o operador
  não veja o alerta.
- O operador é o único usuário da máquina. Decisões de segurança
  locais (permissões) podem ser relaxadas em favor de
  simplicidade — mas não devem ser implicitamente permissivas.

## Current state (evidência)

- `main.py:333-340` — Telegram crash-alert (admin-only). Mensagem
  diz "A Máquina Virtual encontrou um Erro Fatal" (em
  português) — **wording legado da era VM, corrigido pelo Step 1
  do plano 018** ("O monitor encontrou um Erro Fatal e o script
  foi interrompido.").
- `main.py:237-252` — `_run_polling` já tem retry de polling
  (`409 Conflict` espera 30s; outros erros backoff exponencial até
  5 min). Isso é auto-recuperação **dentro** do main.
- `scrapers.py:170-227, 232-298` — `undetected_chromedriver` cria
  driver por batch, com cleanup via `try/finally`.
- `main.py:11-13` — `output_stream.ativar()` é import-level.
  WinSW vai rodar `python main.py` como `Command`, então o stdout
  fica acessível no event log do Windows.
- `scrapers.py:11` — `VERSAO_CHROME_VM = 150` (constante de
  versão). Out of scope do plano 018 (wording só). Manter nome.
- `AGENTS.md:5` — confirma desktop, sem VM.

Não há config de serviço hoje (`sc Select-String -Path . -Pattern
"WinSW|NSSM|pywin32" -Recurse` retorna nada).

## Options

### (a) WinSW (recomendado)

- **O que é**: `WinSW-x64.exe` + `vigilante.xml` (config). Roda
  qualquer executável como serviço Windows. Padrão para
  Java/Python/Node no Windows.
- **Prós**:
  - Binário único (~500 KB) + XML — zero dependência externa
    runtime (só o `WinSW.exe`).
  - Config declarativa: `<onfailure action="restart"/>`,
    `<startmode>automatic</startmode>`, `<delayedAutoStart>`.
  - Bem documentado, ativo, mantido.
  - `serviceaccount` permite rodar como usuário logado (resolve
    SYSTEM-vs-user profile para Chrome/Playwright).
  - Logs de stdout/stderr vão para o Event Log do Windows
    automaticamente.
- **Contras**:
  - XML tem opções obscuras (e.g., `stoptimeout`, `stopparentfirst`).
  - Não tem UI; gerência é via `sc` (Service Control) ou
    `winsw.exe install/uninstall/start/stop`.
  - **Requer testar** o impacto de `serviceaccount` vs
    `LocalSystem` no undetected_chromedriver.

### (b) NSSM (Non-Sucking Service Manager)

- **O que é**: `nssm.exe` que "instala" qualquer comando como
  serviço Windows.
- **Prós**:
  - CLI muito amigável: `nssm install vigilante "C:\...\python.exe"
    "main.py"`. Wizard via `nssm edit`.
  - GUI nativa (`nssm.exe` mostra form com tabs).
  - Mais maduro que WinSW em algumas dimensões (trata
    dependências entre serviços).
- **Contras**:
  - Menos popular para Python/Java hoje.
  - Não tem `serviceaccount` declarativo — gerência de
    credenciais é via GUI ou registry.
  - Requer admin install path (`C:\nssm` ou similar).

### (c) `pywin32` service nativo

- **O que é**: classe Python que herda de
  `win32serviceutil.ServiceFramework`. O `main.py` vira módulo
  `servico.py` com ponto de entrada.
- **Prós**:
  - Zero binário externo — só o `pywin32` (já tem dependência de
    `pywin32` em outros pontos? — verificar).
  - Controle total do ciclo de vida (start/stop/pause).
- **Contras**:
  - Mais código. Refatorar `main.py` em dois modos (CLI e
    serviço).
  - Debugging mais difícil (rodar fora de serviço exige
    flags/ambiente).
  - `pywin32` tem API instável entre versões do Windows.

**Recomendação: (a) WinSW**. Tradeoff: simplicidade declarativa
vs NSSM tem GUI. WinSW + `serviceaccount` é suficiente para o caso
(1 operador, 1 máquina, sem dependência entre serviços).

## Decisões de recuperação (recomendação)

Camadas de auto-recuperação no Vigilante Master:

1. **Telegram crash-alert** (já existe, `main.py:333-340`):
   notifica o operador que houve crash. **Sempre ligado.**
2. **Retry de polling** (já existe, `main.py:237-252`): o bot
   reconecta em backoff exponencial (até 5 min). **Sempre ligado.**
3. **WinSW restart-on-fail** (este spike): se o processo Python
   sair com código != 0, WinSW reinicia após `<resetperiod>`
   segundos. **Decisão recomendada: LIGADO.**

Por que **ambos** (Telegram + WinSW) e não "ou":

- O Telegram avisa o humano. Se o operador está dormindo ou
  viajou, o alerta fica registrado.
- O WinSW reinicia mesmo que ninguém veja o alerta. Em 5 minutos
  o ciclo está de novo rodando, e o operador vê o alerta na hora
  que acordar.
- Se WinSW falhar em reiniciar (e.g., crash-loop por bug novo), o
  alerta Telegram fica lá como evidência.

**Config recomendada no XML**:

```xml
<service>
  <id>vigilante-master</id>
  <name>Vigilante Master</name>
  <description>Monitora TJRJ/STF/TSE e notifica via Telegram.</description>
  <executable>python</executable>
  <arguments>main.py</arguments>
  <workingdirectory>C:\Meus_projetos\vigilante-master</workingdirectory>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>5</keepFiles>
  </log>
  <onfailure action="restart" delay="30 sec"/>
  <resetperiod>1 hour</resetperiod>
  <startmode>Automatic</startmode>
  <delayedAutoStart>true</delayedAutoStart>
  <serviceaccount>
    <domain>LEANDRO-DESKTOP</domain>
    <user>leandro</user>
    <password>...</password>
  </serviceaccount>
</service>
```

- `onfailure action="restart" delay="30 sec"` — 30s entre
  tentativas evita crash-loop (bug novo não derruba a máquina
  inteira).
- `resetperiod` reseta o contador de falhas depois de 1h
  (WinSW só).
- `delayedAutoStart` espera 2-3 min após o boot antes de subir —
  dá tempo de `LOCALAPPDATA`, `%TEMP%`, e Chrome profile ficarem
  prontos.
- `serviceaccount` roda como `leandro` (não SYSTEM) — resolve o
  problema de perfil do Chrome/Playwright.

**Open question crítica**: rodar como serviço do **usuário logado**
ou **SYSTEM**?

- SYSTEM: processo sobrevive a logout do usuário (mais robusto),
  mas perfis de Chrome/Playwright ficam em
  `C:\Windows\System32\config\systemprofile\...`. Testes
  pendentes para validar.
- Usuário logado (`serviceaccount`): perfis do Chrome ficam em
  `%LOCALAPPDATA%\Google\Chrome\...` do Leandro (igual hoje),
  mas o serviço pode parar se o usuário fizer logoff. Em
  Windows com login automático, é equivalente a SYSTEM para
  esse caso.

**Recomendação**: começar com `serviceaccount` (usuário) porque
o Chrome já tem perfil lá (o Leandro já usa o Chrome diário).
Migrar para SYSTEM só se o operador precisar de "sobrevive
logoff" como requisito.

## Passos de implementação (plano futuro, fora deste spike)

1. Baixar `WinSW-x64.exe` do GitHub (releases), renomear para
   `vigilante.exe`. Colocar em `C:\Meus_projetos\vigilante-master\`
   (junto do `main.py`).
2. Criar `vigilante.xml` (template na seção acima) com paths
   absolutos.
3. `vigilante.exe install` (PowerShell admin) — registra o
   serviço.
4. `vigilante.exe start` — inicia o serviço.
5. **Teste de reboot**: reiniciar a máquina. Confirmar que o
   serviço sobe automaticamente e que o Telegram recebe
   "Vigilante Master Online".
6. **Teste de crash**: `Stop-Process` no `python.exe`. Confirmar
   que o WinSW reinicia em ~30s e o Telegram recebe o crash-alert.
7. **Teste de Playwright/Chrome**: rodar 1 ciclo TJRJ + 1 STF +
   1 TSE como serviço. Verificar que os profiles do Chrome são
   criados (em `systemprofile` ou `leandro` dependendo da config
   de `serviceaccount`) e que os processos não vazam `chrome.exe`
   zumbis.
8. Documentar no `AGENTS.md` o comando para reiniciar o serviço
   (`vigilante.exe restart`) e onde ficam os logs
   (`%PROGRAMDATA%\vigilante-master\logs\`).

## Risks

- **Risco SYSTEM-vs-user**: undetected_chromedriver e Playwright
  podem falhar em SYSTEM. Mitigação: `serviceaccount` (default),
  testar exaustivamente antes de migrar para SYSTEM.
- **Risco de crash-loop**: bug novo no `main.py` faz o processo
  crashar em <30s. WinSW reinicia, processo recrasha, loop.
  Mitigação: `resetperiod=1 hour` (WinSW só), Telegram crash-alert
  alerta o humano, monitorar via `Get-EventLog` (PowerShell).
- **Risco de `python` no PATH do SYSTEM**: se o serviço rodar
  como SYSTEM, o PATH é o de SYSTEM (sem `.venv\Scripts`). Usar
  `<executable>C:\...\venv\Scripts\python.exe</executable>`
  (path absoluto) em vez de `python` nu.
- **Risco de console interativo**: WinSW não dá console
  interativo. Se o operador rodar `python main.py` no terminal
  (modo dev), pode dar conflito de porta no web_panel
  (`web_panel.py:154`, `FLASK_PORT=8080`). Mitigação: parar o
  serviço antes de rodar dev, ou mudar a porta em dev.
- **Risco de SAC + undetected_chromedriver**: já documentado
  no `AGENTS.md` (SAC foi desativado). Se o operador reativar
  SAC, o serviço pode quebrar. Não há mitigação automática.
- **Risco de `VERSAO_CHROME_VM` desatualizado**: o Chrome
  auto-atualiza; `scrapers.py:11` precisa acompanhar (ver
  `AGENTS.md` §"Smart App Control + Chrome"). WinSW não muda
  isso.

## Consequences

### Positivas

- Auto-restart em crash (sem o operador precisar fazer nada).
- Sobrevive a reboot da máquina.
- Logs de stdout/stderr vão automaticamente para o Event Log
  do Windows (mais fácil de debugar do que arquivo de log).
- Camada de recuperação explícita: WinSW (automático) +
  Telegram (humano).

### Negativas

- Mais um binário externo (`WinSW.exe`) para manter.
- Debugging mais difícil: stack traces vão para Event Log, não
  para o terminal do operador.
- `serviceaccount` requer senha em texto claro no XML (ou via
  env var) — se a máquina for comprometida, o atacante tem
  credencial de serviço.
- Refator mínimo do `main.py` para o `print(f"...")` ir para
  `sys.stdout` (já vai — é o default).

### Neutras

- O Telegram crash-alert continua sendo a principal forma de
  notificação humana. WinSW não substitui.
- O comportamento do loop principal não muda — só quem invoca
  o `python main.py` muda (operador → WinSW).

## Implementation plan (próximos passos, fora deste spike)

1. **Plano 018a** (teste controlado): instalar WinSW em
   staging, rodar por 1 semana em paralelo com o `python main.py`
   manual. Comparar logs.
2. **Plano 018b** (cutover): parar o `python main.py` manual,
   instalar WinSW como serviço. Atualizar `AGENTS.md` com
   comandos de operação.
3. **Plano 018c** (cosmético): renomear `VERSAO_CHROME_VM` para
   `VERSAO_CHROME` em `scrapers.py:11`. Out of scope do 018b —
   tech-debt separado.

## References

- `main.py:333-340` — Telegram crash-alert (wording já corrigido)
- `main.py:237-252` — `_run_polling` (retry/backoff)
- `scrapers.py:11` — `VERSAO_CHROME_VM = 150` (constante de
  versão, out of scope)
- `scrapers.py:170-298` — `undetected_chromedriver` (STF + TSE,
  sensível a perfil de usuário)
- `AGENTS.md:5` — confirmação de ambiente desktop
- `AGENTS.md` §"Smart App Control + Chrome" — contexto de SAC
- `README.md:186` — roadmap "Deploy como serviço Windows (WinSW)"
- [WinSW GitHub](https://github.com/winsw/winsw) — referência
  do XML schema
- [NSSM](https://nssm.cc/) — alternativa (b)
