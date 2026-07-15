# Java Project Standard (full)

An engineering standard for AI-led development in Java. Same spine as the Python / Rust / Swift / Kotlin siblings: **trust is placed in machine-checkable code, not in the model.** Java is closest to Kotlin and Swift — a static, non-erased-at-the-API type system gives you a lot for free (sealed types with exhaustive `switch`, records, generics). But plain `javac` is lax where it matters: unchecked casts only *warn*, `null` is unchecked, and many real bug patterns compile clean. So this standard turns every knob to the maximum and adds the two tools the compiler lacks — **Error Prone** (bug-pattern lint, promoted to errors) and **NullAway** (compile-time null-safety over JSpecify `@Nullable`) — then shuts the escape hatches, pushes every external dependency behind an interface, keeps the structure deep and name-navigable, and externalizes the human's implicit "is it done?" judgment into a gate that can fail.

> **Positioning**: this is the **project-level engineering charter** (the gate + architecture conventions), governing **how the Java host is written** — format, lint, strict compilation, module structure, the provider seam, tests, coverage. It is **complementary to `polyglot-core-standard`**, which governs the **cross-language seam** (a canonical Rust core + derived bindings that are vendored, `linguist-generated`, gate-excluded, never-edited; a typed/fallible FFI boundary; a composed gate). In a polyglot repo the two compose: polyglot defines "how the seam connects", this defines "how Java is written inside", and this skill's `./ci.sh` plugs into polyglot's `make check-java` slot.

**Scope (two layers)**: the constraints below split into a **universal spine** and an **AI-triggered layer**.

- **Universal spine** (any Java project, AI or not): compiler + `-Werror` + `-Xlint:all` + Error Prone + NullAway, the zero-warning gate, TDD + a JaCoCo coverage floor, sealed errors with the escape hatches shut, Jackson + lightweight record validation at boundaries, Gradle module-per-domain + deep naming, a version catalog, `Log` + typed `AppConfig`, Spotless format gate.
- **AI-triggered layer** (only when the project actually calls an LLM / embedding / vector store): the `:domain` interface seam + zero-SDK module, `MockProvider`-as-default, classpath prompts + strict rendering, `logProvenance`, constrain-don't-ask.

A pure app/library that never calls a model should take the spine in full and skip the AI layer outright; bolting `MockProvider` or prompt-embedding onto such a project is cargo-culting, not conformance.

Baseline: **Java 21+** targeted via `options.release = 21` (host-JDK-independent; runs on any JDK 21..25+ on `JAVA_HOME`), Gradle **9.x** (Kotlin DSL), a version catalog (`gradle/libs.versions.toml`) pinning everything; per-module `-Werror` + `-Xlint:all,-processing,-serial` + `-parameters`; **Error Prone** + **NullAway** (JSpecify); **Spotless** (google-java-format); Jackson at boundaries; SLF4J; JUnit 5 + **JaCoCo**.

---

## 1. The one zero-warning gate (the only completion judge)

`ci.sh` is a single `set -euo pipefail` script, shared by humans and agents, ordered fast → slow:

```bash
#!/usr/bin/env bash
set -euo pipefail
GRADLE="./gradlew --no-daemon --stacktrace"

$GRADLE spotlessCheck                     # 1. format (google-java-format)
$GRADLE compileJava                       # 2. compile (-Werror + Error Prone + NullAway = fatal)
$GRADLE test                              # 3. tests (offline, mock default, JUnit 5)
$GRADLE jacocoTestCoverageVerification    # 4. coverage floor (>= 80% line, non-app modules)

echo "OK: all green"
```

Any non-zero step means "not done". Four gates, each with a job: **Spotless** owns formatting (the ktlint / `cargo fmt` analog), **`compileJava`** under `-Werror` + Error Prone + NullAway is `-Werror` + the detekt/clippy analog + null-safety, **`test`** runs the offline smoke + conformance suite, **`jacocoTestCoverageVerification`** enforces the coverage floor. Pin it with a pre-push hook; CI mirrors it; in a polyglot repo it plugs into `make check-java`. `make check` == `./ci.sh`; `make fmt` (`spotlessApply`) / `make lint` / `make build` / `make test` / `make coverage` are single-gate shortcuts.

## 2. Static guarantee: compiler + strict knobs, escape hatches shut

