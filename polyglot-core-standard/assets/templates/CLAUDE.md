# __REPO__ — root routing table (polyglot-core-standard)

This repo is governed by **polyglot-core-standard**: one canonical core, thin hosts,
derived bindings, one composed gate. This file is the *routing table* — the hard
cross-language constraints + where each thing lives. Each sub-tree's own CLAUDE.md holds
its local contract and defers to its language standard (rust/swift/python-project-standard).

## Hard constraints (the cross-language seams)

1. **`core/` is the single source of truth.** All shared logic + the data model live here
   (Rust, per rust-project-standard). Never reimplement a shared rule in a host. The smell:
   you're about to write the same validation/crypto/parse/state-machine in two languages.
2. **The contract is declared once; bindings are derived.** Never hand-copy a core struct
   into a host. Binding emission is a build step (`make gen-bindings`), not a manual port.
3. **The FFI boundary is typed & fallible; no `panic!` crosses it.** Core `Result<T,E>` →
   host error (`throws` / `raise` / checked exception). A thin hand-written wrapper on each
   host re-types results; that wrapper IS governed, the generated file is not.
4. **Generated bindings are vendored** — gate-excluded, `linguist-generated`, never edited.
   Hand-written binding layers (PyO3/JNI) are governed core code.
5. **`make check` is the only correctness judge** — it runs every sub-tree's gate + the
   binding-freshness guard. Never "looks fine" on a single language.
6. **Toolchains + generator versions are pinned in `versions.toml`** — the single matrix.

## Where things live

| Path | What | Standard |
|---|---|---|
| `core/` | Rust workspace, canonical truth, the cross-language contract | rust-project-standard → `core/CLAUDE.md` |
| `apple/` | Swift host (spine-only); generated UniFFI binding in `apple/Generated/` | swift-project-standard → `apple/CLAUDE.md` |
| `python/` | Python host (spine-only); PyO3 stub `src/__REPO__/_native.pyi` | python-project-standard → `python/CLAUDE.md` |
| `scripts/gen_bindings.sh` · `scripts/check_bindings.sh` | derive + drift-guard bindings | — |
| `versions.toml` | pinned toolchain + generator matrix | — |
| `Makefile` | the composed gate | — |
| `docs/adr/` | decision records (one before any contract change) | — |

## Adding a host / changing the contract

A contract change is a **multi-sub-tree change**: write an ADR first → change the core →
`make gen-bindings` → adapt every host's hand-written wrapper → `make check` green →
**one** coherent commit (never split across states where some bindings are stale).
