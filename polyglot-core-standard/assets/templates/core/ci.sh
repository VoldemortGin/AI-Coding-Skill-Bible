#!/usr/bin/env bash
# core/ gate — the canonical core's own zero-warning gate. The composed repo gate
# (`make check-core`) calls this. This is a FAITHFUL MINIMAL version; see
# rust-project-standard for the FULL gate (cargo-deny, doc warnings-as-errors, drift checks).
set -euo pipefail

cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings   # warnings are errors
cargo test --all-features                                  # unit + doctests
echo "✓ core gate green"