No mypy/beartype to bolt on — Java's types are enforced at compile time. "Strictest" is expressed natively and then hardened. **Per-module** (a greppable, per-module contract — the same design decision as the Kotlin sibling: typed accessors like `libs.*` and the Error Prone DSL are unreliable in a root `subprojects {}`, so each module applies and configures the plugins itself):

```kotlin
tasks.withType<JavaCompile>().configureEach {
    options.release.set(21)                                                    // target 21, any host JDK
    options.compilerArgs.addAll(listOf("-Werror", "-Xlint:all,-processing,-serial", "-parameters"))
    options.errorprone {
        disableWarningsInGeneratedCode.set(true)
        excludedPaths.set(".*/generated/.*")
        nullaway { error() }                                                   // null-safety violation = build error
    }
}
```

What each knob buys:

- **`-Werror` + `-Xlint:all`** turns javac's own warnings fatal — this is where the **unchecked-cast escape hatch dies** (`-Xlint:unchecked`), along with raw types, deprecation, and fall-through. `-processing` and `-serial` are excluded with reason: annotation processors (Error Prone, NullAway) emit benign `processing` notes, and sealed exception hierarchies would otherwise demand a `serialVersionUID` on every subtype (`serial`) for no safety gain.
- **`-parameters`** keeps parameter names in the class file so Jackson binds JSON to record components by name (no `@JsonProperty` noise).
- **Error Prone** runs Google's bug-pattern checks; its default-error checks stay errors (self-comparison, dead code, format-string mismatches, `CheckReturnValue`, and dozens more), so a whole class of "compiles but wrong" is caught.
- **NullAway** makes null a compile error. Annotate the base package tree as annotated (JSpecify semantics: `@NonNull` by default) in each module — `nullaway { annotatedPackages.add("<base pkg>") }` — so `@Nullable` is the explicit, checked opt-out. Dereferencing a `@Nullable` without a guard fails the build. This is the Java standard's headline: `null` moves from a runtime bomb to a compile-time error, the way Kotlin's null-safety and Swift's optionals do.

**Escape hatches, shut.** The literal implementation of "no escape hatches":

- **Unchecked cast** — banned via `-Xlint:unchecked` + `-Werror`. Use a checked pattern (`instanceof` pattern, sealed `switch`) instead.
- **Null** — banned via NullAway. Use `@Nullable` + an explicit guard, or `Objects.requireNonNull(x, "reason")`.
- **Swallowed exception** (empty `catch`) — a program bug hidden. Don't; let it propagate, or normalize it at the adapter boundary (§3).
- **`System.out` / `System.err` on the hot path** — use `Log` (§7). The entry point routes through `Log` too.
- **Bare `@SuppressWarnings`** — never blanket-suppress. A site that truly needs an exit (a framework contract, an invariant already checked) takes the **controlled exit**: a per-site suppression *with a reason*:

```java
@SuppressWarnings("NullAway") // value is non-null by construction; a null here is a compile-time bug
String value = requireNonNull(parsed);
```

This is the Java equivalent of `# type: ignore[code] # reason` / `#[allow(clippy::…)] // reason` / `// swiftlint:disable:next … — reason`: not a ban, but making every exit **explicit, auditable, and greppable**.

**Why google-java-format, not palantir-java-format** — the Spotless formatter runs on the Gradle daemon's JVM, which (to target `--release 21` without a separately-provisioned JDK) must be a JDK 21..25. As of its latest 2.x releases palantir-java-format does not run on JDK 25 (it calls a `com.sun.tools.javac` internal whose signature changed). google-java-format's recent releases explicitly track new JDKs, so it is the only one of the two that runs the gate on a modern JDK. It is also zero-config and canonical (2-space, 100-col Google style). Pin its version in the catalog.

**Why Error Prone is pinned to a specific version** — NullAway loads an Error Prone internal (`predicates.type.DescendantOf`) that later Error Prone releases removed; the catalog pins `error_prone_core` to the last release that both ships that class *and* runs on JDK 21..25+. Bump Error Prone and NullAway together, and re-run the gate.

## 3. No silent failure: sealed error hierarchies + exhaustive `switch`

Against Rust's `Result<T,E>` + `thiserror` and Swift's typed `throws`, Java uses a **sealed exception hierarchy**: exceptions are Java's idiomatic error channel, and sealing gives the exhaustiveness the others get from their return types.

