#!/usr/bin/env bash
# Regenera docs/diagrams/svg y docs/diagrams/png a partir de docs/diagrams/src/*.mmd
# Requiere Node.js (brew install node). La primera vez descarga mermaid-cli.
set -euo pipefail
cd "$(dirname "$0")/../docs/diagrams"
mkdir -p svg png
for f in src/*.mmd; do
  n=$(basename "$f" .mmd)
  npx -y @mermaid-js/mermaid-cli -c src/mermaid.config.json -i "$f" -o "svg/$n.svg" -b white -q
  npx -y @mermaid-js/mermaid-cli -c src/mermaid.config.json -i "$f" -o "png/$n.png" -b white -s 2 -q
  echo "OK $n"
done
