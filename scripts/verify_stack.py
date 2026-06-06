"""Live smoke test of the deployed stack (API, OPC UA and BaSyx twin-sync).

Runs inside the backend image (it has the runtime deps) against the running
stack. Endpoints come from the environment config, not hardcoded values.
"""
import asyncio
import base64

import requests
from asyncua import Client

from src.infra.config import ApiConfig, OpcuaConfig, TwinConfig

API_URL = f"http://localhost:{ApiConfig.PORT}"
EFFICIENCY_ID = "https://marchforce.org/sm/energyefficiency"


def _encode_id(raw_id: str) -> str:
    return base64.urlsafe_b64encode(raw_id.encode()).decode().rstrip("=")


def check_api() -> bool:
    endpoints = requests.get(f"{API_URL}/api/endpoints", timeout=5).json()
    sessions = requests.get(f"{API_URL}/api/sessions", timeout=5).json()
    print(f"API endpoints={endpoints} sessions={len(sessions)}")
    return bool(endpoints.get("host")) and len(sessions) > 0


def check_opcua() -> bool:
    async def read() -> dict:
        url = OpcuaConfig.endpoint().replace("0.0.0.0", "127.0.0.1")
        groups: dict = {}
        async with Client(url=url) as client:
            for root in await client.nodes.objects.get_children():
                if (await root.read_browse_name()).Name != OpcuaConfig.SHELL_NAME:
                    continue
                for group in await root.get_children():
                    name = (await group.read_browse_name()).Name
                    groups[name] = len(await group.get_children())
        return groups

    groups = asyncio.run(read())
    print(f"OPC UA groups={groups}")
    return "TimeSeries" in groups and "EnergyEfficiency" in groups


def check_twin() -> bool:
    base = f"{TwinConfig.BASYX_URL}/submodels/{_encode_id(EFFICIENCY_ID)}/submodel-elements"
    elements = requests.get(base, timeout=5).json().get("result", [])
    values = {e["idShort"]: e.get("value") for e in elements}
    print(f"BaSyx EnergyEfficiency={values}")
    return any(float(v or 0) != 0 for v in values.values())


def main() -> int:
    checks = {"api": check_api, "opcua": check_opcua, "twin-sync": check_twin}
    failed = []
    for name, check in checks.items():
        try:
            ok = check()
        except Exception as error:  # noqa: BLE001
            ok = False
            print(f"[{name}] error: {error}")
        print(f"[{name}] {'OK' if ok else 'FAIL'}")
        if not ok:
            failed.append(name)
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