```java
public abstract sealed class ProviderException extends Exception
    permits ProviderException.MissingCredentials,
        ProviderException.Transport,
        ProviderException.InvalidResponse {

  private ProviderException(String message) { super(message); }

  public static final class MissingCredentials extends ProviderException { /* … */ }
  public static final class Transport extends ProviderException { /* … */ }
  public static final class InvalidResponse extends ProviderException { /* … */ }

  public String kind() {
    return switch (this) {                         // no default: adding a subtype breaks compilation here
      case MissingCredentials ignored -> "missing_credentials";
      case Transport ignored -> "transport";
      case InvalidResponse ignored -> "invalid_response";
    };
  }
}
```

Discipline:

- **The sealed base is `abstract`.** A concrete base would itself be a possible value, so the `switch` would demand a `default` and lose exhaustiveness. `abstract` makes the three subtypes the *only* possibilities — the compiler then checks the `switch` is exhaustive with no `default`.
- **`ProviderException` is checked (`extends Exception`).** Ports declare `throws ProviderException`, so callers must handle or propagate — the strongest "it can't be silently ignored". It is the Java mirror of Rust's `Result` and Swift's typed `throws`.
- **Vendor errors normalize at the adapter boundary** to `Transport` / `InvalidResponse` / `MissingCredentials`: each SDK's zoo of network/timeout/credential/decoding exceptions is mapped there and nowhere else.
- **Program bugs throw unchecked and propagate** (`IllegalArgumentException` for a bad config value, `IllegalStateException` for a broken invariant) — never funneled into a fallback and swallowed. This matches the siblings: external errors normalize, program bugs trap.
- Test-assertion failures are reported by JUnit — not a "silent failure".

## 4. TDD and the coverage floor (spine-level)

In the siblings TDD is a workflow suggestion; here it is a **non-negotiable**, because an AI that optimizes only for observable feedback needs the test to *be* the feedback.

- **Red-light first.** Write the failing JUnit 5 test, then implement to green. Never weaken a test to make it pass. Attach the failing test as a subagent's acceptance criteria.
- **Coverage is in the gate.** The gate ends with `jacocoTestCoverageVerification`, enforcing **≥ 80% line coverage on every non-app module**. Per module:

```kotlin
tasks.named<Test>("test") {
    useJUnitPlatform()
    finalizedBy(tasks.named("jacocoTestReport"))
}
tasks.named<JacocoCoverageVerification>("jacocoTestCoverageVerification") {
    dependsOn(tasks.named("test"))
    violationRules { rule { limit { counter = "LINE"; minimum = "0.80".toBigDecimal() } } }
}
tasks.named("check") { dependsOn(tasks.named("jacocoTestCoverageVerification")) }
```

