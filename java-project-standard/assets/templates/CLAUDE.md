# __PKG__ — AI development constraints (always on, root routing table)

> Hard constraints + where to look only. **Every module has its own `CLAUDE.md`** (local contract);
> domain detail does not pile up here.

## Non-negotiable (violating these breaks the design)
- Static guarantee: the Java compiler + `-Werror` + `-Xlint:all` + **Error Prone** + **NullAway**
  (JSpecify `@Nullable`). Null is a compile error, not a runtime bomb. Every module targets Java 21
  via `options.release`.
- Escape hatches stay shut: no unchecked cast, no swallowed exception, no `System.out` (use `Log`),
  no bare `@SuppressWarnings`. Escaping a site is a controlled exit: `@SuppressWarnings("NullAway")
  // reason` (explicit, auditable, greppable).
- No silent failure: sealed error hierarchies (`ProviderException`) with exhaustive `switch`;
  vendor/network/timeout normalize at the adapter boundary; program bugs throw and propagate.
- **TDD, red-light first**: write the failing JUnit 5 test, then implement to green. Tests are the
  immutable spec; never weaken a test to pass. **Coverage is in the gate** (JaCoCo, >= 80% line on
  every non-app module).
- Boundaries: decode external input (config, LLM output, files) with Jackson into records; encode a
  constraint in a record's compact constructor where it earns its keep (lightweight -- Java's type
  system already carries most of the load; do not wrap every value in a newtype).
- External AI dependencies go behind a `:domain` interface; vendor SDKs live only in `:adapters`
  (real backends in a gated module). **`:domain` has zero SDK / zero framework deps.**
- Completion = one gate green: `./ci.sh` (spotlessCheck -> compileJava(-Werror+ErrorProne+NullAway)
  -> test -> jacocoTestCoverageVerification). The only judge; never "looks fine, commit".
- Structure module-per-domain; names resolve to paths. One-way deps: feature / `:adapters` ->
  `:domain` + `:kernel`; `:app` -> everything. `:domain` never depends on `:adapters` / an SDK.

## Boundary with polyglot-core-standard (if this repo is polyglot)
- This standard governs the **Java host's internals** (format / lint / strict compile / module
  structure / provider seam / tests / coverage).
- The **seam** (one canonical Rust core + derived bindings, vendored / tracked / `linguist-generated`
  / gate-excluded / never-edited; a typed & fallible FFI boundary; a composed gate) is
  polyglot-core-standard's job.
- Generated bindings (`**/generated/**`) are excluded from Spotless + Error Prone; the hand-written
  FFI bridge is governed seam code. Java hosts a Rust core via JNI / JNA / Panama (FFM) -- UniFFI has
  no official Java support.
- This module's gate plugs into polyglot's `make check-java` slot.

## Flow
- Direction first: write `docs/adr/` (numbered, immutable: context + choice + rejected + why).
- TDD: failing test first (JUnit 5), then green; never weaken a test.
- Big changes as numbered steps, each through `./ci.sh` before the next; no giant diffs.
- After writing, run a separate, hostile review (assume it's wrong; falsify it).

## Where to look
- Full standard + rationale: the skill's `references/standard.md`.
- Per-module contracts: `<module>/CLAUDE.md`.
- Toolchain / versions: `gradle/libs.versions.toml` (polyglot repos also align the root `versions.toml`).
