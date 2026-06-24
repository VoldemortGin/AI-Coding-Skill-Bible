# core/ — canonical core (rust-project-standard)

The single source of truth: all shared logic + the cross-language data model. Conforms to
**rust-project-standard** in full — Cargo workspace, `#![forbid(unsafe_code)]`, strict
clippy workspace lints, the zero-warning gate via `./ci.sh`, `domain` crate zero-SDK,
`serde` + newtypes at boundaries. That standard governs everything *inside* this sub-tree.

## Seam-local contract (polyglot-core-standard)

- **The cross-language interface is declared HERE and nowhere else** — UniFFI
  `#[uniffi::export]` / a `.udl` in the `__REPO__-ffi` crate, and/or PyO3 `#[pymethods]`
  in `__REPO__-py`. Hosts derive bindings from this; they never hand-mirror a struct.
- **No `panic!` may cross an FFI boundary.** Every recoverable failure becomes a typed
  error enum that maps to the host's idiomatic error. `unwrap`/`expect`/`try!`/indexing
  in code reachable across the boundary is a defect, not a shortcut — propagate a typed
  error instead.
- **The `__REPO__-ffi` / `__REPO__-py` crate is the ONE controlled exit** from
  `#![forbid(unsafe_code)]`: it opts out of the workspace forbid, drops to `unsafe = "deny"`,
  and carries per-site `// SAFETY:` notes — keeping the rest of the workspace hard-forbidden.
- **After any interface change**, run `make gen-bindings` from the repo root and commit the
  regenerated host bindings in the SAME commit. The freshness guard (`make check-bindings`)
  will fail otherwise.
- If the core itself calls a model, the AI provider seam (trait in `domain` + default
  `MockProvider`) lives **here** and hosts consume typed results across the boundary.
