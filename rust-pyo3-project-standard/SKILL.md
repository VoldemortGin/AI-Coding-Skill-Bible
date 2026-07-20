---
name: rust-pyo3-project-standard
description: >-
  Enforce a strict project standard for Rust-backed Python packages built with
  PyO3 and Maturin, including abi3 compatibility, Python wrapper typing, wheel
  packaging, cross-platform CI, API/documentation parity, and release gates.
  Use when creating, auditing, restructuring, testing, or releasing a repository
  containing Cargo.toml plus pyproject.toml with maturin/PyO3; when deciding
  whether Python-project-standard rules such as src layout, Python 3.13,
  beartype, or pydantic apply; or when a Rust extension exposes Python APIs.
---

# Rust/PyO3 Project Standard

Apply this profile together with `python-project-standard` and
`rust-project-standard`. It defines narrow substitutions for conflicts caused by
Maturin, PyO3, and abi3; it is not a general waiver from either standard.

Read `references/standard.md` before designing, auditing, or changing a project.

## Classify the repository

Use this profile only when all of these are true:

- Rust is the canonical implementation or extension core.
- Python exposes that core through PyO3.
- Maturin builds the Python distributions.
- The repository ships an importable Python package, not merely a private Rust
  binary that embeds Python.

Use `polyglot-core-standard` instead when one canonical core serves multiple
first-class host languages. Continue applying this profile to the Python host.

## Apply the exception map

Keep every unlisted rule from both parent standards. Permit only these explicit
substitutions:

1. **Maturin source layout:** accept `python/<package>/` when
   `[tool.maturin].python-source = "python"` and the built wheel contains exactly
   that package. Do not accept a loose root package or `import src`.
2. **Python compatibility floor:** derive `requires-python` from the documented
   abi3 compatibility promise. It may be lower than 3.13. Test every declared
   minor version and build with the matching lowest PyO3 abi3 feature.
3. **Runtime typing:** require strict static typing for the Python wrapper.
   Require beartype only for substantial pure-Python domain logic. Do not wrap
   native PyO3 callables merely for formal compliance.
4. **Boundary validation:** Rust parsers may own validation of native binary
   formats. Require pydantic for Python-owned structured process boundaries such
   as JSON, HTTP, configuration, or model output; do not translate a byte buffer
   into a pydantic model without a domain reason.
5. **Domain placement:** Rust may own domain logic. Keep Python bindings thin and
   do not duplicate Rust validation or business rules in Python.

Never use an exception without recording the evidence in an ADR or equivalent
tracked architecture decision. The record must name the substituted parent
rule, chosen behavior, compatibility evidence, affected files, and a trigger for
revisiting the decision.

## Keep the hard gates

Require one root command that fails on every relevant warning and runs:

- `cargo fmt --check`
- `cargo clippy --all-targets --all-features -- -D warnings`
- Rust tests and dependency policy checks
- `ruff format --check` and `ruff check`
- `mypy --strict` over handwritten Python and public stubs
- pytest with warnings as errors
- sdist and wheel builds
- installation/import smoke tests against built wheels
- API, stub, documentation, and generated-artifact drift checks

Run the same command in pre-push and CI. Test Linux, macOS, and Windows when the
package claims support for them. Test the lowest and highest supported Python
versions; test intermediate versions when release risk warrants it.

## Preserve one public contract

Treat the following as synchronized views of one API:

- PyO3 exports
- Python wrappers
- `.pyi` stubs and `py.typed`
- README and reference documentation
- bundled LLM-facing documentation
- wheel contents and import paths

Generate or mechanically compare these surfaces where practical. A new native
method is incomplete until the wrapper, stub, tests, and user documentation
agree.

## Audit an existing project

Run:

```bash
python scripts/check_conformance.py <project-root>
```

Then run the project's root quality command and inspect the non-mechanical rules
in `references/standard.md`. Report `N/A`, `profile exception`, and
`noncompliant` separately. Never count an applicable failure as an exception.

## Change safely

Before editing:

1. Read the repository instructions, README, and architecture/release docs.
2. Inspect existing Rust and Python implementations before adding abstractions.
3. State which parent-standard rules are being substituted and why.
4. Make the smallest cross-language change that keeps every contract surface in
   sync.
5. Build distributions and test the installed artifacts, not only the source
   checkout.
6. Run the complete root gate before committing or publishing.

Do not silently raise the Python floor, change abi3, rename the import package,
or alter wheel contents. Treat each as a compatibility decision requiring
explicit review.

## Resources

- `references/standard.md` contains the complete exception rationale,
  architecture rules, gate, documentation policy, and audit rubric.
- `scripts/check_conformance.py` checks the mechanically detectable baseline.
