#!/usr/bin/env bash
# Binding-freshness drift guard (polyglot-core-standard non-negotiable 5).
# Regenerate every binding + type stub from the CURRENT core, then fail if the committed
# artifacts differ — i.e. the core's interface changed but a host's binding was never
# regenerated. This is the cross-language analog of the per-language drift checks; it
# closes the one hole generation cannot close itself: forgetting to run gen-bindings.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ regenerating all bindings from the core (single source of truth)…"
bash scripts/gen_bindings.sh

echo "→ verifying committed bindings match the regenerated output…"
# List every derived path here (mirror versions.toml [bindings]).
DERIVED=(apple/Generated python/src/*/_native.pyi)
if ! git diff --exit-code -- "${DERIVED[@]}" 2>/dev/null; then
  echo "" >&2
  echo "✗ STALE BINDINGS — the core changed but committed bindings did not." >&2
  echo "  Fix: run 'make gen-bindings' and commit the result in the SAME commit as the" >&2
  echo "  core interface change. A contract change is one coherent multi-sub-tree commit." >&2
  exit 1
fi
echo "✓ bindings are fresh"