- **`:app` is exempt.** `Main.main()` and `Wiring` are the composition root — exercised by running the app, not unit tests — so no floor is enforced there (`Wiring` still has a unit test). The exemption is *why* real logic must stay out of `:app`: if you put logic there, you put it beyond the coverage gate.
- The scaffolded skeleton ships tests that already clear the floor (domain model + error exhaustiveness, kernel config precedence + strict prompt rendering, adapter `MockProvider` conformance + smoke, each feature module's port delegation), so a fresh project is green from the first `./ci.sh`.

## 5. Boundaries: parse at the edge — Jackson + records (lightweight)

Every value crossing a process boundary (config, LLM output, tool results, files) decodes into a **record** via Jackson at the entry point. Compile with `-parameters` so Jackson binds JSON keys to record components without `@JsonProperty`. Where a constraint genuinely earns its keep, encode it in the record's **compact constructor** so an invalid value fails at construction:

```java
public record TopK(int value) {
  public TopK {
    if (value < 1 || value > 100) throw new IllegalArgumentException("topK out of range 1..100: " + value);
  }
}
```

**Deliberately lighter than the Python/Rust siblings.** Do **not** wrap every value in a newtype — Java's static type system already carries most of that load, and newtype-everywhere is ceremony that fights readability here. Reserve compact-constructor validation for real boundaries (a parsed config field, a decoded tool argument), not internal plumbing. Records give you immutability, `equals`/`hashCode`/`toString`, and structural clarity for free; that is usually enough. This is the Java tuning of "parse, don't validate": parse at the edge into a record, lean on the type system inside.

## 6. Config: layered, typed `AppConfig`

`:kernel`'s `AppConfig` is a record + a layered loader. Precedence low → high: **defaults < `configs/settings.json` < environment variables (`APP_` prefix, `__` for nesting)**. Records have no field defaults, so the canonical constructor normalizes absent values; a missing file yields defaults, but a present-but-invalid file fails loudly (never swallowed):

```java
public record AppConfig(String llmProvider, RetrieverConfig retriever) {
  public AppConfig {
    if (llmProvider == null) llmProvider = "mock";
    if (retriever == null) retriever = RetrieverConfig.defaults();
  }
  public static AppConfig load(String settingsPath, Map<String, String> env) { /* Jackson + env overrides */ }
}
```

The defaults are the offline baseline — "loads successfully with no settings.json and no env" — which the offline tests depend on. `APP_RETRIEVER__TOP_K=20` overrides `retriever.topK` (`__` = nesting). `:kernel` is zero-SDK: Jackson (a serde analog) + SLF4J only. This is the Java mirror of pydantic-settings / figment / a Codable `AppConfig`.

## 7. Logging / provenance / privacy: SLF4J `Log`, payloads never logged

`:kernel`'s `Log` wraps the SLF4J facade; library code only emits events, and the concrete binding (slf4j-simple, Logback, …) is chosen once at the composition root (`:app`).

```java
public final class Log {
  private static final Logger LOGGER = LoggerFactory.getLogger("app");
  public static void info(String category, String message) { LOGGER.info("[{}] {}", category, message); }
  public static void logProvenance(String source, String impl, String version, int count) {
    LOGGER.info("provenance source={} impl={} version={} count={}", source, impl, version, count);
  }
}
```

Discipline:

- **Privacy is the API shape.** `logProvenance` has parameters only for `source` / `impl` / `version` / `count` — codes, counts, versions. The payload (answers, source text, vector values, user input) has **no parameter to pass in**. Rather than relying on a human to remember to redact, "payloads never logged" is a signature constraint. Put this in `:kernel`'s CLAUDE.md as a hard rule.
- **Library code only emits events**; the backend is configured once, at the composition root. No mutable shared logging state on the hot path.

## 8. Prompts: classpath resources + strict rendering

Prompts live in `:kernel`'s `src/main/resources/prompts/<domain>/*.md`, loaded as **classpath resources** (`getResourceAsStream`) so they ship in the jar — dev and release identical, no runtime path problems (the Java mirror of Swift `Bundle.module` / Rust `include_str!`).

**Strict rendering**: a `{{ key }}` referenced in the template but not supplied throws `PromptException.MissingVariable` — never a silent empty string (the mirror of Jinja2 `StrictUndefined` / minijinja strict undefined). The renderer is a single-exit loop (no `break`/`continue`): an unclosed `{{` leaves the remaining text as a literal. Changing a prompt = changing the repo + rebuilding (more disciplined); runtime hot-swap is a separate feature, out of scope here.

## 9. Structure: Gradle multi-module, module-per-domain

Depth comes from **modules** (many modules), not one module with deep folders. A Gradle module ≈ Cargo crate ≈ SPM target: module-level dependency isolation. "Fix the reranker" resolves to `:retrieval/...` with no search.

```
repo/
├── settings.gradle.kts        # module registration (Gradle has no glob; explicit include + a sentinel)
├── build.gradle.kts           # root: plugins apply false (each module applies them itself)
├── gradle/libs.versions.toml  # version catalog: every version pinned (one matrix)
├── .editorconfig              # non-Java formatting + generated-bindings exclusion
├── ci.sh  Makefile  gradle.properties
├── CLAUDE.md                  # root routing table
├── docs/adr/  configs/settings.json  .env.example
├── kernel/    # cross-cutting: AppConfig / Log / Prompts (+ CLAUDE.md + resources/prompts/); java-library, zero SDK
├── domain/    # ports (interfaces) + records + sealed boundary errors; zero SDK / zero framework
├── adapters/  # impls; MockProvider default + ProviderFactory seam (+ tests: conformance + smoke)
├── retrieval/ generation/  # domain feature modules (scaffold generates per --domains)
└── app/       # application plugin: manual composition root (Wiring + Main)
```

Notes:

- **Module names are project-independent**: `:kernel`/`:domain`/`:adapters`/feature names are fixed; only the base package, `rootProject.name`, and CLAUDE.md headers carry the literal name (via `__PKG__`, with the source-package directory `__PKG_PATH__` = its `/` form). Infra is `:kernel`, not `:core` (avoids the std/concept collision).
- **Module roles**: `:kernel` cross-cutting infra (java-library, zero external SDK); `:domain` pure abstraction (java-library, **zero SDK zero framework**); `:adapters` impls + `MockProvider` + `ProviderFactory`; feature modules depend on `:domain` + `:kernel`; `:app` the one `application` module (manual composition root).
- **Dependency direction is one-way**: feature / `:adapters` → `:domain` + `:kernel`; `:app` → everything. `:domain` is zero-SDK and **never** depends on `:adapters` (a mechanically-checked invariant, §12).
- **Gradle has no Cargo `members = ["*"]` glob** — every module must be `include`d explicitly. So scaffold injects feature modules at two sentinels: `settings.gradle.kts`'s `// __DOMAIN_MODULES__` (append `include(":<name>")`) and `app/build.gradle.kts`'s `// __DOMAIN_APP_DEPS__` (append `implementation(project(":<name>"))`). The template builds with zero domains.

### 9.1 A CLAUDE.md per module (layered context)

The root `CLAUDE.md` is a **routing table** (hard constraints + where to look + the polyglot boundary only); each module directory's `CLAUDE.md` states that module's responsibility, dependency direction, and local contract (`:domain`'s "zero SDK zero framework", `:adapters`' "errors normalize + Mock default", `:kernel`'s "payloads never in `Log`"). `check_conformance.py` requires one per module. The benefit: an agent working in a module gets the precise local constraints nearby, not diluted in one big document.

### 9.2 Navigability

Naming-as-path is the navigation analog of "types as interface contracts"; Gradle lifts it to the module level. Group by capability (not by `models/`/`util/`), nesting until leaf files have a single responsibility. Deep structure + consistent naming = "which code is where" with no search.

## 10. Model-agnostic: provider interface seam + zero-SDK `:domain` + manual composition root

The model is a hot-swappable commodity. Pull correctness, testability, and auditability out of the concrete model and pin them to interfaces + deterministic code.

- **Every external dependency = a minimal interface in `:domain`** (`Llm`/`Embedder`/`Reranker`/vector store/parser), failing with `ProviderException`. Domain logic depends only on the interface:

```java
public interface Llm {
  String complete(String prompt) throws ProviderException;   // normalized at the adapter boundary
}
```

- **`MockProvider` is the default implementation (not a test stub)**: deterministic, offline, no key, zero SDK. The app, tests, and CI run against Mock by default — fast, stable, free, un-polluted by randomness.
- **`ProviderFactory` is the assembly seam**: it selects an impl by config string, default `mock`, and an **unknown provider throws — never a silent fallback**:

```java
public static Llm makeLlm(String provider) {
  return switch (provider) {
    case "mock" -> new MockLlm();
    default -> throw new IllegalArgumentException("unknown llmProvider: " + provider);
  };
}
```

- **The seam maps to a manual composition root.** The interface is in `:domain`, the default impl (Mock) in `:adapters`, and the **one assembly point is `:app`'s `Wiring`** — a plain, framework-free function that reads config and picks impls. **No DI framework** (Dagger/Guice/Spring): a hand-written wiring function is enough at this size, and it keeps `:app` the only place that "chooses". When wiring genuinely outgrows it (many singletons, scopes, lifecycles), introduce a DI container **there and nowhere else**, so the rest of the code keeps depending only on ports. This is the Java tuning of the Kotlin Hilt composition root / Rust `app` `match` root.
- **`:domain` is zero SDK / zero framework** (mechanically checked): `check_conformance.py` parses `domain/build.gradle.kts` and flags any SDK-denylist substring (`openai`/`anthropic`/`langchain4j`/`pinecone`/`onnxruntime`/…) or framework token (`org.springframework`/`micronaut`/`quarkus`/`dagger`/…). `:domain` is a plain `java-library`.
- **Real SDKs live in a gated sibling module**: a real backend like `:adapters-openai` is a separate module that depends on the SDK, **gated by a Gradle property** — `settings.gradle.kts` `include`s it only when `-PrealProviders` is set, so the default build never pulls the SDK. The Java analog of Cargo features / SPM traits:

```kotlin
if (providers.gradleProperty("realProviders").isPresent) {
    include(":adapters-openai")
}
```

Inside the adapter, vendor errors normalize to `ProviderException`; program bugs propagate.

- **Conformance kit (`:adapters`'s `ProviderConformanceTest`)**: any type claiming to implement a port (Mock and real backends) runs the same behavioral invariants — hot-swapping is only safe when all plugs behave alike. Mock and real backends go into the same supplier map and share the assertions (determinism, input-count preserved, non-empty vectors, non-empty completion).
- **Offline smoke (`SmokeTest`)**: the whole path runs with no key — default config + Mock + strict prompt rendering + record validation — and asserts "unknown provider throws (no silent fallback)", "missing variable throws `MissingVariable`", "`new TopK(0)` / `new TopK(101)` throw". A hard acceptance test.

## 11. Making AI output trustworthy: push constraints into control flow, not the prompt

The prompt is a soft constraint; temperature, jailbreaks, and long context all route around it. Only constraints that sink into code move from "probabilistically obeyed" to "structurally impossible to violate". This section is principle (not fully mechanically checkable), but it is the upper-level discipline for AI-touching code.

- **Constrain, don't ask.** For non-negotiable properties (no fabrication, must-cite, no privilege escalation), make the model physically unable to violate them — on a fact hit, synthesize the answer deterministically from structured values in code and discard the model's prose; on a miss, the orchestration layer rewrites to "not found". Migration: list "must never happen", ask of each "can the model comply and still violate it?", and move every "yes" out of the model.
- **Narrow the emission surface.** Don't let the model freely generate the key payload — make it choose from a `sealed interface` / `enum`, or call a tool returning a tri-state (`found`/`notFound`/`unrecognized`); take the final value from the tool result, not the model text. A `sealed interface` + exhaustive `switch` is a natural controlled surface, and the compiler proves you handled every case.
- **Guardrails are deterministic, independent, never pluggable.** The understanding layer (intent parsing) is swappable; safety decisions (privilege, sensitive isolation) are deterministic code re-evaluated from raw input, not trusting a pluggable component's output. **In a polyglot repo, guardrails live in the core, not the host** — the host receives typed values across the FFI and does not re-judge.
- **Provenance in, privacy out**: see §7 (`logProvenance` + the payload-never-a-parameter discipline).

## 12. Externalize the implicit backstop into artifacts that can fail

Humans judge "done?" and "docs stale?" from experience; an agent has none and optimizes only observable feedback. Each failing check turns a piece of implicit knowledge into a hard constraint the agent can't quietly bypass.

- **The zero-warning gate** (§1): spotlessCheck → compileJava (`-Werror` + Error Prone + NullAway) → test → coverage. Any non-zero step = not done. Pin with a pre-push hook.
- **`check_conformance.py`'s mechanical invariants** (structure; the `ci.sh` gate covers behavior + quality). Gradle has no clean manifest JSON export, so it does text/regex checks on `build.gradle.kts` / `settings.gradle.kts`. It checks: ① required root files (`settings.gradle.kts`/`build.gradle.kts`/`libs.versions.toml`/`.editorconfig`/`ci.sh`/`CLAUDE.md`); ② multi-module (`include` ≥ 2); ③ **a CLAUDE.md per module + a `src/test` per non-app module**; ④ **`:domain` zero-SDK (denylist) + zero-framework (tokens) + no `:adapters` dep**; ⑤ `-Werror` wired per module or at root; ⑥ **Error Prone + NullAway wired, NullAway elevated to `error()`**; ⑦ **Spotless + a Java formatter configured**; ⑧ **`jacocoTestCoverageVerification` wired on a non-app module**; ⑨ `ci.sh` has `set -euo pipefail` and chains format → compile → test → coverage; ⑩ the catalog pins Error Prone / NullAway / Spotless / a formatter / JUnit; ⑪ if a generated-bindings dir exists, it is gate-excluded.
- **Self-describing artifacts derive from real code**: introspect the dependency graph with `./gradlew :module:dependencies`, don't hand-draw it — a hand-maintained graph rots, and a rotten graph is worse than none.
- **Layered context** (§9.1): a root routing table + nearby per-module contracts, not one big document read top to bottom. Context windows are scarce; "dump everything" dilutes the signal.

## 13. Driving AI on big work: decomposable, step-verifiable, adversarially reviewed

Treat AI as supervisable labor, not unsupervised autopilot. The lightweight workflow layer:

- **Decision-first (ADR, `docs/adr/`)**: architecture/product decisions are numbered, immutable ADRs (context + choice + rejected alternatives and why). AI is best at filling implementation under fixed constraints, worst at making the ambiguous trade-offs for you; rejected-reasons stop it re-walking excluded paths.
- **TDD red-light first** — spine-level here (§4). Give a subagent the failing test as acceptance criteria.
- **Numbered steps, each independently green**: split a big refactor into ordered steps, one commit per step through the full `./ci.sh` before the next — never a giant diff. Compress the failure blast radius to one step.
- **Decompose → parallelize → synthesize**: the lead agent splits well-bounded, fully-specified subtasks, reviews each diff, and passes the gate before committing.
- **Adversarial independent review**: after writing, run a separate, hostile, multi-perspective review ("assume it's wrong; falsify it"), prioritizing what tests can't cover (diagrams, docs, trade-offs).
- **Polyglot amplifier**: a core-contract change touches many sub-trees. **A core-contract change + regenerated bindings + each host's adaptation = one coherent commit** — never split it so some bindings are stale mid-commit (the drift guard would fail).

## 14. Boundary with polyglot-core-standard (complementary, non-overlapping)

This standard governs the **Java host's internals**; `polyglot-core-standard` governs the **cross-language seam**. In a polyglot repo they compose with clean responsibility splits:

- **Seam (polyglot's job)**: the core is the single source of truth (shared logic/data models exist once, in Rust); the contract is declared once, host bindings are **derived**, **never hand-mirrored**; the FFI boundary is typed & fallible (core `Result<T,E>` → a Java checked exception, **no panic crosses FFI**); a **composed gate** (`make check` chains each host gate + a drift guard); toolchain + generator versions are pinned in the root `versions.toml` (this standard's `libs.versions.toml` must align its Error Prone / NullAway / Spotless / generator versions with it).
- **Internals (this standard's job)**: format / lint / strict compile / module structure / provider seam / tests / coverage — §1–§13.
- **Java has no official UniFFI support.** UniFFI generates Swift/Kotlin/Python bindings, not Java. A Java host binds a Rust core through **JNI**, **JNA**, or the **Panama Foreign Function & Memory API (FFM, `java.lang.foreign`, stable since JDK 22)** — that bridge is the seam. Treat any *generated* binding code (e.g. `jextract` output, or a `**/generated/**` tree) as a vendored artifact: `linguist-generated`, gate-excluded (Spotless `targetExclude` + Error Prone `excludedPaths` + `.editorconfig`), never edited. The host's escape-hatch bans do **not** apply to generated files — governance moves to the hand-written bridge.
- **The hand-written FFI bridge is governed seam code**: the layer that consumes the generated/native types and re-types native failures into host values (a `ProviderException` or a domain value) is **governed by this standard** (escape hatches shut, exceptions normalized, generated types reused rather than re-declared). The generated bindings themselves are not governed.
- **The gate plugs into `make check-java`**: this module's `./ci.sh` is the Java cell of the composed gate.
- **The AI seam lives in the one sub-tree that calls the model** (usually the core or a dedicated worker): if the LLM lives in the core, the Java host is **spine-only** — it receives typed values across the FFI and does not wrap `MockProvider` (that would be cargo-culting). This standard's AI-triggered layer switches on only when the **Java host itself** calls a model.

## 15. Scale to project size: universal spine vs AI-triggered layer

The module split, per-module CLAUDE.md, ADRs, and provider seam are real overhead — overkill for a 200-line tool. They are **triggered, scalable patterns**, not blanket mandates:

- **Scale along two axes** — size × domain.
- **Universal spine** (any Java project, AI or not): compiler strictness + `-Werror` + `-Xlint:all` + Error Prone + NullAway, the zero-warning gate, TDD + a coverage floor, sealed errors + escape hatches shut, Jackson + lightweight record validation at boundaries, Gradle module-per-domain + deep naming, a version catalog, Spotless.
- **AI-triggered layer** (only when actually calling an LLM/embedding/vector store): the `:domain` interface seam + zero-SDK module, `MockProvider`-as-default, classpath prompts + strict rendering, `logProvenance`, constrain-don't-ask.
- A pure app (never calls a model) takes the spine in full and skips the AI layer; bolting on `MockProvider` is cargo-culting.
- **Small projects can start single-module**: one module + Spotless + Error Prone + NullAway + the zero-warning gate with a coverage floor is a perfectly good small-scale instantiation. Split a module out when a second responsibility appears; push a dependency behind an interface when you actually call a model.
- **Polyglot repo**: the AI seam lives in the sub-tree that calls the model (usually the core); the Java host stays spine-only and receives typed values across the FFI.

---

## Appendix: mapping to the Python / Rust / Swift / Kotlin siblings

| Concern | Python | Rust | Swift | Kotlin/Android | **Java** |
|---|---|---|---|---|---|
| Static typing | mypy `--strict` | compiler (free) | compiler (free) | compiler (null-safety) | compiler + `-Werror` + `-Xlint:all` + **Error Prone** |
| Runtime typing | beartype + claw hook | not needed | not needed | not needed | not needed |
| Null-safety | mypy | `Option<T>` | optionals | Kotlin null-safety | **NullAway** (JSpecify `@Nullable`), compile-time |
| "No escape hatches" | no bare `Any` | `#![forbid(unsafe_code)]` | no `!`/`try!`/`as!` | no `!!`/unchecked `as`/`lateinit` | no unchecked cast (`-Xlint` + `-Werror`), no null (NullAway), no swallowed exception, no `System.out` |
| No silent failure | no bare `except`, StrictUndefined | `Result`/`thiserror`, clippy `unwrap` | typed `throws(E)` | sealed errors + `Result` | **sealed `ProviderException` + exhaustive `switch`**; normalize at boundary |
| Escapes recorded | `# type: ignore[code] # reason` | `#[allow(clippy::…)] // reason` | `// swiftlint:disable:next … — reason` | `@Suppress("rule") // reason` | `@SuppressWarnings("NullAway") // reason` |
| Boundary validation | pydantic | `serde` + newtype | `Codable` + newtype | kotlinx.serialization + value class | **Jackson + record compact-constructor (lightweight; not newtype-everywhere)** |
| TDD + coverage | pytest (advisory) | `#[test]` (advisory) | XCTest (advisory) | JUnit (advisory) | **TDD spine-level + JaCoCo coverage floor in the gate** |
| Structure | src layout + domain-first deep | Cargo workspace + crate-per-domain | SPM package + target-per-domain | Gradle multi-module | **Gradle multi-module + module-per-domain** |
| Model-agnostic | `ports/`+`adapters/`, zero-SDK core | `domain`(trait)+`adapters` | `Domain`(protocol)+`Adapters` | `:domain`(interface)+`:adapters` | **`:domain`(interface)+`:adapters`, zero SDK zero framework** |
| Optional backends | optional extras + lazy import | `optional` deps + features | package traits | gated module + gradle property | **gated module + gradle property** |
| Assembly seam | `ports/factory.py` | `app` `match` root | `App` root | Hilt `@Module @Provides` | **manual `Wiring` (no DI framework)** |
| Config | pydantic-settings + yaml | figment + toml | Codable + layered | `@Serializable AppConfig` + layered | **record `AppConfig` + layered (defaults < settings.json < env `APP_*`)** |
| Logging/provenance/privacy | logging + log_provenance + SENSITIVE_FIELDS | tracing + log_provenance | os.Logger + privacy interpolation | `Log` + logProvenance | **SLF4J `Log` + logProvenance (payload not a parameter)** |
| Prompts | PackageLoader (in the wheel) | `include_str!` | `Bundle.module` | classpath resources | **classpath resources (in the jar) + strict rendering** |
| Gate | ruff+mypy+drift+pytest | fmt+clippy -D+doc+test+cargo-deny | swift-format+swiftlint+build+test | ktlint+detekt+compile+test | **Spotless + compile(-Werror+ErrorProne+NullAway) + test + JaCoCo** |
| Layered context | root CLAUDE.md + nearby | root + per-crate CLAUDE.md | root + per-target CLAUDE.md | root + per-module CLAUDE.md | **root + per-module CLAUDE.md** |
| Scaffold / conformance | scaffold.py / check_conformance.py | same | same (`dump-package`) | same (text/regex on gradle) | **scaffold.py / check_conformance.py (text/regex on gradle)** |
| Polyglot FFI | PyO3 (hand-written) | the core | UniFFI (generated) | UniFFI/JNI (generated) | **JNI / JNA / Panama FFM (no official UniFFI)** |
