#!/usr/bin/env bash
# __REPO__ — root gate entrypoint: a thin wrapper over the composed Makefile gate.
# CI calls this and the pre-push hook pins it, so every caller runs the SAME judge
# as `make check` — core + every host + binding freshness. The Makefile is the
# routing table; the real per-seam logic lives in each sub-tree's ci.sh. See CLAUDE.md.
set -euo pipefail

make check
