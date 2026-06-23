# Interactive Energy Digital Twin — CARLA

Gêmeo digital de energia do protótipo MarchForce: um modelo longitudinal simplificado
estima potência instantânea e energia acumulada a partir da telemetria do veículo
(CARLA em simulação, hardware real no futuro), transmitida por um barramento MQTT,
persistida no TimescaleDB, espelhada numa Asset Administration Shell (Eclipse BaSyx)
e exposta via OPC UA, com dashboard React em tempo real. Arquitetado segundo o RAMI 4.0.

---

## Sumário

1. [Como rodar](#como-rodar)
2. [O pipeline de dados](#o-pipeline-de-dados)
3. [O modelo de energia](#o-modelo-de-energia)
4. [Grandezas, unidades e sinais](#grandezas-unidades-e-sinais)
5. [Por que a autonomia mostra "0min"?](#por-que-a-autonomia-mostra-0min)
6. [Os ruídos nos gráficos — por que existem?](#os-ruídos-nos-gráficos--por-que-existem)
7. [O dashboard (frontend)](#o-dashboard-frontend)
8. [Integração com o CARLA](#integração-com-o-carla)
9. [O gêmeo digital BaSyx / AAS](#o-gêmeo-digital-basyx--aas)
10. [Automação com o Makefile](#automação-com-o-makefile)
11. [Tópicos MQTT](#tópicos-mqtt)
12. [Desenvolvimento e testes](#desenvolvimento-e-testes)

---

## Como rodar

### Pré-requisitos

| Ferramenta | Onde roda | Observação |
|---|---|---|
| Docker + Docker Compose | WSL2 / Linux | toda a infra corre em containers |
| GNU make | WSL2 / Linux | orquestra os comandos |
| Python 3.12 (Windows) | Host Windows | só para a aquisição CARLA |
| CARLA 0.9.16 | Host Windows | simulador — `make carla-download` baixa |

Sem CARLA, a stack usa o simulador interno como fonte de dados (sem nenhuma
instalação extra no Windows).

### Modo CARLA — um único comando

```bash
# No WSL2:
make run-carla
```

O que acontece em sequência:

1. Abre o **CARLA** no Windows (`CarlaUE4.exe -quality-level=Low`)
2. Aguarda CARLA responder na porta 2000 (até 4 min)
3. Sobe o **Docker stack** completo (mosquitto, timescaledb, processing, api, twin-sync, BaSyx, dashboard)
4. Abre uma **janela PowerShell** no Windows rodando `carla/run-acquisition.ps1`, que conecta ao CARLA, faz spawn do veículo e publica telemetria no MQTT

Após alguns segundos o veículo aparece no CARLA em autopiloto. O dashboard estará em:

| Serviço | Endereço |
|---|---|
| Dashboard | http://localhost:8080 |
| API + WebSocket | http://localhost:8000 |
| BaSyx AAS (REST) | http://localhost:8081 |
| BaSyx UI | http://localhost:3000 |
| OPC UA | `opc.tcp://<ip-do-host>:4840/marchforce/` |

### Modo simulador (sem CARLA)

```bash
make run        # build + deploy completo
make down       # para tudo
```

### Modo desenvolvimento (hot reload)

```bash
make install    # instala deps Python (venv) + Node (npm)
make dev        # API com --reload + Vite HMR + infra Docker
```

Dashboard em http://localhost:4173 · API em http://localhost:8000

---

## O pipeline de dados

```
CARLA (Windows)
    │  velocidade, aceleração, posição  (10 Hz, modo síncrono)
    ▼
run-acquisition.ps1
    │  publica RawTelemetryDto
    ▼
MQTT  marchforce/telemetry/raw
    │
    ▼
ProcessingService  (Docker, src/processing_main.py)
    │  aplica modelo de energia longitudinal
    │  deriva Vdc / Idc do barramento DC
    │  avalia alertas de diagnóstico
    │  publica ProcessedTelemetryDto
    ▼
MQTT  marchforce/telemetry/processed
    │
    ├──► TimescaleDB  (persistência histórica por sessão)
    │
    ├──► API FastAPI / WebSocket  →  Dashboard React
    │
    └──► TwinSyncService  (src/twin_main.py)
              │  PATCH REST → BaSyx (submodelos EnergyEfficiency)
              │
              └──► MQTT  marchforce/aas/{Submodel}/{idShort}
                         (espelho AAS em tópicos flat)
```

Cada mensagem `raw` contém apenas o estado cinemático medido pelo CARLA (`velocity`,
`acceleration`, `dt`, `x`, `y`). A mensagem `processed` acrescenta todos os KPIs
derivados pelo domínio.

---

## O modelo de energia

O modelo longitudinal decompõe as forças que atuam no veículo em linha reta:

```
F_total = F_inercial + F_aerodinâmica + F_rolamento

F_inercial    = m · a                          (Newton)
F_aerodinâmica = ½ · ρ · Cd · A_frontal · v²  (arrasto do ar)
F_rolamento   = Crr · m · g                   (resistência dos pneus)

Potência instantânea  P = F_total · v   [W]
Energia acumulada     E += P · dt        [J]  (somente quando P > 0)
```

Parâmetros padrão (configuráveis via dashboard ou `POST /api/config`):

| Parâmetro | Valor padrão | Descrição |
|---|---|---|
| Massa veículo | 60 kg | chassi + motor |
| Massa piloto | 50 kg | |
| Massa total | **110 kg** | usada no modelo |
| Cd (arrasto) | 0,10 | baixo — protótipo aberto |
| Área frontal | 0,5 m² | |
| Crr (rolamento) | 0,002 | pneus slick |
| Capacidade bateria | 5 000 000 J ≈ **1,39 kWh** | |
| Tensão nominal DC | **48 V** | barramento elétrico |

### Modelo da bateria

O SoC (estado de carga) é integrado numericamente a partir da energia elétrica
consumida ou recuperada:

```
Descarga:   ΔSoC = (P · dt / η_desc) / C_bat
Regeneração: ΔSoC = (P · dt · η_regen) / C_bat

η_desc = η_regen = 0,9   (eficiência de 90%)
```

---

## Grandezas, unidades e sinais

### Por que potência e corrente podem ser **negativas**?

O modelo trata o sinal de potência como o sinal energético do veículo em relação
à bateria:

| Situação | Sinal de P | Significado |
|---|---|---|
| Acelerando / cruzeiro | **P > 0** | bateria fornece energia ao motor |
| Frenagem regenerativa | **P < 0** | motor age como gerador, recarrega bateria |
| Parado | P ≈ 0 | sem troca de energia |

A corrente DC segue o mesmo sinal, pois `I = P_elétrica / Vdc`. Corrente negativa
significa fluxo de retorno para a bateria (regen).

### Por que a tensão DC bate ~50 V se a nominal é 48 V?

A tensão é **derivada** (não medida diretamente no CARLA), usando um modelo linear
do estado de carga:

```
Vdc = V_nominal × (0,95 + 0,10 × SoC)
```

Com bateria cheia (SoC = 1,0): `48 × 1,05 = 50,4 V` — realista para uma bateria
LFP/NMC 48 V com SoC alto. Conforme descarrega: `48 × 0,95 = 45,6 V` (SoC = 0).

### Tabela completa de grandezas

| Grandeza | Tópico MQTT (campo) | Unidade exibida | Conversão | Pode ser negativa? |
|---|---|---|---|---|
| Velocidade | `velocity` | km/h | ×3,6 (de m/s) | Não (longitudinal) |
| Aceleração | `acceleration` | m/s² | — | Sim (desaceleração) |
| Potência DC | `power` | W | — | **Sim** (regen) |
| Tensão DC | `vdc` | V | — | Não |
| Corrente DC | `idc` | A | — | **Sim** (regen) |
| SoC | `soc` | % | ×100 (de 0–1) | Não |
| Energia acumulada | `energy` | Wh | ÷3600 (de J) | Não |
| Distância | `distance` | km | ÷1000 (de m) | Não |
| Consumo específico | `specific_consumption` | Wh/km | ×1000 (de Wh/m) | Não |
| Autonomia estimada | `autonomy` | h:mm ou Xmin | formatado (de s) | Não |

---

## Por que a autonomia mostra "0min"?

A autonomia é calculada como:

```
autonomia = (SoC × C_bat) / P_média   [segundos]
```

onde `P_média` é a **média móvel das últimas 50 amostras** de potência.

A autonomia só é calculada quando `P_média > 5 W` (piso mínimo). Isso evita
divisões por zero e valores absurdos quando o veículo está parado ou na primeira
fração de segundo após o spawn.

**Por que mostra 0min no início da sessão?**
As primeiras ~5 segundos de telemetria (50 amostras × 0,1 s) ainda estão
preenchendo a janela de média. Enquanto a janela não for completa, a média é
calculada sobre menos amostras, podendo resultar em potência média baixa — o que
faz a autonomia cair abaixo do piso e ser mostrada como zero.

**Por que pode aparecer valores absurdamente altos?**
Se o veículo ainda está quase parado (`P_média` muito baixa), a divisão gera um
número enorme. O código limita a `MAX_AUTONOMY_S = 1 000 000 s ≈ 277 horas`.
Mesmo assim, esse valor soa irreal — é um artefato do modelo simplificado sem
inércia de janela completa.

**Formato de exibição:**

| Valor em segundos | Exibição |
|---|---|
| 0 – 3599 s | `Xmin` |
| 3600 – 359999 s | `Xh YYmin` |
| ≥ 360000 s (>99h) | `>99h` |
| Dados ausentes | `—` |

---

## Os ruídos nos gráficos — por que existem?

Os gráficos de potência, corrente e velocidade apresentam oscilações que são
**fisicamente justificadas** e não erros de software.

### 1. Decisões do Traffic Manager (autopiloto do CARLA)

O piloto automático do CARLA aplica aceleração e frenagem em pulsos discretos para
manter a velocidade alvo e respeitar outros veículos. Cada decisão do TM se
traduz em um pico ou vale de potência — visível no gráfico de Potência (W).

### 2. Derivada numérica da aceleração

A aceleração é calculada como `(v_atual − v_anterior) / dt`. Pequenas variações
de velocidade (1–2 cm/s entre ticks de 100 ms) geram picos de aceleração de
±1–3 m/s². Para suavizar, é aplicado um **filtro EMA** (média móvel exponencial)
com α = 0,15:

```
a_filtrada = 0,15 × a_bruta + 0,85 × a_filtrada_anterior
```

Mesmo com o filtro, variações rápidas de velocidade (mudanças de marcha, curvas)
aparecem como ruído no gráfico de potência, pois `P = F · v` amplifica qualquer
variação de aceleração.

### 3. Modo síncrono do CARLA + sleep

O CARLA roda em **modo síncrono** (a simulação só avança quando `world.tick()` é
chamado). O loop de aquisição chama `tick()` e depois dorme 80 ms. O `dt` real
de cada frame é lido do snapshot do CARLA (`delta_seconds`), então não há
acumulação de erro temporal — mas a cadência pode variar ligeiramente.

### 4. Regime transitório de spawn

Nos primeiros 1–2 segundos após o spawn, o veículo é "solto" no ponto de spawn
com velocidade zero. O Traffic Manager começa a acelerar imediatamente, gerando
um pico de potência inicial acentuado (visível no gráfico logo no começo da
sessão).

---

## O dashboard (frontend)

### Tecnologias

- **React 18** com Vite (bundler) e HMR em desenvolvimento
- **Recharts** para os gráficos de série temporal
- **WebSocket nativo** do browser para telemetria em tempo real

### Como os dados chegam ao browser

```
ProcessingService
    │  publica ProcessedTelemetryDto no MQTT
    ▼
API FastAPI (src/api/server.py)
    │  MqttClient subscreve marchforce/telemetry/processed
    │  LiveHub enfileira payloads (asyncio.Queue, maxsize=1000)
    │  broadcast_loop() distribui para todos os WebSocket conectados
    ▼
useLiveTelemetry.js  (hook React)
    │  WebSocket ws://localhost:8000/ws/live
    │  mantém `latest` (última amostra) e `series` (janela de 120 pontos)
    ▼
KpiCards + LiveCharts + TrackMap + AlertsPanel
```

O WebSocket reconecta automaticamente a cada 1,5 s em caso de queda. Ao reconectar,
o servidor envia imediatamente o último frame conhecido para evitar tela em branco.

### Conversões de unidades no frontend

Todas as conversões acontecem **exclusivamente no frontend** — o backend sempre
publica valores nas unidades base do SI. O arquivo [src/components/KpiCards.jsx](frontend/src/components/KpiCards.jsx)
centraliza os fatores de escala de cada grandeza (campo `scale`) e o formatador
customizado da autonomia (`fmtAutonomy`).

Os gráficos ([src/components/LiveCharts.jsx](frontend/src/components/LiveCharts.jsx))
aplicam o mesmo fator `scale` mapeando o array de séries antes de passar para o
Recharts — assim o eixo Y já exibe a unidade correta sem alterar os dados originais.

### Mapa da pista

O componente `TrackMap` renderiza a trajetória do veículo em um canvas SVG usando
as coordenadas `x` / `y` enviadas pelo CARLA. A cor de cada ponto codifica a
velocidade (verde = parado, laranja/vermelho = alta velocidade).

### Alertas de diagnóstico

O `ProcessingService` avalia cada amostra contra limiares configuráveis e emite
alertas junto com a telemetria. O `AlertsPanel` no dashboard exibe o alerta ativo
mais recente. Os limiares padrão são:

| Alerta | Warning | Crítico |
|---|---|---|
| SoC | < 20% | < 5% |
| Corrente DC | > 60 A | > 100 A |
| Velocidade | > 33 m/s | > 42 m/s |

---

## Integração com o CARLA

### Por que a aquisição roda no Windows e não no WSL?

O SDK Python do CARLA é distribuído como um wheel `win_amd64` — ele só funciona no
Python do Windows. O WSL2 é Linux e não executa DLLs do Windows, então a aquisição
**precisa obrigatoriamente rodar no host Windows**.

O restante da stack (processamento, banco, API, BaSyx) roda em containers Docker
no WSL2 normalmente.

### Comunicação Windows ↔ WSL2

O WSL2 cria automaticamente regras de port-forward para todas as portas Docker
expostas. Isso significa que o `localhost:1883` no Windows alcança o broker
Mosquitto rodando no Docker/WSL2 sem nenhuma configuração extra.

```
Windows
  CARLA (porta 2000) ◄── CarlaClient (win_amd64)
  run-acquisition.ps1 → publica MQTT → localhost:1883
                                              │
                                    WSL2 port-forward
                                              │
                                    Docker mosquitto :1883
                                              │
                                    mf-processing container
                                    mf-twin-sync container
```

### Controle manual do veículo

Enquanto o `run-acquisition.ps1` estiver aberto em janela ativa, é possível
controlar o veículo manualmente via teclado (o foco deve estar na janela do CARLA
ou de qualquer aplicação — usa `GetAsyncKeyState`, que lê o estado global das teclas):

| Tecla | Ação |
|---|---|
| `W` | acelerar (para frente) |
| `S` | ré |
| `A` / `D` | virar esquerda / direita |
| `P` | alternar autopiloto / manual |

No modo autopiloto (padrão), o Traffic Manager do CARLA controla o veículo
automaticamente.

### Spawn do veículo

O veículo (`vehicle.audi.tt` por padrão) é spawnado no **primeiro ponto de spawn
disponível** da lista retornada pelo mapa. O código usa `try_spawn_actor()` em
loop por todos os pontos — se o ponto 0 estiver ocupado (por exemplo, de uma sessão
anterior que não foi encerrada corretamente), ele tenta o próximo automaticamente.

Se o CARLA retornar "all spawn points occupied", feche o CARLA completamente e
reabra antes de rodar o script de aquisição.

---

## O gêmeo digital BaSyx / AAS

### O que é o BaSyx?

O Eclipse BaSyx é uma implementação open-source do padrão **Asset Administration
Shell (AAS)** da Industrie 4.0. Uma AAS é um "passaporte digital" do ativo físico
(neste caso, o protótipo MarchForce) — estrutura os dados em submodelos padronizados
para interoperabilidade entre sistemas.

### Submodelos implementados

| Submodelo | Conteúdo | Atualização |
|---|---|---|
| `OperationalState` | velocidade, aceleração, potência, energia | PATCH por amostra |
| `Battery` | SoC, fluxo de energia elétrica | PATCH por amostra |
| `EnergyEfficiency` | distância, P_média, consumo específico, autonomia | PATCH por amostra |

### Exposição no MQTT

Além de atualizar a AAS via REST, o `TwinSyncService` publica cada elemento em um
tópico MQTT flat — facilitando integração com qualquer cliente MQTT sem precisar
fazer parsing do JSON da AAS:

```
marchforce/aas/TimeSeries/Velocity
marchforce/aas/TimeSeries/Acceleration
marchforce/aas/TimeSeries/InstantaneousPower
marchforce/aas/TimeSeries/AccumulatedEnergy
marchforce/aas/TimeSeries/DcVoltage
marchforce/aas/TimeSeries/DcCurrent
marchforce/aas/TimeSeries/StateOfCharge     ← SoC em % (×100)
marchforce/aas/EnergyEfficiency/Distance
marchforce/aas/EnergyEfficiency/AveragePower
marchforce/aas/EnergyEfficiency/SpecificConsumption
marchforce/aas/EnergyEfficiency/Autonomy
```

O prefixo é configurável via `MQTT_TOPIC_AAS` (padrão: `marchforce/aas`).

### Eventos próprios do BaSyx no MQTT

O BaSyx publica seus próprios eventos em tópicos separados (configurado em
`basyx-setup/basyx/aas-env.properties`):

```
aas-repository/aas-repo/shells/created      ← quando a AAS é registrada (uma vez)
sm-repository/sm-repo/submodels/created     ← quando os submodelos são registrados
```

Esses são **eventos de ciclo de vida** (criação), não telemetria em tempo real —
por isso aparecem no MQTT Explorer mas não ficam atualizando continuamente.

---

## Automação com o Makefile

```
make <target>
```

| Target | O que faz |
|---|---|
| `help` | lista todos os targets com descrição |
| `install` | cria venv Python + instala npm no frontend |
| `run` | build com testes + deploy completo via Docker |
| `run-carla` | abre CARLA + sobe stack + lança aquisição no Windows |
| `dev` | infra Docker + API hot-reload + Vite HMR + twin-sync |
| `dev-up` | só a infra: TimescaleDB + BaSyx completo (AAS + Mongo + MQTT) |
| `twin-up` | só o BaSyx (AAS + Mongo + MQTT) |
| `dev-twin` | twin-sync como processo host (para depuração) |
| `carla` | abre o CARLA no Windows (sem subir o resto) |
| `carla-download` | baixa o CARLA para o Windows (~10–20 GB, só uma vez) |
| `test` | roda pytest |
| `smoke` | pipeline offline end-to-end (sem infra, usa fakes) |
| `verify` | smoke-test na stack ao vivo |
| `down` | para todos os containers Docker |
| `logs` | segue os logs do stack Docker |
| `clean` | para serviços dev + remove artefatos |

### Por que o `make dev` sempre inclui o twin-sync?

O `deploy.sh all` (chamado por `make dev-back`) inclui `deploy_twin` explicitamente
para garantir que o BaSyx seja atualizado em qualquer modo de execução — não apenas
no modo Docker completo. Sem o `twin_main.py` rodando, o BaSyx fica com os dados
estáticos do arquivo `.aasx` e nunca reflete a telemetria ao vivo.

---

## Tópicos MQTT

| Tópico | Publicado por | Conteúdo |
|---|---|---|
| `marchforce/telemetry/raw` | acquisition service | cinemática bruta do CARLA (`velocity`, `acceleration`, `dt`, `x`, `y`, `vdc=null`, `idc=null`) |
| `marchforce/telemetry/processed` | processing service | KPIs completos + alertas |
| `marchforce/aas/TimeSeries/*` | twin-sync service | valores individuais por elemento AAS |
| `marchforce/aas/EnergyEfficiency/*` | twin-sync service | KPIs de eficiência por elemento AAS |
| `marchforce/control` | (futuro) | comandos de controle remoto |
| `marchforce/config` | API (`POST /api/config`) | atualização de parâmetros do veículo e limiares |

---

## Como parar tudo

### Modo CARLA (`make run-carla`)

```bash
make carla-down
```

Isso faz em sequência:
1. Encerra os containers Docker (stack + BaSyx) via `make down`
2. Mata o processo da janela PowerShell de aquisição (PID salvo em `.run/acq-win.pid`)
3. Encerra o `CarlaUE4.exe` no Windows via `Stop-Process`

Se precisar parar só o CARLA sem derrubar a stack:

```bash
make carla-stop  # só mata o CarlaUE4.exe, containers continuam
```

### Modo simulador / Docker (`make run`)

```bash
make down
```

### Modo desenvolvimento (`make dev`)

```bash
make dev-stop   # para os processos host (API, processing, twin-sync, frontend)
make twin-down  # para o BaSyx (AAS + Mongo + MQTT)
```

Ou de uma vez:

```bash
make clean      # dev-stop + remove artefatos de build
make twin-down  # BaSyx
```

### Resumo rápido

| Como subiu | Como para |
|---|---|
| `make run-carla` | `make carla-down` |
| `make run` | `make down` |
| `make dev` | `make dev-stop` + `make twin-down` |

---

## Desenvolvimento e testes

```bash
make test       # pytest — cobertura do modelo de energia, bateria e diagnósticos
make smoke      # pipeline end-to-end offline (sem Docker, sem CARLA)
make verify     # smoke na stack live (requer `make run` antes)
make report     # compila relatório técnico em PDF (Docker TeX Live)
```

Os testes seguem o padrão AAA (Arrange / Act / Assert) e cobrem:

- `EnergyModel` — forças individuais e integração de energia
- `Battery` — descarga, regeneração e limites de SoC
- `VehicleEnergySystem` — integração dos dois módulos acima
- `ProcessingService` — derivação de Vdc/Idc e alertas de diagnóstico
- Smoke pipeline — sequência `raw → processed → twin sync` com fakes

### Configuração via ambiente

Tudo é configurado por variáveis de ambiente, selecionadas por `APP_ENV`
(`dev` | `staging` | `prod`). Os arquivos ficam em `config/.env.<env>`.
Copie `config/.env.example` para criar novos ambientes. Arquivos `.env.staging`,
`.env.prod` e `.env.local` são ignorados pelo git.

```bash
APP_ENV=prod make run
```
