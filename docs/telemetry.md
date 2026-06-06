# Telemetria MarchForce — fluxo MQTT → processamento → dashboard

Camada de telemetria construída **ao lado** do gêmeo digital (CARLA + BaSyx),
reaproveitando a modelagem energética da PEX (`src/domain/`). Segue a arquitetura
da proposta MarchForce: aquisição → MQTT → processamento energético →
TimescaleDB → API/WebSocket → dashboard.

## Visão geral do pipeline

```
Fonte (CARLA | simulador)
   │  UpdateRequestDto
   ▼
Aquisição (bridge)  ── publica ──▶  MQTT  marchforce/telemetry/raw
                                     │
                                     ▼
Processamento energético  (domínio PEX: potência, energia, SoC, KPIs + diagnóstico)
   ├── persiste ──▶ TimescaleDB (sessions + telemetry)
   └── publica  ──▶ MQTT  marchforce/telemetry/processed
                                     │
                                     ▼
API FastAPI  ── WebSocket /ws/live ─▶ Dashboard React (ao vivo)
             ── REST /api/sessions ─▶ Dashboard React (histórico)

Consumidores adicionais do tópico processed:
   ├── LoRa      ─▶ box (telemetria resumida)
   └── twin-sync ─▶ BaSyx (REST) ─▶ MQTT/OPC UA do BaSyx (host)
```

