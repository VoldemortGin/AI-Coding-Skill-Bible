# Rust/PyO3 Project Standard

## Contents

1. Scope and precedence
2. Allowed substitutions
3. Architecture
4. Type and error contracts
5. Packaging and compatibility
6. Tests and quality gate
7. Documentation and API drift
8. Audit rubric

## 1. Scope and precedence

This profile governs a Python distribution whose implementation includes a Rust
extension built with PyO3 and Maturin. Apply `rust-project-standard` to Rust and
`python-project-standard` to handwritten Python. This document wins only where
it explicitly defines a PyO3-specific substitution.

An exception must preserve the parent rule's intent, be narrow, and be
machine-checkable. Record compatibility choices such as Python floor, abi3
baseline, source layout, and Rust/Python ownership in an ADR or an equivalent
tracked decision. That record must state the substituted parent rule, decision,
evidence, affected files, and a measurable revisit trigger. Scattered comments
do not qualify when they disagree.

This profile does not excuse lint failures, undocumented public APIs, loose
typing, silent failures, untested wheels, or stale documentation.

## 2. Allowed substitutions

### 2.1 Source layout

`python/<package>/` is conforming when all conditions hold:

- `[build-system].build-backend = "maturin"`
- `[tool.maturin].python-source = "python"`
- `[tool.maturin].module-name` resolves inside the public package
- the distribution includes `python/<package>/py.typed`
- an installed-wheel smoke test imports the expected public package

`src/<package>/` remains valid. A root-level package, path mutation, rootutils,
or tests that pass only from a checkout are not valid substitutions.

### 2.2 Python version and abi3

Python 3.13 is not a mandatory floor for abi3 libraries. The declared floor is
a product compatibility promise and must agree across:

- `project.requires-python`
- PyO3's `abi3-pyXY` feature
- classifiers
- CI test matrix
- wheel tags and release matrix
- user documentation

Use the oldest supported Python in build and smoke-test jobs. Raising the floor
or abi3 baseline is a breaking compatibility decision even when source code does
not change.

Modern syntax is bounded by the declared floor. Prefer native syntax available
at that floor. Permit `from __future__ import annotations` only when needed for
supported interpreters or runtime annotation behavior; document the reason and
test consumers that inspect annotations. Do not combine it blindly with runtime
type instrumentation.

### 2.3 Runtime type checking

Keep `mypy --strict` for handwritten Python and public stubs. Native PyO3
functions already cross a checked Rust conversion boundary; beartype is not
required around generated/native callables.

Use beartype when pure-Python modules own domain policy, state transitions, or
data transformations beyond argument normalization and ergonomic delegation to
Rust. Wrapper size alone does not trigger it. If enabled, preserve the parent
standard's central hook and import ordering rules. Never scatter decorators
across wrappers.

### 2.4 Boundary validation

Let Rust validate formats it canonically parses, such as PDF bytes or native
binary structures. Map Rust failures into a documented Python exception
hierarchy.

Use pydantic for Python-owned structured boundaries: configuration, JSON, HTTP,
subprocess records, tool results, or model output. `argparse` is sufficient for
a simple CLI whose values are immediately converted into typed domain inputs.

### 2.5 Domain ownership

Maintain one canonical implementation. Rust owns performance-sensitive parsing,
validation, and transformations when designated as the core. Python owns
ergonomic wrappers, Python protocols, path-like handling, context management,
and presentation helpers. Do not independently implement the same rule in both
languages.

## 3. Architecture

A typical mixed project may use:

```text
Cargo.toml
crates/
  core/
  python/
python/
  package/
    __init__.py
    _core.pyi
    py.typed
    document.py
tests/
  rust/
  python/
scripts/
pyproject.toml
ci.sh
```

The exact Rust workspace shape may vary. Preserve these boundaries:

- Rust core crates do not depend on Python.
- The PyO3 crate adapts Rust types and errors to Python.
- Python wrappers import the extension through one stable internal module.
- Public imports come from the named Python package.
- Generated code and handwritten code have clear ownership.

