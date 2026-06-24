#!/usr/bin/env bash
# python/ gate — the Python host's own zero-warning gate; the composed repo gate
# (`make check-python`) calls this. FAITHFUL MINIMAL version; see python-project-standard for
# the FULL gate (beartype runtime types, drift guard, pytest warnings-as-errors).
#
# SEAM RULE (non-negotiable 4): the generated stub `src/__REPO__/_native.pyi` is a vendored
# artifact — ruff `extend-exclude`s it (pyproject.toml) — but mypy READS it as the typed
# contract for the `__REPO__._native` PyO3 module.
set -euo pipefail

ruff format --check .
ruff check .
mypy src                  # reads src/__REPO__/_native.pyi as the PyO3 contract stub
# pytest                  # boundary tests: native dict -> validated pydantic model
echo "✓ python gate green"
