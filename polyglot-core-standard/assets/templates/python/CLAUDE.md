# python/ — Python host (python-project-standard, spine-only)

A thin host over the core, exposed via a **hand-written PyO3 binding layer**. Conforms to
**python-project-standard**'s spine: `mypy --strict`, ruff, beartype via the central
switch, pydantic at boundaries, the zero-warning gate via `./ci.sh`. **No AI layer**
unless this host itself calls a model.

## Seam-local contract (polyglot-core-standard)

- **Posture = hand-written.** The PyO3 binding layer lives in the CORE
  (`core/crates/__REPO__-py`, Rust `#[pymethods]`) and is **governed core code** — it
  conforms to rust-project-standard, and crucially **no `panic!` crosses the boundary**:
  every failure is converted to a `PyErr` (so Python sees a normal exception, not an abort).
- **`src/__REPO__/_native.pyi` is the published contract stub** the host's mypy reads — a
  **derived, drift-guarded** artifact (`make check-bindings` regenerates it from the compiled
  module and fails on drift). It is `linguist-generated`; never let it drift from the Rust
  `#[pymethods]` signatures by hand-editing.
- **Cross the boundary into pydantic at the entry point** (parse, don't validate): the raw
  native return values are re-typed into pydantic models / newtypes before flowing into host
  logic — the Python analog of the Swift wrapper.
