---
name: polyglot-core-standard
description: >-
  Enforce a strict, drift-free, AI-navigable standard for polyglot repos built around a shared
  native core (typically a Rust core) consumed by host languages (Swift, Kotlin, Python, …) through
  generated (UniFFI/cbindgen/protobuf) or hand-written (PyO3/JNI) bindings. It governs the seams
  between languages — not each language's internals, which it delegates to rust/swift/python-
  project-standard. The non-negotiables: one canonical core owns all shared logic + the data model;
  the cross-language contract is declared exactly once and bindings are derived, never hand-mirrored;
  the FFI boundary is the typed, fallible, parse-don't-validate seam and no panic ever crosses it;
  generated bindings are vendored artifacts excluded from gates while hand-written binding layers are
  governed core code; binding freshness is drift-guarded; one composed repo-level zero-warning gate
  runs every sub-tree's gate; the toolchain + binding-generator matrix is pinned; the AI provider
  seam lives in exactly one sub-tree; and a CLAUDE.md routing table sits at the root and in every
  sub-tree. Use whenever a repo has a shared core called from more than one language; setting up
  UniFFI / PyO3 / cbindgen / JNI bindings; deciding where shared logic vs host code belongs;
  composing per-language gates into one CI; guarding binding freshness; pinning a cross-language
  toolchain; or checking that an existing multi-language repo conforms. Apply it even when the user
  only says "Rust core with Swift/Python bindings", "set up the monorepo", "add a Kotlin binding",
  or "wire up the cross-language build", without naming the standard.
---

# Polyglot Core Standard

This skill is the guiding standard for **any repo where one shared core is called from more than one language**. Apply it by default; don't wait to be asked.

Its spine: **trust is placed not in any one language's checker, but in the machine-checkable contract at every seam between languages.** Each per-language standard (rust/swift/python-project-standard) already secures its own sub-tree; that is necessary but not sufficient. A polyglot repo fails at the *seams the single-language checkers cannot see*: the core and a host drift apart, the same struct is hand-copied into four languages and three of them rot, a Rust `panic!` unwinds across an FFI boundary into undefined behavior, "the build is green" means one language's build while another's binding is stale. So the job here is to (a) collapse shared truth to **one canonical core** and **derive** every binding rather than hand-mirror it, (b) make the **FFI boundary itself typed, fallible, and abort-safe**, (c) **drift-guard** every generated artifact, and (d) compose the per-language gates into **one gate that crosses every seam**. The repo's correctness ceiling equals the tightness of its **weakest seam**, not its strongest sub-tree.

This standard is a **meta-standard**: it governs the seams and **delegates each language's internals** to `rust-project-standard` (the core), `swift-project-standard`, `python-project-standard`, and their siblings. It does not restate their rules — it composes them and adds the cross-language layer they each lack.

Baseline: a **Rust canonical core** (per `rust-project-standard`), one or more **host sub-trees** each per its own standard, bindings via **UniFFI** (generated, for Swift/Kotlin/Python) and/or **PyO3 / JNI / cbindgen** (hand-written layer), a **pinned generator version**, a top-level **composed gate** (`make check` / `just check`), a **binding-freshness drift guard**, and a `CLAUDE.md` routing table at the root and in every sub-tree.

## When starting a new project

```bash
python scripts/scaffold.py <repo_name> --target <dir> --core rust --hosts swift python kotlin
```

This mirrors `assets/templates/` into a polyglot monorepo: a `core/` Rust workspace (delegating to `rust-project-standard`'s scaffold), an `interface/` single-source contract, a host sub-tree skeleton per `--hosts` (each delegating to that language's scaffold), the generated-bindings boundary with `.gitattributes` + gate excludes, a root `Makefile` composed gate, a `versions.toml` toolchain+generator matrix, a binding-freshness `check_bindings.sh`, a root routing-table `CLAUDE.md`, and `docs/adr/`. When adapting an existing repo, copy from `assets/templates/` by hand — only the repo root, the core crate name, and CLAUDE.md headers carry the literal name; module/import paths within each sub-tree never depend on it.

Then: scaffold each sub-tree with its own language standard, and run `make check` (or `./ci.sh`) — the composed gate — to verify.

## When working on existing code

Apply the rules below, and verify the cross-language structural invariants:

```bash
python scripts/check_conformance.py <repo_root>
```

It discovers the sub-trees, then checks the mechanically enforceable **seam** invariants: a single canonical core is identified; the cross-language contract has one source (no hand-mirrored struct definitions in host trees); generated bindings are marked `linguist-generated` **and** excluded from that host's lint/format config; the binding-generator version is pinned; a composed top-level gate exists and chains every sub-tree's gate plus the freshness guard; a `versions.toml` (or equivalent) pins each toolchain; a root routing-table `CLAUDE.md` exists and each sub-tree has its own. It then **delegates** the per-language structural checks by invoking each sub-tree's own `check_conformance.py`. Everything else is enforced by the composed gate and by applying the standard.

