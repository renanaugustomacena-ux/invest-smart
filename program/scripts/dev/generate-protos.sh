#!/usr/bin/env bash
set -euo pipefail

echo "=== Generating Protocol Buffer code ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="$(cd "$SCRIPT_DIR/../../shared/proto" && pwd)"

cd "$PROTO_DIR"
make all

echo "=== Proto generation complete ==="
echo "Python output: $PROTO_DIR/gen/python/"
echo "Go output:     $PROTO_DIR/gen/go/"
