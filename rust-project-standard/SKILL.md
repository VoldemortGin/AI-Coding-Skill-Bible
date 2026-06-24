---
name: rust-project-standard
description: >-
  Enforce a strict, model-agnostic, AI-navigable Rust project standard: a Cargo
  workspace with crate-per-domain deep structure, #![forbid(unsafe_code)] + strict
  clippy workspace lints + a one-command zero-warning gate (fmt + clippy -D warnings
  + doc + test + cargo-deny), serde + newtypes at boundaries, trait-based provider
  seams with a zero-SDK domain crate and a default MockProvider, tracing, figment,
  include_str! + minijinja prompts, and a CLAUDE.md in every crate. Use whenever
  starting or scaffolding a Rust project, crate, or workspace; setting up Cargo.toml /
  clippy / rustfmt / CI; deciding crate or module structure; adding an LLM / embedding /
  vector-store dependency; wiring providers or adapters; setting up cargo-deny or
  supply-chain/license checks; or checking an existing Rust project conforms. Apply
  even when the user only says "start a Rust project", "structure this crate", "add an
  LLM", or "wire up CI" without naming the standard.
---

# Rust Project Standard

This skill is the guiding standard for **any** Rust work. Apply it by default; don't wait to be asked.

Its spine: **trust is placed not in the model, but in the machine-checkable code that constrains it.** In Rust most of that scaffold is the compiler — types, ownership, exhaustiveness are enforced at compile time with no type erasure, so there's **no runtime type-checker to bolt on** (unlike the Python sibling's beartype). The job here is to (a) keep the few escape hatches shut, (b) push every external dependency behind a trait so the model is hot-swappable, (c) organize deep and name-navigable, and (d) mechanize the implicit knowledge a human would otherwise hold — via a zero-warning gate, per-crate contracts, and supply-chain checks. The agent's output ceiling equals the tightness of that loop.

Baseline: **edition 2024**, pinned toolchain (`rust-toolchain.toml`), `#![forbid(unsafe_code)]`, strict clippy via workspace lints, `serde`, `thiserror`/`anyhow`, `tracing`, `figment`, `minijinja`, `cargo-deny`.

## When starting a new project

```bash
python scripts/scaffold.py <project_name> --target <dir> --domains ingestion retrieval generation agents
```

This mirrors `assets/templates/` into a Cargo workspace (root config + `kernel`/`domain`/`adapters` crates + `app` binary + a CLAUDE.md per crate + `ci.sh` + CI + ADR), substitutes `__PROJECT__`, and creates a crate skeleton per domain (`members = ["crates/*", "app"]` auto-includes them). When adapting an existing repo, copy from `assets/templates/` by hand — only the workspace root, `app/Cargo.toml`, and CLAUDE.md headers carry the literal name; crate names (`kernel`/`domain`/`adapters`) are project-independent so `use` paths never depend on the project name.

Then: `cargo check`, and `./ci.sh` (or `just check`) to verify. `./ci.sh` needs `cargo install cargo-deny` once (CI uses the action).

## When working on existing code

Apply the rules below, and verify structural invariants:

```bash
python scripts/check_conformance.py <project_root>
```

It checks the mechanically enforceable invariants (workspace layout, `unsafe_code = "forbid"`, clippy lints configured, **`domain` crate has zero vendor-SDK deps** — parsed from its Cargo.toml, cleaner than grep, toolchain/deny/ci files present, **a CLAUDE.md in every crate**). Everything else is enforced by the gate and by applying the standard.

## The non-negotiables

Full rationale in `references/standard.md`.

