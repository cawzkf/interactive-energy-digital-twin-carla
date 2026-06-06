#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "=== validar XML (basyx-python-sdk) ==="
.venv/bin/python aas-model/_validate.py
echo "=== empacotar .aasx ==="
.venv/bin/python aas-model/package_aasx.py
echo "=== copiar para basyx-setup/aas/ ==="
cp aas-model/vehicle-digitaltwin.aasx basyx-setup/aas/vehicle-digitaltwin.aasx
ls -la basyx-setup/aas/
echo "=== testes ==="
.venv/bin/python -m pytest -q 2>&1 | tail -n 4
