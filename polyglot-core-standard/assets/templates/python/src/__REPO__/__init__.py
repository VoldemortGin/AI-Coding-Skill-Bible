"""`__REPO__` — the Python host over the shared Rust core (polyglot-core-standard).

A thin host: the PyO3 binding layer lives in the core (`core/crates/__REPO__-py`); this package
re-types the native return values into validated pydantic models at the boundary. The public
API is re-exported from `client` — never import the raw `_native` module from host logic.
"""
from __REPO__.client import CoreClientError, Totp, parse_otpauth

__all__ = ["CoreClientError", "Totp", "parse_otpauth"]
