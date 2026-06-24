---
name: swift-project-standard
description: >-
  Enforce a strict, model-agnostic, AI-navigable Swift project standard: Swift 6
  language mode + complete strict concurrency + warnings-as-errors as a one-command
  zero-warning gate, the escape hatches (`!` force-unwrap / `try!` / `as!` /
  `@unchecked Sendable` / implicitly-unwrapped optionals) shut, `Codable` + newtypes
  at boundaries (parse don't validate), an SPM package with target-per-domain deep
  structure, a zero-SDK `Domain` target behind provider protocol seams with a default
  `MockProvider`, `os.Logger` with privacy interpolation, a strongly-typed `AppConfig`,
  a swift-format + SwiftLint double gate, a CLAUDE.md in every target, and
  scaffold/conformance scripts. Use whenever starting or scaffolding a Swift or SwiftUI
  project; setting up Package.swift / SwiftLint / swift-format / CI; deciding module or
  target structure; adding an LLM / embedding / vector-store dependency; wiring providers
  or adapters; or checking that an existing Swift project conforms. Apply it even when the
  user only says "start a Swift project", "set up the structure", "add an LLM", or "wire
  up CI" without naming the standard.
---

# Swift Project Standard

This skill is the guiding standard for **any** Swift work. Apply it by default; don't wait to be asked.

Its spine: **trust is placed not in the model, but in the machine-checkable code that constrains it.** In Swift, like Rust, most of that scaffold is the compiler — types, optionality, exhaustiveness, and (in Swift 6) data-race safety are enforced at compile time with no type erasure, so there's **no runtime type-checker to bolt on** (unlike the Python sibling's beartype). The job here is to (a) keep the few escape hatches shut and turn on Swift 6 complete strict concurrency, (b) push every external dependency behind a protocol so the model is hot-swappable, (c) organize deep and name-navigable, and (d) mechanize the implicit knowledge a human would otherwise hold — via a zero-warning gate, a per-target contract, and drift guards. The agent's output ceiling equals the tightness of that loop.

Baseline: **Swift 6.x** (`// swift-tools-version: 6.0`, `swiftLanguageModes: [.v6]`), complete strict concurrency, `warnings-as-errors` at the gate, `swift-format` (toolchain-bundled), `SwiftLint` (community, `--strict`), `Codable` + newtypes, `os.Logger`, a Codable `AppConfig`, and `XcodeGen` for a thin app shell when there's a UI.

This standard is the **project-level engineering charter** (the gate + architecture conventions). For *how to write the implementation inside a target*, it delegates to the existing implementation skills — `swift-concurrency`, `swift-error-handling`, `swift-protocols`, `swift-data-flow`, `swift-testing`, `swift-networking`, `swift-persistence`, and the rest — rather than restating them. Cite them where relevant; don't duplicate their content.

## When starting a new project

```bash
python scripts/scaffold.py <package_name> --target <dir> --domains ingestion retrieval generation agents
```

This mirrors `assets/templates/` into an SPM package (`Package.swift` + `Kernel`/`Domain`/`Adapters` targets + an `App` executable + a domain target per `--domains` + a CLAUDE.md per target + `ci.sh` + ADR), substitutes `__PACKAGE__`, and registers each domain target in `Package.swift`'s targets/products. Module names (`import Kernel`, `import Domain`, …) are project-independent — only the package name, the executable name, and CLAUDE.md headers carry the literal name, so `import` paths never depend on it. When adapting an existing repo, copy from `assets/templates/` by hand.

Then: `swift build`, and `./ci.sh` (or `make check`) to verify. `swift format` ships with the toolchain; `swiftlint` needs `brew install swiftlint` once. Pass `--app` to run `xcodegen` and emit a thin `.xcodeproj` app shell that links the `AppCore` library product.

## When working on existing code

Apply the rules below, keep new code strict, and verify structural invariants:

```bash
python scripts/check_conformance.py <project_root>
```

It parses the manifest via `swift package dump-package` (JSON, cleaner than regex) and checks the mechanically enforceable invariants (SPM present, tools ≥ 6 + v6 language mode, target-per-domain, **the `Domain` target has zero vendor-SDK dependencies**, warnings-as-errors wired in `ci.sh` or the manifest, `.swift-format` + `.swiftlint.yml` present, `ci.sh` chaining swift-format/swiftlint/build/test, **a CLAUDE.md in every `Sources/<Target>`**). Everything else is enforced by the gate and by applying the standard.

## The non-negotiables

