---
name: java-project-standard
description: >-
  Enforce a strict, model-agnostic, AI-navigable Java project standard: the Java compiler plus
  `-Werror` + `-Xlint:all` as the baseline, **Error Prone** (bug-pattern checks as errors, the
  clippy/detekt analog) and **NullAway** (JSpecify `@Nullable`, null-safety at compile time — the
  Kotlin null-safety / Swift optional analog) as the static guarantee, **Spotless** with
  google-java-format as the format gate, sealed error hierarchies + exhaustive `switch` (no silent
  failures), **TDD with a JaCoCo coverage floor in the gate**, Jackson at boundaries with lightweight
  record compact-constructor validation, a Gradle multi-module module-per-domain structure, a
  zero-SDK zero-framework `:domain` module behind provider interface seams with a default
  `MockProvider`, a manual composition root (no DI framework), a version catalog pinning every
  version, a CLAUDE.md in every module, and scaffold/conformance scripts. Use whenever starting or
  scaffolding a Java project; setting up Gradle / settings.gradle.kts / libs.versions.toml / Error
  Prone / NullAway / Spotless / JaCoCo / CI; deciding module structure; adding an LLM / embedding /
  vector-store dependency; wiring providers or adapters; or checking that an existing Java project
  conforms. Apply it even when the user only says "start a Java project", "set up the structure",
  "add an LLM", or "wire up CI" without naming the standard. This skill governs the Java host's
  internals; it is complementary to polyglot-core-standard, which governs the cross-language seam
  (a Rust core + a JNI/JNA/Panama-FFM bridge — Java has no official UniFFI support).
---

# Java Project Standard

This skill is the guiding standard for **any** plain-JVM Java work. Apply it by default; don't wait to be asked.

Its spine: **trust is placed not in the model, but in the machine-checkable code that constrains it.** In Java a large part of that scaffold is the compiler — a static, non-erased-at-the-API type system, sealed types with exhaustive `switch`, and records. But `javac` alone is lax (unchecked casts warn but pass; `null` is unchecked; many bug patterns slip through), so the standard turns the knobs to the maximum and adds two tools the compiler lacks: **Error Prone** (bug-pattern checks, promoted to errors — the clippy/detekt analog) and **NullAway** (compile-time null-safety over JSpecify `@Nullable` — the Kotlin null-safety / Swift optional analog). The job here is to (a) keep the escape hatches shut and turn on `-Werror` + `-Xlint:all` + Error Prone + NullAway, (b) push every external dependency behind an interface so the model is hot-swappable, (c) organize deep with module-per-domain and name-navigable structure, and (d) mechanize the implicit knowledge a human would otherwise hold — via a zero-warning gate with a coverage floor, a per-module contract, and the format + lint gates. The agent's output ceiling equals the tightness of that loop.

Baseline: **Java 21+** (LTS; targeted via `options.release = 21`, so the build is independent of the host JDK version — any JDK 21..25+ on `JAVA_HOME`), Gradle **9.x** (Kotlin DSL) multi-module + a version catalog (`gradle/libs.versions.toml`) pinning everything, `-Werror` + `-Xlint:all,-processing,-serial`, **Error Prone** + **NullAway** (JSpecify), **Spotless** (google-java-format), Jackson at boundaries, SLF4J for logging, JUnit 5 (Jupiter) tests with a **JaCoCo** coverage floor.

This standard is the **project-level engineering charter** (the gate + architecture conventions). It is **complementary to `polyglot-core-standard`**: that meta-standard governs the *cross-language seam* (one canonical Rust core + a typed/fallible FFI boundary + a composed gate). This skill governs the *Java host's internals* — format, lint, strict compilation, module structure, the provider seam, and tests. In a polyglot repo the two compose, and this skill's `./ci.sh` plugs into polyglot's `make check-java` slot.

## When starting a new project

