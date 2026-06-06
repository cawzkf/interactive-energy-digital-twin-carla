# CARLA (opcional)

Integração **opcional e removível** com o simulador CARLA, usado como fonte de
dados (`ACQ_SOURCE=carla`) enquanto o B.O.M. não é liberado. O CARLA roda no
**host Windows** (precisa de GPU) — não é containerizado junto com o restante do
stack.

## Instalar (uma vez, ~10–20 GB)

```powershell
powershell -ExecutionPolicy Bypass -File carla\download-carla.ps1 -Version 0.9.15 -Dest C:\CARLA
```

Ou baixe manualmente em <https://github.com/carla-simulator/carla/releases> e
extraia para uma pasta. Defina `CARLA_HOME` apontando para ela.

## Subir

```bash
make carla                 # inicia o CarlaUE4.exe (detached) no host Windows
ACQ_SOURCE=carla make run  # sobe o stack consumindo do CARLA
```

Ou direto no Windows:

```powershell
powershell -ExecutionPolicy Bypass -File carla\start-carla.ps1 -Quality Low
```

O cliente Python conecta no host pelo gateway do WSL (ver
`src/infra/carla_client.py`). É preciso instalar o wheel `carla` no ambiente que
roda a aquisição.

## Remover por completo

Nada mais depende disto: basta **apagar a pasta `carla/`** e os alvos `carla*`
no `Makefile`. O app continua funcionando com `ACQ_SOURCE=sim` (padrão).
