---
name: android-project-standard
description: >-
  Enforce a strict, model-agnostic, AI-navigable Kotlin/Android project standard: the Kotlin
  compiler's null-safety + sealed/`when` exhaustiveness as the static guarantee, plus
  `allWarningsAsErrors` + library-module `explicitApi()` + a detekt static-analysis gate as a
  one-command zero-warning gate, the escape hatches (`!!` non-null assertion / unchecked `as` /
  `lateinit` abuse / platform-type leaks / `GlobalScope`) shut via detekt-as-error, kotlinx.serialization
  + `@JvmInline value class` newtypes at boundaries (parse don't validate), a Gradle multi-module
  module-per-domain structure, a zero-SDK zero-framework `:domain` module behind provider interface
  seams with a default `MockProvider`, Hilt composition-root injection in `:app`, a version catalog
  pinning every version, an ktlint + detekt double lint gate, a CLAUDE.md in every module, and
  scaffold/conformance scripts. Use whenever starting or scaffolding a Kotlin or Android project;
  setting up Gradle / settings.gradle.kts / libs.versions.toml / detekt / ktlint / CI; deciding module
  structure; adding an LLM / embedding / vector-store dependency; wiring providers or adapters with
  Hilt; or checking that an existing Android project conforms. Apply it even when the user only says
  "start an Android project", "set up the structure", "add an LLM", or "wire up CI" without naming the
  standard. This skill governs the Kotlin host's internals; it is complementary to
  polyglot-core-standard, which governs the cross-language seam (generated UniFFI/JNI bindings).
---

# Android Project Standard

This skill is the guiding standard for **any** Kotlin/Android work. Apply it by default; don't wait to be asked.

Its spine: **trust is placed not in the model, but in the machine-checkable code that constrains it.** In Kotlin, a large part of that scaffold is the compiler — null-safety, sealed `when` exhaustiveness, and (with `explicitApi()`) an explicit public API surface are enforced at compile time. But Kotlin lacks Rust's `Send`/`Sync` or Swift 6's compile-time data-race safety, so structured concurrency discipline + detekt's coroutine rules backstop it. The job here is to (a) keep the escape hatches shut and turn on `allWarningsAsErrors` + `explicitApi()` + a detekt error-gate, (b) push every external dependency behind an interface so the model is hot-swappable, (c) organize deep with module-per-domain and name-navigable structure, and (d) mechanize the implicit knowledge a human would otherwise hold — via a zero-warning gate, a per-module contract, and the two lint gates. The agent's output ceiling equals the tightness of that loop.

Baseline: **Kotlin 2.x** (`kotlin("jvm")`/`com.android.application`), `allWarningsAsErrors = true` at every module, `explicitApi()` on library modules, **detekt** (`io.gitlab.arturbosch.detekt`, escape-hatch rules as `error`) + **ktlint** (`org.jlleitschuh.gradle.ktlint`, format), kotlinx.serialization + `@JvmInline value class` newtypes, a version catalog (`gradle/libs.versions.toml`) pinning everything, Hilt + Jetpack Compose + Material3 in `:app`, KSP for annotation processing.

This standard is the **project-level engineering charter** (the gate + architecture conventions). It is **complementary to `polyglot-core-standard`**: that meta-standard governs the *cross-language seam* (one canonical Rust core + derived UniFFI/JNI bindings that are vendored, `linguist-generated`, gate-excluded, and never edited; a typed/fallible FFI boundary; a composed gate). This skill governs the *Kotlin host's internals* — lint, format, strict compilation, module structure, the provider seam, and tests. In a polyglot repo the two compose: polyglot defines "how the seam connects", this defines "how Kotlin is written inside", and this skill's `./ci.sh` plugs into polyglot's `make check-android` slot (today the weakest cell of that composed gate — just `gradlew compileDebugKotlin`).

## When starting a new project

```bash
python scripts/scaffold.py com.example.notes --target <dir> --domains retrieval generation
```

This mirrors `assets/templates/` into a Gradle multi-module project (`settings.gradle.kts` + `:kernel`/`:domain`/`:adapters` library modules + a `:app` Android application + a `kotlin("jvm")` module per `--domains` + a CLAUDE.md per module + `ci.sh` + ADR), substitutes `__APP_ID__` in file contents and rewrites the `__PKG_PATH__` source-package directory, and registers each domain module in `settings.gradle.kts` + `:app` dependencies. Module names (`:kernel`, `:domain`, …) are project-independent; only the app id, namespace, and CLAUDE.md headers carry the literal name. When adapting an existing repo, copy from `assets/templates/` by hand.

Then: `gradle wrapper --gradle-version 8.11.1` (once), and `./ci.sh` (or `make check`) to verify. detekt + ktlint are wired via Gradle plugins; no extra install.

## When working on existing code

Apply the rules below, keep new code strict, and verify structural invariants:

```bash
python scripts/check_conformance.py <project_root>
```

It parses `settings.gradle.kts` / `build.gradle.kts` (text/regex — Gradle has no clean manifest-dump) and checks the mechanically enforceable invariants (multi-module present, **`:domain` zero-SDK + zero-framework + no `:adapters` dependency**, `allWarningsAsErrors` wired per module or in root, detekt + ktlint config present, **detekt.yml marks `!!`/`UnsafeCast` as `error`** with a fail threshold, generated bindings gate-excluded, `ci.sh` chaining ktlint → detekt → compile(-Werror) → test, **a CLAUDE.md in every module**). Everything else is enforced by the gate and by applying the standard.

## The non-negotiables

Full rationale in `references/standard.md`.

1. **The compiler is the static guarantee; turn on the strict knobs and keep the escape hatches shut.** Every module sets `allWarningsAsErrors = true`; library modules add `explicitApi()` (public API must be explicit). The escape hatches are *banned* as detekt **errors**: no `!!` (`UnsafeCallOnNullableType`), no unchecked `as` (`UnsafeCast` → use `as?`), no `lateinit` abuse (`LateinitUsage`), no platform-type leaks, no `GlobalScope` (`GlobalCoroutineUsage`). A site that genuinely needs one takes the **controlled exit**: `@Suppress("UnsafeCallOnNullableType") // reason` (explicit, auditable, greppable — the Kotlin analog of a justified `// swiftlint:disable:next … — reason`).

2. **No silent failures: a sealed error hierarchy / `Result<T>`, not swallowed exceptions.** Recoverable failures are a sealed `ProviderError`/`DomainError` (exhaustive `when`) or `Result<T>`; vendor/network/timeout errors normalize at the adapter boundary into a domain error; program bugs trap (`error(...)`/`require(...)`) and propagate — never swallowed (detekt `SwallowedException` = error). The Kotlin mirror of Rust's `Result<T,E>` + `thiserror` and Swift's typed throws.

3. **Boundaries: parse, don't validate — kotlinx.serialization + value-class newtypes.** Everything crossing a boundary (config, LLM output, tool results, files) decodes into a strongly-typed value via kotlinx.serialization; constraints are encoded in `@JvmInline value class` newtypes with a validating factory (`of(...)` that throws), so invalid states are unrepresentable. A custom serializer routes decoding through the factory. The Kotlin mirror of pydantic / `serde` + newtype.

4. **Model-agnostic: every external AI dependency behind an interface in `:domain`; SDKs only in `:adapters`.** The `:domain` module has **zero SDK and zero framework dependencies** (the checker enforces this); it is a pure `kotlin("jvm")` library. Real SDKs live in a separate **gated module** (`:adapters-openai`, conditionally `include`d by a Gradle property — the analog of Cargo features / SPM traits) and normalize to `ProviderError`. The composition root (`:app`'s Hilt `@Module`) is the one place that selects an impl by config and injects it via `@Provides`. A deterministic **MockProvider is the default** (not a test stub) so the app, tests, and CI run offline with no SDK or key.

5. **Completion = one zero-warning gate, the agent's only correctness judge.** `./ci.sh` runs `ktlintCheck` → `detekt` → `compileDebugKotlin` (with `allWarningsAsErrors`) → `test` (offline, Mock default, smoke + conformance), under `set -euo pipefail`. Run it after every change; fix until green; never "looks fine, commit". Pin it with a pre-push hook; CI mirrors it; in a polyglot repo it plugs into `make check-android`.

6. **Two lint gates, both in the gate.** **ktlint** owns formatting (the `swift-format`/`cargo fmt` analog, via `.editorconfig`); **detekt** owns lint and the escape-hatch bans (the `SwiftLint`/`clippy` analog, via `config/detekt/detekt.yml` with `maxIssues: 0`). They are complementary, not redundant — keep both, both in the gate.

## Structure: Gradle multi-module, module-per-domain

The depth comes from the **modules**, not from one module with deep folders. A Gradle module ≈ a Cargo crate / SPM target: module-level dependency isolation. "Fix the reranker" should resolve to `:retrieval/...` with no search.

- **A module per bounded context**, plus the fixed infra modules and a thin app:
  - `:kernel` — cross-cutting infra: `Config.kt` (`@Serializable AppConfig`; defaults < `configs/settings.json` < env `APP_*` with `__` nesting), `Log.kt` (platform-agnostic `Log` + `logProvenance`; payloads never logged), `Prompts.kt` (classpath resources + strict rendering). `kotlin("jvm")`, zero external deps.
  - `:domain` — ports (interfaces) + models (value-class newtypes) + sealed boundary errors; **zero SDK, zero framework**.
  - `:adapters` — interface impls; `MockProvider` is the default; `ProviderFactory` is the assembly seam; real SDKs in a gated sibling module.
  - domain feature modules (`:retrieval`/`:generation`/…) depend on `:domain` + `:kernel`, **never** on `:adapters` or SDKs.
  - `:app` — `com.android.application`; Compose UI + the Hilt composition root that wires concrete adapters by config.
- **Dependency direction** (one-way): feature / `:adapters` → `:domain` + `:kernel`; `:app` → everything. `:domain` is zero-SDK and never depends on `:adapters`.
- **A `CLAUDE.md` in every module**: the root one is a routing table (hard constraints + where to look + the polyglot boundary); each module's states its responsibility, dependency direction, and local contract (`:domain`'s "zero SDK", `:adapters`' "errors normalize", `:kernel`'s "payloads never logged"). The checker requires one per module.
- Go **deep**: split a module into sub-packages by sub-capability; names map to paths.

## Navigability

Naming-as-path is to navigation what types are to interface contracts — and Gradle lifts it to the module level. Group by capability, not by `models/`/`utils/`. Nest until leaf files have a single clear responsibility. A name should resolve to a path with no search.

## Principles for AI-touching code (advisory)

Beyond the type system — for any code where a model produces output. Upper-level discipline; not all mechanically checkable.

- **Constrain, don't ask.** Push non-negotiable properties (no fabrication, must-cite, no privilege escalation) into deterministic control flow so the model *physically cannot* violate them — don't rely on the prompt. Synthesize answers from typed values in code; discard model prose on the critical path.
- **Narrow the emission surface.** Make the model pick from a typed `sealed`/`enum` or call tools returning a tri-state result; take final values from tool results, not free-form model text. A Kotlin `sealed class` + exhaustive `when` is the natural controlled surface.
- **Guardrails are deterministic, independent, never pluggable.** Intent parsing can be swapped; safety decisions are deterministic code re-evaluated from raw input, not trusting a pluggable component's output. (In a polyglot repo these live in the core, not the host.)

## Driving AI on big work (advisory)

Treat AI as supervisable labor, not unsupervised autopilot.

- **Decision-first: a numbered, immutable ADR (`docs/adr/`) before coding** — context + chosen option + rejected alternatives and why. Rejected-reasons stop it re-walking excluded paths.
- **TDD red-light first; tests are the immutable spec.** Write the failing test (JUnit / kotlin.test), then implement to green; never weaken a test to pass.
- **Numbered steps, each independently green; one commit per step through the full gate.** No giant diffs. (In a polyglot repo, a core-contract change + regenerated bindings + the host adaptation is **one** coherent commit.)
- **Adversarial independent review.** After writing, run a separate, hostile, multi-perspective review prioritizing what tests can't cover (diagrams, docs, tradeoffs).

## Scale to project size

The module split, per-module CLAUDE.md, ADRs, and provider seam are real overhead — overkill for a 200-line app. Present them as **triggered, scalable patterns** ("the moment you call an LLM/embedding/vector store, put it behind an interface in `:domain`"; "split a module out the moment it takes a second responsibility"), not blanket mandates. A single-module app + the two lint gates + the zero-warning gate is a perfectly good small-scale instantiation.

Scale along **two axes, not one** — size *and* domain. The standard has a **universal spine** that holds for any Kotlin/Android project whether or not it touches AI: Kotlin compiler strictness + `allWarningsAsErrors` + `explicitApi`, the zero-warning gate, sealed errors / `Result` with the escape hatches shut, kotlinx.serialization + value-class newtypes at boundaries, Gradle module-per-domain + deep naming-as-path, a version catalog, ktlint + detekt. The rest is an **AI-triggered layer** that only switches on once the project actually calls an LLM / embedding / vector store: the `:domain` interface seam + zero-SDK module, `MockProvider`-as-default, bundled prompts + strict rendering, `logProvenance`, and the constrain-don't-ask discipline. A pure app that never calls a model should take the spine in full and skip the AI layer outright — bolting `MockProvider` onto such a project is cargo-culting, not conformance. (In a polyglot repo the AI seam lives in the **one** sub-tree that calls the model — usually the core — and the Kotlin host stays spine-only, receiving typed values across the FFI boundary.)

## Resources

- `references/standard.md` — the full standard with rationale and complete code for every module (read for the why, edge cases, or exact module contents), plus the mapping to the Python/Rust/Swift sibling standards and the polyglot seam boundary.
- `assets/templates/` — exact Gradle boilerplate; `__APP_ID__` (content) + `__PKG_PATH__` (source-package dir) are the only placeholders. Includes `:kernel`/`:domain`/`:adapters`/`:app`, `detekt.yml`, `.editorconfig`, `ci.sh`, `Makefile`, a per-module CLAUDE.md, `gradle/libs.versions.toml`, `configs/settings.json`, and smoke/conformance tests.
- `scripts/scaffold.py` — generate a conforming multi-module project.
- `scripts/check_conformance.py` — verify structural invariants (incl. `:domain`-zero-SDK and per-module CLAUDE.md).