Cada serviço só conversa com o broker / o banco — nunca direto com outro serviço.
Isso é o que permite trocar uma peça sem mexer nas demais (ver "Camadas e
contratos").

## Componentes

| Camada | Arquivo | Papel |
|---|---|---|
| Domínio | `src/domain/energy_model.py`, `battery.py`, `vehicle_energy_system.py` | Modelagem energética (reuso PEX) |
| Domínio | `src/domain/diagnostics.py` | Enums `Severity`/`AlertCode` + regras de alerta |
| Aquisição | `src/infra/sources.py`, `src/application/acquisition_service.py` | Lê a fonte e publica `raw` |
| Processamento | `src/application/processing_service.py` | `raw` → domínio → persiste + publica `processed` |
| Infra | `src/infra/mqtt_client.py` | Adapter do barramento lógico (MQTT) |
| Infra | `src/infra/timescale_repository.py` | Persistência por sessão (TimescaleDB) |
| Exposição | `src/api/server.py` | REST (histórico) + WebSocket (ao vivo) |
| Externa (LoRa) | `src/application/lora_service.py`, `src/infra/lora_link.py` | Envia subconjunto ao box |
| Gemeo digital | `src/application/twin_sync_service.py`, `src/application/twin_service.py` | Atualiza BaSyx (→ MQTT/OPC UA) |
| Interfaces | `src/application/ports.py` | Contratos `MessageBus`, `TelemetryRepository`, `TelemetryLink`, `TelemetrySource` |
| Erros | `src/exceptions.py`, `src/infra/messages.py` | Exceções por camada + mensagens amigáveis |
| Frontend | repositório próprio (`frontend/` local) | Dashboard React (Vite + Recharts) |

## Como rodar

Há dois fluxos: **produção** (imagens Docker locais, enxutas, para o
computador de bordo Linux 24/7) e **dev** (process-based, com hot reload).

### Produção — imagens locais (`make run`)

```bash
make run     # build (testes como gate) -> deploy do stack self-contained
```

`make run` = `images` + `deploy`:

1. `images` constrói as imagens lean. **Os testes rodam como um estágio do
   build do backend**: se a suíte falha, a imagem não é gerada e o deploy não
   sobe — a versão boa que já roda não é substituída.
2. `deploy` sobe o stack self-contained: broker MQTT próprio + TimescaleDB +
   `api` + `processing` + `acquisition` + `dashboard` (nginx).

Ao final:

- Dashboard: <http://localhost:8080>
- API: <http://localhost:8000> (REST + WebSocket)

Outros alvos: `make logs`, `make down`. Selecione o ambiente com
`APP_ENV=prod make run`.

### Dev — hot reload (`make dev`)

```bash
make install   # venv + pip + npm
make dev       # infra dev + backend (uvicorn --reload) + frontend (Vite HMR)
```

- Dashboard (Vite HMR): <http://localhost:4173>
- API (auto-reload em `src/`): <http://localhost:8000>

> **Hot reload é exclusivo de `dev`.** Em `staging`/`prod` o artefato é a imagem
> imutável (nginx estático + uvicorn puro), sem watcher consumindo CPU.

Alvos dev: `make dev-up`, `make dev-back`, `make dev-front`, `make dev-stop`,
`make test`, `make smoke` (use `make help`).

## Imagens enxutas (foco em desempenho)

As imagens são multi-stage para não embarcar peso desnecessário:

- **Backend**: `python:3.12-slim`; o estágio de testes roda o pytest mas **não é
  embarcado** no runtime; a imagem final leva só deps + `src`.
- **Frontend**: Node só no estágio de build; o runtime é `nginx:alpine` +
  bundle estático (centenas de KB) — sem `node_modules` nem toolchain.
- **`.dockerignore`** exclui `.venv`, `node_modules`, `.git`, `basyx-setup` e o
  `.aasx` (200 MB+) do contexto de build, mantendo o upload de contexto mínimo.

Restart policies (`unless-stopped`) mantêm o stack rodando após reboot do box.

### Fonte de dados

Definida por `ACQ_SOURCE`:

- `carla` (padrão em staging/prod) — lê de um servidor CARLA em execução.
- `sim` (padrão em dev) — simulador sintético, ideal para demo sem CARLA.

> Enquanto o B.O.M. não é liberado, a fonte real é o CARLA; o simulador é o
> fallback offline para demonstrações.

## Configuração por ambiente

Nada de credenciais no código. A config é carregada de `config/.env.<APP_ENV>`:

- `config/.env.dev` (commitado, credenciais não-sensíveis)
- `config/.env.staging`, `config/.env.prod` (ignorados pelo git — preencher)
- `config/.env.example` (modelo)

Selecione com `APP_ENV=staging make deploy`, por exemplo. Variáveis reais de
ambiente sempre têm precedência sobre o arquivo (bom para secrets em deploy).

## Broker MQTT por ambiente

- **Dev / com gêmeo digital (`WITH_TWIN=1`, padrão)**: **reutiliza o mosquitto do
  `basyx-setup/`** (já escuta na 1883 com acesso anônimo). Não sobe um segundo
  broker — dois mapeariam a mesma porta do host. No deploy containerizado, os
  serviços apontam `MQTT_HOST=host.docker.internal` (ajustado pelo
  `deploy_docker.sh`); em dev por processo, `make dev-up` sobe só o serviço
  `mosquitto` do BaSyx. O Mongo e o deploy do gêmeo digital não são tocados.
- **Box self-contained (`WITH_TWIN=0`)**: o stack roda o **próprio** broker
  (serviço `mosquitto`, ativado pelo profile `own-broker`), pois o computador de
  bordo roda os serviços críticos localmente sem depender do BaSyx (requisito de
  autonomia local da proposta MarchForce).

O serviço `mosquitto` do `deploy/` fica atrás do profile `own-broker`
justamente para nunca subir junto com o broker do BaSyx (evita o conflito na
porta 1883). Em ambos os modos os tópicos são namespaced
(`marchforce/telemetry/...`) e não colidem.

## Dashboard externa (LoRa)

A dashboard atual é a **local completa** (computador de bordo). A **externa
limitada** (box, via LoRa) é alimentada pelo serviço LoRa
([lora_service.py](../src/application/lora_service.py)), um consumidor puro do
barramento: assina `marchforce/telemetry/processed`, seleciona poucos campos
essenciais (`LORA_FIELDS`) + alertas críticos, respeita o duty cycle
(`LORA_MIN_INTERVAL`) e descarta frames acima de `LORA_MAX_BYTES`. O enlace é um
port `TelemetryLink`: `LoggingLoRaLink` (sem hardware, padrão) ou
`SerialLoRaLink` (módulo real). É opcional no deploy (`--profile lora`).

## Implementando um port (adapter novo)

Um port é um contrato (`src/application/ports.py`). Para plugar uma
implementação:

1. Crie uma classe herdando do port: `class MeuRepo(TelemetryRepository): ...`
2. Implemente todos os métodos `@abstractmethod` com a mesma assinatura. O
   Python recusa instanciar a classe se faltar algum — é a rede de segurança da
   interface.
3. Injete a implementação no serviço (os serviços tipam pelo port, não pela
   classe concreta).

Adapters concretos vivem em `src/infra` (MqttClient, TimescaleRepository, links,
sources). Os testes usam fakes em `tests/fakes.py`.

## Mensagens amigáveis

Falhas de infraestrutura são traduzidas para mensagens em pt-BR com dica de
correção por [messages.py](../src/infra/messages.py) (`friendly(erro)`), usadas
nos entrypoints — o usuário vê "Não foi possível falar com o broker MQTT…" em
vez de um stack trace.

## Frontend em repositório separado

O código do frontend vive em um repositório próprio. O deploy continua buildando
a imagem: defina `FRONTEND_REPO` (e opcionalmente `FRONTEND_BRANCH`) e o
`scripts/deploy_docker.sh` clona/atualiza o repo e builda a partir dele. Sem
`FRONTEND_REPO`, usa o `frontend/` local (modo mono-repo).

## Gemeo digital (BaSyx) — MQTT/OPC UA

O gemeo digital é o **BaSyx** (`basyx-setup/`). Ao subir, o AAS Environment
expõe o modelo e, com `basyx.*.feature.mqtt.enabled=true`
([aas-env.properties](../basyx-setup/basyx/aas-env.properties)), **publica os
eventos de atualização dos submodels no MQTT** — além do endpoint OPC UA — no
host. Não é código da aplicação; é infraestrutura do BaSyx.

O serviço **twin-sync** ([twin_sync_service.py](../src/application/twin_sync_service.py))
assina o tópico `processed` e atualiza o AAS via REST
([twin_service.py](../src/application/twin_service.py) — `sync_processed`),
escrevendo os KPIs do submodelo `EnergyEfficiency`. Ao fazer o PATCH, o BaSyx
dispara seus eventos MQTT/OPC UA. Assim **uma única fonte CARLA** alimenta
dashboard, LoRa e o gemeo digital (sem um segundo loop CARLA).

O PATCH usa o endpoint *ValueOnly* do BaSyx v2
(`/submodel-elements/{idShort}/$value`) e o corpo precisa ser o valor como
**string JSON** (`"123.45"`, não o número cru) com `Content-Type:
application/json` — por isso o `_patch_value` envia `json.dumps(value)`. Valor
cru responde 500 e `text/plain` responde 415.

`make run` sobe o BaSyx junto por padrão (camada opcional/removível). Desligue
com `WITH_TWIN=0 make run`. Em dev: `make twin-up` + `make dev-twin`. O cliente
externo (OPC UA/MQTT) conecta no IP do WSL + porta (1883, 8081).

## CARLA (opcional)

Fonte de dados atual (`ACQ_SOURCE=carla`), roda no host Windows. Instalação,
execução e remoção em [../carla/README.md](../carla/README.md). É plug-and-play:
apagar a pasta `carla/` remove a integração sem afetar o resto.

**Um comando:** `make run-carla` inicia o CARLA no Windows, espera a porta 2000,
sobe o stack em modo CARLA e roda a aquisição. Como o wheel `carla` só existe
para Python 3.8–3.10, a **aquisição em modo CARLA roda como processo no host**
(o resto fica em Docker). Crie o ambiente uma vez com `make carla-venv` (gera
`.venv-carla` com `carla==0.9.16`) ou aponte `CARLA_PY` para um Python compatível.

## Camadas e contratos (trocar peças sem efeito colateral)

Os serviços dependem das **interfaces** em `src/application/ports.py`, não das
implementações concretas. Para trocar uma peça, implemente o port e injete:

| Trocar | Mexe em | Contrato a respeitar |
|---|---|---|
| Fonte (CARLA→RS485→sim) | `src/infra/sources.py` | `TelemetrySource` |
| Broker | `src/infra/mqtt_client.py` | `MessageBus` |
| Persistência | `src/infra/timescale_repository.py` | `TelemetryRepository` |
| Dashboard | `frontend/` | REST + WebSocket |

As únicas costuras compartilhadas são os DTOs (`RawTelemetryDto`,
`ProcessedTelemetryDto`), os nomes dos tópicos e as assinaturas dos ports.

## Grandezas e Vdc/Idc

As grandezas seguem a Tabela 5 da proposta. Enquanto não há medição real do
barramento, `processing_service.derive_dc_bus()` deriva `Vdc/Idc` a partir da
potência elétrica e de `NOMINAL_DC_VOLTAGE`. Quando a aquisição passar a medir
`vdc/idc` (campos opcionais em `RawTelemetryDto`), esses valores medidos são
usados diretamente.

## Diagnóstico e alertas

`src/domain/diagnostics.py` avalia cada amostra e emite alertas com `AlertCode`,
`Severity` e mensagem, propagados no payload `processed` e exibidos no dashboard.

| Código | Severidade | Condição |
|---|---|---|
| `W-SOC-LOW` / `E-SOC-CRITICAL` | warning / error | SoC ≤ 20% / ≤ 5% |
| `W-VDC-RANGE` / `E-VDC-RANGE` | warning / error | Vdc fora de ±10% / ±20% do nominal |
| `W-IDC-HIGH` / `E-IDC-OVERCURRENT` | warning / error | \|Idc\| ≥ 60 A / ≥ 100 A |
| `W-SPEED-HIGH` / `E-SPEED-CRITICAL` | warning / error | velocidade ≥ 33 / ≥ 42 m/s |
| `E-DATA-INVALID` | error | leitura NaN/inf |
| `E-PERSIST` | error | falha ao gravar no banco (stream continua) |

Limiares e tensão nominal são configuráveis (`DiagnosticThresholds`,
`NOMINAL_DC_VOLTAGE`).

## Testes

```bash
make test     # suíte unitária (pytest, padrão AAA)
make smoke    # pipeline ponta a ponta offline (sim → processamento → fakes)
make verify   # smoke do stack JÁ NO AR (API + OPC UA + BaSyx twin-sync)
```

Os serviços são testados com fakes que implementam os ports
(`tests/fakes.py`) — sem broker nem banco. Config de pytest/lint em
`pyproject.toml`.

`make test`/`make smoke` são offline e rodam no *build gate* da imagem
(`docker --target test`): suíte vermelha derruba o build, então a imagem nunca
é trocada. `make verify` é diferente — valida o stack **depois** do deploy
(`scripts/verify_stack.py`, executado dentro da imagem backend, que tem as deps
de runtime). Lê os endpoints da config (sem hardcode) e confere: a API responde
com host real e sessões; o servidor OPC UA expõe os grupos `TimeSeries` e
`EnergyEfficiency`; e o `twin-sync` já escreveu KPIs não-zero no submodelo
`EnergyEfficiency` do BaSyx. Rode após `make run` (dê alguns segundos para os
dados fluírem).
