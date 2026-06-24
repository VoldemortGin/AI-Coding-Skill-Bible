#!/usr/bin/env bash
# Derive ALL host bindings from the core — the ONLY way binding code is produced.
# Never hand-edit generated output; it is wiped on the next run. Generator versions are
# pinned in versions.toml / core/Cargo.toml. See polyglot-core-standard non-negotiables 2 & 4.
#
# Two postures coexist (uncomment the ones your repo uses):
#   • generated   (UniFFI/cbindgen/protobuf): emits host-language source → vendored, gate-excluded
#   • handwritten (PyO3/JNI): binding layer is governed Rust in the core; only the STUB is derived
set -euo pipefail
cd "$(dirname "$0")/.."

# ── Generated posture: UniFFI → Swift (apple host) ───────────────────────────────────────
# cargo build -p __REPO__-ffi --release
# cargo run -p __REPO__-ffi --bin uniffi-bindgen -- generate \
#   --library target/release/lib__REPO___core.dylib \
#   --language swift --out-dir apple/Generated

# ── Generated posture: UniFFI → Kotlin (android host) ────────────────────────────────────
# cargo run -p __REPO__-ffi --bin uniffi-bindgen -- generate \
#   --library target/release/lib__REPO___core.so \
#   --language kotlin --out-dir android/app/src/main/java

# ── Hand-written posture: PyO3 → regenerate the .pyi stub the host consumes ───────────────
# (the binding layer itself is hand-written Rust in core/crates/__REPO__-py; only the
#  published stub is a derived artifact, so the host's mypy sees the true contract)
# maturin develop -m core/crates/__REPO__-py/Cargo.toml
# python -m __REPO__._stubgen > python/src/__REPO__/_native.pyi

echo "✓ bindings derived — uncomment the invocations for your generator; pin versions in versions.toml"
