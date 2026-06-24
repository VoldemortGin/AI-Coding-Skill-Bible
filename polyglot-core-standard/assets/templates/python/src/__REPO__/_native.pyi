# Drift-guarded PyO3 contract stub (polyglot-core-standard non-negotiables 4 & 5).
#
# This is the host's view of `core/crates/__REPO__-py`'s #[pyfunction] signatures — a DERIVED
# artifact: `make check-bindings` regenerates it from the compiled module and FAILS the gate on
# drift (core changed, stub didn't). It is `linguist-generated` and ruff-excluded; NEVER hand-edit
# it to match the Rust core — regenerate instead. mypy reads it as the truth for `__REPO__._native`.
def parse_otpauth(uri: str) -> dict[str, object]:
    """Parse an otpauth:// URI into a dict. Raises ``ValueError`` on malformed input.

    The Rust `CoreError` is converted to a `PyErr` at the boundary (never a panic/abort).
    """
    ...