```bash
python scripts/scaffold.py com.example.notes --target <dir> --domains retrieval generation
```

This mirrors `assets/templates/` into a Gradle multi-module project (`settings.gradle.kts` + `:kernel`/`:domain`/`:adapters` library modules + a `:app` application + a `java-library` module per `--domains` + a CLAUDE.md per module + `ci.sh` + ADR), substitutes `__PKG__` in file contents and rewrites the `__PKG_PATH__` source-package directory, and registers each domain module in `settings.gradle.kts` + `:app` dependencies. Module names (`:kernel`, `:domain`, …) are project-independent; only the base package, `rootProject.name`, and CLAUDE.md headers carry the literal name. When adapting an existing repo, copy from `assets/templates/` by hand.

Then: `gradle wrapper --gradle-version 9.4.1` (once, if not auto-generated), and `./ci.sh` (or `make check`) to verify. Error Prone + NullAway + Spotless are wired via Gradle plugins; no extra install.

## When working on existing code

Apply the rules below, keep new code strict, and verify structural invariants:

```bash
python scripts/check_conformance.py <project_root>
```

It parses `settings.gradle.kts` / `build.gradle.kts` (text/regex — Gradle has no clean manifest-dump) and checks the mechanically enforceable invariants (multi-module present, **`:domain` zero-SDK + zero-framework + no `:adapters` dependency**, `-Werror` wired, Error Prone + NullAway wired with NullAway at `error()`, Spotless configured, **JaCoCo `jacocoTestCoverageVerification` wired on every non-app module**, `ci.sh` chaining spotlessCheck → compileJava → test → coverage, **a CLAUDE.md in every module**, **a `src/test` in every non-app module**). Everything else is enforced by the gate and by applying the standard.

## The non-negotiables

Full rationale in `references/standard.md`.

1. **The compiler + strict knobs are the static guarantee; keep the escape hatches shut.** Every module compiles with `options.release = 21`, `-Werror`, and `-Xlint:all,-processing,-serial`, so a warning is fatal (unchecked casts, raw types, deprecation, fall-through all trap here). On top, **Error Prone** runs its bug-pattern checks (default-error checks stay errors) and **NullAway** makes null-safety a compile error: annotate the base package tree so it is `@NonNull` by default (JSpecify), and `@Nullable` is the explicit, checked opt-out — `null` stops being a runtime bomb. A site that genuinely needs an exit takes the **controlled exit**: `@SuppressWarnings("NullAway") // reason` (explicit, auditable, greppable — the Java analog of a justified `# type: ignore[code] # reason` / `#[allow(clippy::…)] // reason`).

2. **No silent failures: sealed error hierarchies + exhaustive `switch`, not swallowed exceptions.** Recoverable failures are a sealed `ProviderException` (make the sealed base `abstract` so `switch` over it is compiler-checked exhaustive with no `default`); vendor/network/timeout errors normalize at the adapter boundary into it; program bugs throw (`IllegalArgumentException`/`IllegalStateException`) and propagate — never an empty `catch`. The Java mirror of Rust's `Result<T,E>` + `thiserror` and Swift's typed `throws`.

3. **TDD, red-light first; tests are the immutable spec, and coverage is in the gate.** Write the failing JUnit 5 test, then implement to green; never weaken a test to pass. This is spine-level here, not advisory: the gate ends with **JaCoCo `jacocoTestCoverageVerification`** enforcing **≥ 80% line coverage on every non-app module** (`:kernel`/`:domain`/`:adapters`/feature). `:app` is exempt — its `Main`/wiring is a composition root exercised by running the app, so keep real logic out of `:app`. A scaffolded project ships tests that already clear the floor.

