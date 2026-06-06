#!/usr/bin/env bash
cd "$(dirname "$0")/.."
.venv/bin/pip install -q basyx-python-sdk 2>&1 | tail -n 3
.venv/bin/python aas-model/_validate.py