Avoid a Python mirror of the Rust module tree unless it improves the public API.
Navigation should follow public capabilities, not implementation language.

## 4. Type and error contracts

Ship `py.typed` and complete public `.pyi` files when the native extension cannot
expose sufficient annotations itself. Type-check stubs and representative
consumer programs.

Avoid `Any` in public signatures. A narrow `Any` for an intentionally dynamic
Python protocol requires a comment and a test. Parameterize collections and
annotate every handwritten function under the strict gate.

Define a stable Python exception hierarchy. Preserve causal information when
mapping Rust errors. Do not catch `Exception` to continue with a fallback unless
the fallback is a documented part of the API and the original failure remains
observable.

Panics must not cross the FFI boundary. Prefer Rust `Result` values and explicit
conversion to Python exceptions.

## 5. Packaging and compatibility

Use one canonical version source or a mechanical equality check across Cargo,
Python metadata, generated module attributes, and release tags.

Build both sdist and wheels. Validate:

- clean-environment installation
- expected import package and version
- native module loading
- package data, stubs, licenses, and bundled documentation
- absence of repository-only paths and unintended large assets
- lowest-supported-Python compatibility
- platform and architecture wheel tags

Use Maturin's supported configuration instead of custom copying where possible.
Pin the Rust toolchain and lock dependencies appropriate to a library release.

Do not publish until the exact artifacts that passed smoke tests are the
artifacts selected for release.

## 6. Tests and quality gate

Expose one root command such as `./ci.sh` or `make check`. It must stop on the
first failure and include, as applicable:

```text
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo deny check
ruff format --check
ruff check
mypy --strict
pytest -W error
maturin build / build --sdist
installed-wheel smoke tests
API/stub/docs drift checks
```

Mirror the command in CI and pre-push. Extra fuzzing, sanitizers, benchmarks,
compatibility fixtures, or supply-chain jobs strengthen the gate, but required
checks must not use `continue-on-error`.

Test at three layers:

1. Rust unit/property tests for canonical behavior.
2. Python API tests for conversion, lifecycle, exceptions, and ergonomics.
3. Built-wheel tests for packaging, imports, stubs, and dynamic loading.

Tests that import only from the checkout cannot prove a wheel is correct.

## 7. Documentation and API drift

Every public capability must agree across implementation, wrapper, stub, tests,
README/reference docs, bundled agent/LLM docs, and the published site.

Prefer generated API references and executable examples. Add deterministic drift
checks for:

- public names versus stubs
- version values
- compatibility tables
- feature flags and optional dependencies
- bundled models/assets versus distribution metadata
- generated docs or manifests

Document which layer owns expensive work and whether calls release the GIL.
Document thread-safety, object lifetime, path/bytes support, exception types, and
platform limitations when relevant.

Historical changelog entries are historical evidence, not current documentation.
Do not rewrite them merely because current packaging changed.

## 8. Audit rubric

Report each item as:

- **Conforming:** meets the parent standards or this profile.
- **Profile exception:** violates a parent literal but meets every substitution
  condition here; cite the evidence.
- **Noncompliant:** an applicable rule fails or an exception lacks evidence.
- **N/A:** the capability does not exist, such as LLM provider architecture in a
  PDF parser.

Audit at least:

1. Repository classification and canonical domain owner
2. Rust formatting, linting, tests, dependency policy, and panic safety
3. Python layout, Ruff, strict typing, runtime validation decision, and warnings
4. PyO3 conversion and exception contracts
5. abi3/version metadata consistency
6. sdist/wheel contents and installed-artifact smoke tests
7. OS/Python/architecture CI matrix
8. public API, stubs, docs, bundled docs, and website parity
9. one-command local/CI/pre-push gate
10. explicit ADRs for every profile exception

Do not produce a single percentage that hides hard failures. Lead with the
mechanical result, then separate exceptions, strengths, and remediation.
