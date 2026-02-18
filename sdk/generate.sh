#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "1. Extracting OpenAPI spec..."
cd "$ROOT/backend"
python -c "
import json, sys; sys.path.insert(0, '.')
from app.main import app
spec = app.openapi()
with open('../sdk/openapi.json', 'w', encoding='utf-8') as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)
print('openapi.json extracted')
"

echo "2. Generating Python client..."
cd "$ROOT"
openapi-python-client generate \
  --path sdk/openapi.json \
  --output-path sdk/python \
  --config sdk/config.yaml \
  --overwrite

echo "Done! Install with: pip install -e sdk/python"
