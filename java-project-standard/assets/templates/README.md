# __PKG__

A Gradle multi-module project scaffolded per `java-project-standard`: the Java compiler + `-Werror` +
Error Prone + NullAway (JSpecify) as the static guarantee, a one-command zero-warning gate with a
coverage floor, escape hatches shut, Jackson at boundaries, module-per-domain structure, a zero-SDK
`:domain` interface seam with a default `MockProvider`, a manual composition root, and Spotless
(google-java-format) formatting.

## Layout

```
settings.gradle.kts          # module registration (Gradle has no glob; explicit include)
build.gradle.kts             # root: plugins apply false; each module applies + configures them
gradle/libs.versions.toml    # version catalog: every version pinned
ci.sh  Makefile              # the one zero-warning gate
configs/settings.json        # structured config (non-secret; env overrides per key)
kernel/      cross-cutting infra (AppConfig / Log / Prompts + bundled resources); zero SDK
domain/      ports (interfaces) + records + sealed boundary errors. Zero SDK / zero framework
adapters/    port impls. Default MockProvider (offline, no key, zero SDK) + ProviderFactory seam
app/         application + manual composition root (wires impls by config)
```

Dependency direction (one-way): feature / `:adapters` -> `:domain` + `:kernel`; `:app` -> everything.
`:domain` never depends on `:adapters` / an SDK.

## Requirements

A JDK **21+** on `JAVA_HOME` (the build targets `--release 21` and runs Error Prone + google-java-format
on the daemon JVM; both support JDK 21..25+). Gradle **9.x** is required to run on JDK 25.

## Run the gate (the only completion judge)

```bash
gradle wrapper --gradle-version 9.4.1   # first time: generate the wrapper (needs a system gradle)
./ci.sh                                  # spotlessCheck -> compileJava(-Werror) -> test -> coverage
# or
make check
```

Single steps: `make fmt` (spotlessApply), `make lint`, `make build`, `make test`, `make coverage`.

## Enabling a real provider

The default is fully offline, zero SDK. Put a real backend (e.g. OpenAI) in a **gated sibling module**
(`:adapters-openai`), included only when `-PrealProviders` is set, and normalize vendor errors to
`ProviderException` inside the adapter. See `adapters/CLAUDE.md`.

## Relationship to polyglot-core-standard

This skeleton governs the **Java host's internals**. In a "Rust core + multi-language bindings" repo:
shared logic lives only in the core; generated bindings are vendored artifacts (`linguist-generated`
/ gate-excluded / never-edited); this module's `./ci.sh` plugs into polyglot's `make check-java`.