1. **The compiler is the static guarantee; keep the escape hatches shut.** `#![forbid(unsafe_code)]` at the workspace level (a hard ban — `#[allow]` can't override `forbid`). Strict clippy via `[workspace.lints]`; the gate runs `clippy -- -D warnings`, so every warning is fatal. No bolted-on runtime type check — Rust doesn't need one. A crate that genuinely needs `unsafe` (FFI, SIMD) takes the **controlled exit** in `references/standard.md` §2 — isolate it in a dedicated crate that opts out of the workspace lint and drops to `deny` + per-site `// SAFETY:`, rather than loosening the workspace.

2. **No silent failures: `Result<T, E>` + `thiserror`, not `unwrap`/`expect` sprinkled around.** `unwrap_used`/`expect_used`/`panic` are clippy-warn (→ error at the gate); escaping needs `#[allow(...)]` with a reason (the Rust analog of a justified `# type: ignore`). `unwrap`/`expect` are allowed in tests (`clippy.toml`). Vendor errors normalize at the adapter boundary into `domain::ProviderError`; program bugs propagate — never swallow.

3. **Boundaries: parse, don't validate — `serde` + newtypes.** Everything crossing a boundary (config, LLM output, tool results, files) deserializes into a strongly-typed struct via `serde`; encode constraints in newtypes so invalid states are unrepresentable rather than runtime-checked.

4. **Model-agnostic: every external AI dependency behind a trait in `domain`; SDKs only in `adapters`.** The `domain` crate has **zero vendor-SDK dependencies** (the checker parses its Cargo.toml to enforce this); traits stay object-safe (`Box<dyn _>`). SDKs are `optional` + feature-gated in `adapters` and normalized to `ProviderError`. The composition root (`app`) is the one place that selects an impl by config and injects it. A deterministic **MockProvider is the default** (not a test stub) so the binary, tests, and CI run offline with no SDK or key.

5. **Completion = one zero-warning gate, the agent's only correctness judge.** `./ci.sh` runs `cargo fmt --check` → `clippy -D warnings` → `cargo doc` (with `RUSTDOCFLAGS=-D warnings`) → `cargo test` → `cargo deny check`, under `set -euo pipefail`. Run it after every change; fix until green; never "looks fine, commit". Pin it with a pre-push hook; CI mirrors it.

6. **`cargo-deny` is part of the gate.** License allow-list (rejects AGPL/GPL/SSPL leaking into the tree), RUSTSEC advisories, and dependency hygiene are checked on every run — this doubles as supply-chain/SCA compliance.

## Structure: deep Cargo workspace, crate-per-domain

The depth comes from the workspace, not from one crate with deep modules. "Fix the reranker" should resolve to `crates/retrieval/src/reranking/` with no search.

- **Workspace with a crate per bounded context** (`crates/<domain>/`), plus the fixed infra crates and a thin binary:
  - `kernel` — cross-cutting infra: `config` (figment, env `APP_*` + `__` nesting), `logging` (`tracing`; init once in the binary; library code only emits events; `log_provenance` + payload-free traces), `prompts` (`include_str!` compile-time embed + `minijinja` strict undefined). Named `kernel`, not `core` (which collides with `std::core`).
  - `domain` — ports (traits) + models + boundary errors; **zero SDK deps**.
  - `adapters` — trait impls; the only crate that may depend on vendor SDKs (feature-gated); `MockX` defaults.
  - domain crates (`ingestion`/`retrieval`/…) depend on `domain` + `kernel`, never on `adapters` or SDKs.
  - `app` — the binary and composition root; wires concrete adapters by config.
- **A `CLAUDE.md` in every crate** (the layered-context rule applied per directory): the root one is a routing table (hard constraints + where to look); each crate's states its responsibility, dependencies, and local contract. The checker requires one per crate.
- Go **deep**: split crates into submodules by sub-capability; names map to paths.

## Navigability

Naming-as-path is to navigation what types are to interface contracts — and Cargo workspaces make it crate-level. Group by capability, not by `types/`/`utils/`. Nest until leaf modules have a single clear responsibility. See `references/standard.md`.

## Principles for AI-touching code (advisory)

Beyond the type system — for any code where a model produces output. Upper-level discipline; not all mechanically checkable.

- **Constrain, don't ask.** Push non-negotiable properties (no fabrication, must-cite, no privilege escalation) into deterministic control flow so the model *physically cannot* violate them — don't rely on the prompt. Synthesize answers from typed values in code; discard model prose on the critical path.
- **Narrow the emission surface.** Make the model pick from a typed enum of options or call tools returning a tri-state result; take final values from tool results, not free-form model text. A Rust `enum` is the natural controlled surface.
- **Guardrails are deterministic, independent, never pluggable.** Intent parsing can be swapped; safety decisions are deterministic code re-evaluated from raw input.

## Driving AI on big work (advisory)

Treat AI as supervisable labor, not unsupervised autopilot.

- **Decision-first: a numbered, immutable ADR (`docs/adr/`) before coding** — context + chosen option + rejected alternatives and why. Rejected-reasons stop it re-walking excluded paths.
- **TDD red-light first; tests are the immutable spec.** Write the failing `#[test]` (or doc test), then implement to green; never weaken a test to pass.
- **Numbered steps, each independently green; one commit per step through the full gate.** No giant diffs.
- **Adversarial independent review.** After writing, run a separate, hostile, multi-perspective review prioritizing what tests can't cover (diagrams, docs, tradeoffs).

## Scale to project size

The workspace split, per-crate CLAUDE.md, ADRs, and cargo-deny are real overhead — overkill for a 200-line CLI. Present them as **triggered, scalable patterns** ("the moment you call an LLM/embedding/vector store, put it behind a trait in its own crate"; "split a crate out the moment it takes a second responsibility"), not blanket mandates. A single-crate project with modules + clippy + the gate is a perfectly good small-scale instantiation.

Scale along **two axes, not one** — size *and* domain. The standard has a **universal spine** that holds for any Rust project whether or not it touches AI: `#![forbid(unsafe_code)]`, the zero-warning gate, `Result`/`thiserror` (no silent failure), `serde` + newtypes at boundaries, workspace + deep naming-as-path, `cargo-deny`, `tracing`, `figment`. The rest is an **AI-triggered layer** that only switches on once the project actually calls an LLM / embedding / vector store: the `domain` trait seam, `MockProvider`-as-default, `minijinja` / `include_str!` prompts, `log_provenance`, and the constrain-don't-ask / narrow-the-emission-surface discipline. A pure systems / library / CLI crate that never calls a model should take the spine in full and skip the AI layer outright — bolting `MockProvider` or prompt-embedding onto such a project is cargo-culting, not conformance.

## Resources

- `references/standard.md` — the full standard with rationale and complete code for every crate.
- `assets/templates/` — exact workspace boilerplate; `__PROJECT__` is the only placeholder. Includes `kernel`/`domain`/`adapters`/`app`, workspace lints, `clippy.toml`, `deny.toml`, `ci.sh`, GH Actions, a per-crate CLAUDE.md, and `docs/adr/`.
- `scripts/scaffold.py` — generate a conforming workspace.
- `scripts/check_conformance.py` — verify structural invariants (incl. domain-zero-SDK and per-crate CLAUDE.md).