Full rationale in `references/standard.md`.

1. **The compiler is the static guarantee; turn on Swift 6 and keep the escape hatches shut.** `// swift-tools-version: 6.0` + `swiftLanguageModes: [.v6]` gives complete strict concurrency — compile-time data-race safety, the Swift analog of Rust's `Send`/`Sync`. No bolted-on runtime type check — Swift doesn't need one. The escape hatches are *banned*: no `!` force-unwrap, no `try!`, no `as!`, no implicitly-unwrapped optionals, no `@unchecked Sendable`. SwiftLint enforces `force_unwrapping`/`force_try`/`force_cast`. A site that genuinely needs one takes the **controlled exit**: `// swiftlint:disable:next force_unwrapping — reason` (explicit, auditable, greppable — the Swift analog of a justified `# type: ignore`), and `nonisolated(unsafe)` / `@unchecked Sendable` only with a `// SAFETY:` note and a CLAUDE.md entry.

2. **No silent failures: `throws` + typed `throws(E)` + a concrete `Error`, not `!`/`try!` sprinkled around.** Recoverable failures are `throws`; Swift 6 typed throws (`throws(ProviderError)`) makes the error set part of the signature, the analog of Rust's `Result<T, E>`. Vendor/network/timeout errors normalize at the adapter boundary into `ProviderError`; program bugs (precondition violations) trap or propagate — never swallowed into a fallback. See `swift-error-handling`.

3. **Boundaries: parse, don't validate — `Codable` + newtypes.** Everything crossing a boundary (config, LLM output, tool results, files) decodes into a strongly-typed value via `Codable`; encode constraints in newtypes with a validating init (`init(_:) throws` or failable `init?`) so invalid states are unrepresentable rather than runtime-checked. This is the Swift mirror of Python's pydantic and Rust's `serde` + newtype.

4. **Model-agnostic: every external AI dependency behind a protocol in `Domain`; SDKs only in `Adapters`.** The `Domain` target has **zero SDK dependencies** (the checker parses the resolved manifest to enforce this); protocols stay usable as `any LLM` existentials. Real SDKs live in a separate target gated by an SPM **package trait** (`.product(..., condition: .when(traits: ...))`) — the precise analog of Cargo features — and normalize to `ProviderError`. The composition root (`App`) is the one place that selects an impl by config and injects it (`any LLM`, the analog of `Box<dyn>`). A deterministic **MockProvider is the default** (not a test stub) so the executable, tests, and CI run offline with no SDK or key. See `swift-protocols` for the `any`/`some`/protocol-witness tradeoff.

5. **Completion = one zero-warning gate, the agent's only correctness judge.** `./ci.sh` runs `swift format lint --strict` → `swiftlint --strict` → `swift build -Xswiftc -warnings-as-errors` → `swift test` (offline, Mock default, smoke + conformance), under `set -euo pipefail`; an app scenario appends `xcodebuild ... SWIFT_TREAT_WARNINGS_AS_ERRORS=YES SWIFT_STRICT_CONCURRENCY=complete`. Run it after every change; fix until green; never "looks fine, commit". Pin it with a pre-push hook; CI mirrors it.

6. **Two lint gates, both `--strict`.** `swift-format` owns formatting (the `cargo fmt` analog); `SwiftLint` owns lint and the escape-hatch bans (the `clippy` analog). They are complementary, not redundant — keep both, both strict, both in the gate.

## Structure: SPM package, target-per-domain

The depth comes from the **package** (multiple targets), not from one target with deep folders. An SPM target ≈ a Cargo crate: target-level dependency isolation plus a resolvable `Package.swift`. "Fix the reranker" should resolve to `Sources/Retrieval/...` with no search.

- **A target per bounded context** (`Sources/<Domain>/`), plus the fixed infra targets and a thin executable:
  - `Kernel` — cross-cutting infra: `Config.swift` (Codable `AppConfig: Sendable`; defaults < `configs/settings.json` < env `APP_*` with `__` nesting), `Logging.swift` (`os.Logger`; an `enum Log` factory; `logProvenance(...)`; privacy discipline), `Prompts.swift` (`Bundle.module` resources + strict rendering). Named `Kernel`, not `Core`. Zero external deps.
  - `Domain` — ports (protocols) + models + boundary errors; **zero SDK deps**.
  - `Adapters` — protocol impls; `MockProvider` is the default; real SDKs in a trait-gated sibling target.
  - domain targets (`Retrieval`/`Generation`/…) depend on `Domain` + `Kernel`, never on `Adapters` or SDKs.
  - `App` — the executable and composition root; wires concrete adapters by config. The Xcode app target plays this role in a UI project and links the `AppCore` library product.
