#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOC="$ROOT/docs/technical_report"
IMG="${TEXLIVE_IMAGE:-texlive/texlive:latest}"

docker run --rm -v "$DOC:/work" -w /work "$IMG" \
  latexmk -pdf -interaction=nonstopmode -halt-on-error relatorio-digital-twin-energetico.tex

echo "PDF: docs/technical_report/relatorio_atualizado.pdf"