## The non-negotiables

Full rationale, the two-posture binding governance, and worked UniFFI + PyO3 examples in `references/standard.md`.

1. **One canonical core owns shared truth; hosts are thin.** All shared domain logic and the canonical data model live in exactly one implementation — the Rust core (conforming to `rust-project-standard`). No shared business rule is reimplemented in a host language. The smell that a thing belongs in the core: you are about to write the same validation, crypto, parsing, or state machine in Swift *and* Python. Hosts hold only host-specific concerns — UI, platform integration, idiomatic ergonomics over the binding. A security/invariant-bearing core (keys, plaintext, auth) is the **perimeter**: hosts receive opaque handles and typed results, never the raw means to violate the invariant.

2. **The contract is declared once; bindings are derived, never hand-mirrored.** The cross-language interface — the types and functions hosts may call — is declared in exactly one place in the core (UniFFI `#[uniffi::export]`/UDL, or PyO3 `#[pymethods]` + a generated `.pyi`, or a `.proto`). Hosts never hand-copy a struct. Binding emission is a **build step, not a manual port**. This makes model-level drift structurally impossible: a host cannot reference a field the core did not export.

3. **The FFI boundary is the typed, fallible, parse-don't-validate seam — and no panic ever crosses it.** A boundary value is the analog of "parse, don't validate": the core's `Result<T, E>` surfaces as the host's idiomatic error (`throws` in Swift, `raise` in Python, a checked exception in Kotlin), and a host wraps every raw binding call in a thin, hand-written, **governed** adapter that re-types the result into host-native values. A Rust `panic!` must **never unwind across an FFI boundary** — that is undefined behavior or an abort. Every recoverable failure is converted into a typed error *before* the boundary; the `Result → host-error` mapping is explicit and total. (`unwrap`/`expect`/`try!` in code reachable across the boundary is a defect, not a shortcut.)

4. **Two binding postures, two governance rules.**
   - **Generated bindings** (UniFFI, cbindgen, protobuf codegen): the emitted host-language source is a **vendored artifact** — marked `linguist-generated` in `.gitattributes`, **excluded** from that host's lint/format/escape-hatch gate, **never hand-edited** (edits are wiped on regen), and regenerated by a **pinned** generator version. The host language's escape-hatch bans (`try!`/`as!`, force-unwrap, `unwrap`) do **not** apply to generated files — governance moves to the thin hand-written wrapper of rule 3.
   - **Hand-written binding layers** (PyO3, JNI, C-ABI hand-wrappers): the binding code lives in the core's language and **is fully governed by `rust-project-standard`**, plus the FFI rules of rule 3 (no panic across the boundary → convert to `PyErr`/`JThrowable`; normalize at the seam). The **published type stub or header** (`.pyi`, generated `.h`) is the host's view of the contract and is **drift-guarded** (rule 5).

5. **Binding freshness is gated.** A drift guard in the composed gate regenerates every binding and type stub from the current core and runs `git diff --exit-code`. Stale committed artifacts — core changed, host binding didn't — **fail the gate**. This closes the one hole generation cannot close itself: forgetting to regenerate. It is the cross-language analog of the per-language drift checks.

6. **One composed gate over every sub-tree — the repo's only correctness judge.** A single top-level command (`make check` / `just check`), under `set -euo pipefail`, runs the core's gate (`cargo` ci.sh) → each host's gate (swift/python/kotlin ci.sh) → the binding-freshness guard. Completion = the **composed** gate green, never one language's "looks fine". CI mirrors it; a pre-push hook pins it. Because the ceiling is the weakest seam, the gate must cross every seam — a host whose gate isn't wired into `make check` is unguarded.

7. **Pinned, coherent toolchain + generator matrix.** Every language pins its toolchain (`rust-toolchain.toml`, Xcode / `.swift-version`, `.python-version`, Gradle/Kotlin) **and the binding-generator version is pinned** (the `uniffi`/`pyo3` versions in `Cargo.toml`). A `versions.toml` at the root is the single declaration the composed gate and CI both read. Generator-version skew is the subtlest drift source — pin it explicitly.

## Structure: canonical core + thin hosts + a derived-bindings boundary

The depth comes from the **repo topology**, not from any one sub-tree. "Fix the shared rule" resolves to `core/`; "fix how Swift surfaces it" resolves to the apple host's wrapper; the generated binding is **never** where you fix anything — you regenerate it from the core.