- **Dependency direction**: domain target → `Domain` + `Kernel`; `Adapters` → `Domain` + `Kernel`; `App` → everything. `Domain` is zero-SDK.
- **A `CLAUDE.md` in every target** (the layered-context rule applied per directory): the root one is a routing table (hard constraints + where to look); each target's states its responsibility, dependency direction, and local contract (`Domain`'s "zero SDK", `Adapters`' "errors normalize", `Kernel`'s "payloads never logged"). The checker requires one per target.
- Go **deep**: split a target into submodules by sub-capability; names map to paths.

## Navigability

Naming-as-path is to navigation what types are to interface contracts — and SPM lifts it to the target level. Group by capability, not by `Models/`/`Utils/`. Nest until leaf files have a single clear responsibility. A name should resolve to a path with no search.

## Principles for AI-touching code (advisory)

Beyond the type system — for any code where a model produces output. Upper-level discipline; not all mechanically checkable.

- **Constrain, don't ask.** Push non-negotiable properties (no fabrication, must-cite, no privilege escalation) into deterministic control flow so the model *physically cannot* violate them — don't rely on the prompt. Synthesize answers from typed values in code; discard model prose on the critical path.
- **Narrow the emission surface.** Make the model pick from a typed `enum` of options or call tools returning a tri-state result; take final values from tool results, not free-form model text. A Swift `enum` (with associated values, exhaustively matched) is the natural controlled surface.
- **Guardrails are deterministic, independent, never pluggable.** Intent parsing can be swapped; safety decisions are deterministic code re-evaluated from raw input, not trusting a pluggable component's output.

## Driving AI on big work (advisory)

Treat AI as supervisable labor, not unsupervised autopilot.

- **Decision-first: a numbered, immutable ADR (`docs/adr/`) before coding** — context + chosen option + rejected alternatives and why. Rejected-reasons stop it re-walking excluded paths.
- **TDD red-light first; tests are the immutable spec.** Write the failing test (Swift Testing `@Test` or XCTest), then implement to green; never weaken a test to pass. See `swift-testing`.
- **Numbered steps, each independently green; one commit per step through the full gate.** No giant diffs.
- **Adversarial independent review.** After writing, run a separate, hostile, multi-perspective review prioritizing what tests can't cover (diagrams, docs, tradeoffs).

## Scale to project size

The target split, per-target CLAUDE.md, ADRs, and provider seam are real overhead — overkill for a 200-line CLI. Present them as **triggered, scalable patterns** ("the moment you call an LLM/embedding/vector store, put it behind a protocol in `Domain`"; "split a target out the moment it takes a second responsibility"), not blanket mandates. A single-target package with files + the two lint gates + the zero-warning gate is a perfectly good small-scale instantiation.

Scale along **two axes, not one** — size *and* domain. The standard has a **universal spine** that holds for any Swift project whether or not it touches AI: Swift 6 + complete strict concurrency + warnings-as-errors, the zero-warning gate, `throws`/typed throws with the escape hatches shut (`!`/`try!`/`as!`), `Codable` + newtypes at boundaries, SPM target-per-domain + deep naming-as-path, `os.Logger`, a strongly-typed `AppConfig`, swift-format + SwiftLint. The rest is an **AI-triggered layer** that only switches on once the project actually calls an LLM / embedding / vector store: the `Domain` protocol seam + zero-SDK domain target, `MockProvider`-as-default, bundled prompts + strict rendering, `logProvenance`, and the constrain-don't-ask discipline. A pure library / CLI / app that never calls a model should take the spine in full and skip the AI layer outright — bolting `MockProvider` or prompt-embedding onto such a project is cargo-culting, not conformance.

## Resources

- `references/standard.md` — the full standard with rationale and complete code for every target (read for the why, edge cases, or exact module contents).
- `assets/templates/` — exact SPM boilerplate; `__PACKAGE__` is the only placeholder. Includes `Kernel`/`Domain`/`Adapters`/`App`, `.swift-format`, `.swiftlint.yml`, `ci.sh`, `project.yml` (XcodeGen), a per-target CLAUDE.md, `configs/settings.json`, and smoke/conformance tests.
- `scripts/scaffold.py` — generate a conforming package.
- `scripts/check_conformance.py` — verify structural invariants (incl. `Domain`-zero-SDK and per-target CLAUDE.md).