4. **Boundaries: parse at the edge — Jackson into records; keep it lightweight.** Values crossing a process boundary (config, LLM output, tool results, files) decode into records via Jackson (compile with `-parameters` so it binds by component name). Where a constraint genuinely earns it, encode it in the record's **compact constructor** (e.g. `TopK` rejecting out-of-range) so invalid states fail at construction. Do **not** wrap every value in a newtype — Java's static type system already carries most of that load; reserve compact-constructor validation for real boundaries, not internal plumbing. (This is the deliberately lighter cousin of Rust's `serde` + newtype and pydantic.)

5. **Model-agnostic: every external AI dependency behind an interface in `:domain`; SDKs only in `:adapters`.** The `:domain` module has **zero SDK and zero framework dependencies** (the checker enforces this); it is a plain `java-library`. Real SDKs live in a separate **gated module** (`:adapters-openai`, conditionally `include`d by a Gradle property — the analog of Cargo features / SPM traits) and normalize to `ProviderException`. The composition root (`:app`'s `Wiring`, a **manual, framework-free** function) is the one place that selects an impl by config. A deterministic **MockProvider is the default** (not a test stub) so the app, tests, and CI run offline with no SDK or key. A `ProviderConformanceTest` binds mock and real backends to the same behavioral invariants.

6. **Completion = one zero-warning gate, the agent's only correctness judge.** `./ci.sh` runs `spotlessCheck` (google-java-format) → `compileJava` (with `-Werror` + Error Prone + NullAway) → `test` (offline, Mock default, JUnit 5 smoke + conformance) → `jacocoTestCoverageVerification`, under `set -euo pipefail`. Run it after every change; fix until green; never "looks fine, commit". Pin it with a pre-push hook; CI mirrors it; in a polyglot repo it plugs into `make check-java`. **Spotless** owns formatting (the ktlint / `cargo fmt` analog); **Error Prone + NullAway** own lint and the escape-hatch bans (the detekt / clippy analog) — complementary, both in the gate.

## Structure: Gradle multi-module, module-per-domain

The depth comes from the **modules**, not from one module with deep packages. A Gradle module ≈ a Cargo crate / SPM target: module-level dependency isolation. "Fix the reranker" should resolve to `:retrieval/...` with no search.

- **A module per bounded context**, plus the fixed infra modules and a thin app:
  - `:kernel` — cross-cutting infra: `AppConfig` (record; defaults < `configs/settings.json` < env `APP_*` with `__` nesting, decoded by Jackson), `Log` (SLF4J facade; payloads never logged; `logProvenance` only takes codes/counts/versions), `Prompts` (classpath resources + strict rendering — a missing variable throws). Plain `java-library`, zero SDK.
  - `:domain` — ports (interfaces) + models (records) + sealed boundary errors; **zero SDK, zero framework**.
  - `:adapters` — interface impls; `MockProvider` is the default; `ProviderFactory` is the assembly seam; real SDKs in a gated sibling module.
  - domain feature modules (`:retrieval`/`:generation`/…) depend on `:domain` + `:kernel`, **never** on `:adapters` or SDKs.
  - `:app` — the `application` plugin; a **manual composition root** (`Wiring` + `Main`) that selects concrete adapters by config. No DI framework — introduce one here and nowhere else if wiring outgrows a hand-written function.
- **Dependency direction** (one-way): feature / `:adapters` → `:domain` + `:kernel`; `:app` → everything. `:domain` is zero-SDK and never depends on `:adapters`.
- **A `CLAUDE.md` in every module**: the root one is a routing table (hard constraints + where to look + the polyglot boundary); each module's states its responsibility, dependency direction, and local contract (`:domain`'s "zero SDK", `:adapters`' "errors normalize", `:kernel`'s "payloads never logged"). The checker requires one per module.
- Go **deep**: split a module into sub-packages by sub-capability; names map to paths.

## Navigability

Naming-as-path is to navigation what types are to interface contracts — and Gradle lifts it to the module level. Group by capability, not by `models/`/`util/`. Nest until leaf files have a single clear responsibility. A name should resolve to a path with no search.

## Principles for AI-touching code (advisory)

Beyond the type system — for any code where a model produces output. Upper-level discipline; not all mechanically checkable.

- **Constrain, don't ask.** Push non-negotiable properties (no fabrication, must-cite, no privilege escalation) into deterministic control flow so the model *physically cannot* violate them — don't rely on the prompt. Synthesize answers from typed values in code; discard model prose on the critical path.
- **Narrow the emission surface.** Make the model pick from a typed `enum` / sealed interface or call tools returning a tri-state result; take final values from tool results, not free-form model text. A Java `sealed interface` + exhaustive `switch` is the natural controlled surface.
- **Guardrails are deterministic, independent, never pluggable.** Intent parsing can be swapped; safety decisions are deterministic code re-evaluated from raw input, not trusting a pluggable component's output. (In a polyglot repo these live in the core, not the host.)

## Driving AI on big work (advisory)

Treat AI as supervisable labor, not unsupervised autopilot.

- **Decision-first: a numbered, immutable ADR (`docs/adr/`) before coding** — context + chosen option + rejected alternatives and why. Rejected-reasons stop it re-walking excluded paths.
- **TDD is spine-level here (non-negotiable #3).** Beyond that: attach the failing test as a subagent's acceptance criteria.
- **Numbered steps, each independently green; one commit per step through the full gate.** No giant diffs. (In a polyglot repo, a core-contract change + regenerated bindings + the host adaptation is **one** coherent commit.)
- **Adversarial independent review.** After writing, run a separate, hostile, multi-perspective review prioritizing what tests can't cover (diagrams, docs, tradeoffs).

## Scale to project size

The module split, per-module CLAUDE.md, ADRs, and provider seam are real overhead — overkill for a 200-line tool. Present them as **triggered, scalable patterns** ("the moment you call an LLM/embedding/vector store, put it behind an interface in `:domain`"; "split a module out the moment it takes a second responsibility"), not blanket mandates. A single-module app + Spotless + Error Prone + NullAway + the zero-warning gate with a coverage floor is a perfectly good small-scale instantiation.

Scale along **two axes, not one** — size *and* domain. The standard has a **universal spine** that holds for any Java project whether or not it touches AI: `-Werror` + `-Xlint:all` + Error Prone + NullAway, the zero-warning gate, TDD + a coverage floor, sealed errors with the escape hatches shut, Jackson + lightweight record validation at boundaries, Gradle module-per-domain + deep naming-as-path, a version catalog, Spotless. The rest is an **AI-triggered layer** that only switches on once the project actually calls an LLM / embedding / vector store: the `:domain` interface seam + zero-SDK module, `MockProvider`-as-default, bundled prompts + strict rendering, `logProvenance`, and the constrain-don't-ask discipline. A pure app that never calls a model should take the spine in full and skip the AI layer outright — bolting `MockProvider` onto such a project is cargo-culting, not conformance. (In a polyglot repo the AI seam lives in the **one** sub-tree that calls the model — usually the core — and the Java host stays spine-only, receiving typed values across the FFI boundary.)

## Resources

- `references/standard.md` — the full standard with rationale and complete code for every module (read for the why, edge cases, or exact module contents), plus the mapping to the Python/Rust/Swift/Kotlin sibling standards and the polyglot seam boundary.
- `assets/templates/` — exact Gradle boilerplate; `__PKG__` (content) + `__PKG_PATH__` (source-package dir) are the only placeholders. Includes `:kernel`/`:domain`/`:adapters`/`:app`, the version catalog, `.editorconfig`, `ci.sh`, `Makefile`, a per-module CLAUDE.md, `configs/settings.json`, and smoke/conformance tests.
- `scripts/scaffold.py` — generate a conforming multi-module project.
- `scripts/check_conformance.py` — verify structural invariants (incl. `:domain`-zero-SDK, per-module CLAUDE.md, and the coverage-floor wiring).