- `core/` — the **Rust workspace**, the single source of truth; conforms to `rust-project-standard` in full (workspace, `#![forbid(unsafe_code)]` except the FFI crate's controlled exit, zero-warning gate, `domain` zero-SDK). The cross-language contract is declared here.
- `interface/` (or in-core `*.udl` / `#[uniffi::export]`) — the **one** place the cross-language contract lives.
- generated bindings — either built on demand by the host build, or checked in under a clearly-marked `…/generated/` dir with `.gitattributes linguist-generated` and gate excludes. Never hand-edited.
- one sub-tree per host (`apple/`, `android/`, `python/`, …) — each conforms to its own language standard, **spine only** unless it independently calls a model (see below).
- root — `Makefile`/`justfile` (the composed gate), `versions.toml` (the toolchain+generator matrix), a routing-table `CLAUDE.md`, `docs/adr/`.
- **A `CLAUDE.md` in every sub-tree** (each per-language standard already requires this) **plus a root routing table**: it states the hard cross-language constraints — core is canonical, hosts are thin, bindings are generated, the gate is composed — and points to where each sub-tree lives. The checker requires the root one and one per sub-tree.

## The AI seam in a polyglot repo (AI-triggered layer)

The model-agnostic provider seam (`domain` trait/Protocol + default `MockProvider`) is **located once, in the sub-tree that actually calls the model** — and not duplicated across languages. If the core calls the LLM, the seam is in the core's `domain` crate (per `rust-project-standard`) and hosts consume **typed results across the FFI boundary**, spine-only. If a separate service calls the model (a worker, a backend), that service owns the seam and the core/hosts stay model-free. The polyglot rule: **find the one place a model is called, put the seam there, and let every other sub-tree receive typed values across the seam** — bolting `MockProvider` onto a host that only renders results the core computed is cargo-culting, not conformance.

## Navigability

Naming-as-path, lifted to the repo level: the seam makes location unambiguous. Shared logic is **always** `core/`; host-specific code is **always** in that host. "Where do I fix X?" — if X is a shared rule, the core; if X is how language L surfaces it, host L's hand-written wrapper. If you can't tell, that's the signal X is mis-placed: shared logic leaking into a host, or host concerns leaking into the core.

## Principles for AI-touching code (advisory)

Inherited verbatim from the sibling standards — they apply in whichever sub-tree calls the model.

- **Constrain, don't ask.** Push non-negotiable properties into deterministic control flow so the model *physically cannot* violate them; synthesize answers from typed values, discard model prose on the critical path. Across the FFI boundary, pass the typed values — never re-emit model text on the far side.
- **Narrow the emission surface.** Make the model pick from a typed enum / call tools returning a tri-state; take final values from tool results, not free-form text.
- **Guardrails are deterministic, independent, never pluggable** — and they live in the **core**, re-evaluated from raw input, not trusted from a host.

## Driving AI on big work (advisory)

Same discipline as the siblings, with one polyglot amplifier: **a seam change is a multi-sub-tree change.**

- **Decision-first: a numbered, immutable ADR (`docs/adr/`) before coding** — especially for any change to the cross-language contract, which ripples into every host.
- **TDD red-light first across the seam.** A contract change's spec is a failing test *on each side* — a core test and a host test — both green before the step closes.
- **Numbered steps, each independently green through the composed gate; one commit per step.** A contract change + its regenerated bindings + every host's adaptation is **one** coherent commit, never split across "green" states where bindings are stale.
- **Adversarial independent review**, prioritizing the seam: does every host actually re-type the new contract, or did one silently keep the old shape?

## Scale to project size

The `interface/` split, drift guard, `versions.toml`, and composed CI matrix are real overhead — overkill for a core with a single host you build together. Present them as **triggered, scalable patterns**:

- One core + one host built in the same workflow → a 5-line `make check` chaining two gates and one regen-diff is the whole standard. Skip `bindings/<lang>/` taxonomy for a single host.
- **The moment a second host appears**, the contract must become a single declared source and the freshness guard must enter the gate — that is when hand-mirroring starts to rot silently.
- **The moment the core calls a model**, switch on the AI-triggered layer in the core only.

Scale along **two axes**: number of hosts × whether any sub-tree calls a model. A two-language repo with one generated binding and a composed gate is a perfectly good small-scale instantiation; a Rust core with Swift + Kotlin + Python hosts and a worker that calls an LLM is the full topology. Bolting the full apparatus onto a single-host core is cargo-culting; omitting the freshness guard from a multi-host core is the failure this standard exists to prevent.

## Resources

- `references/standard.md` — the full standard with rationale: the two-posture binding governance in depth, worked **UniFFI** (generated) and **PyO3** (hand-written) examples, the `Result → host-error` mapping per host, the composed `Makefile` gate, the binding-freshness guard, the `versions.toml` matrix, and a fully-worked polyglot repo (Rust core + Swift + Python).
- `assets/templates/` — exact boilerplate: root `Makefile` composed gate, `versions.toml`, `.gitattributes`, root routing-table `CLAUDE.md`, `check_bindings.sh`, per-sub-tree `CLAUDE.md` stubs, `docs/adr/`, and a minimal core+interface+two-host skeleton. `__REPO__` is the only placeholder.
- `scripts/scaffold.py` — generate a conforming polyglot monorepo, composing the sibling scaffolds.
- `scripts/check_conformance.py` — verify the cross-language seam invariants and delegate per-language checks to each sub-tree's own checker.
