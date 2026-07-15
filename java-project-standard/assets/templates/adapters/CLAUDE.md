# module: :adapters — contract

Responsibility: concrete implementations of `:domain` ports + the assembly-seam factory.
- `MockLlm` / `MockEmbedder` are the **default** implementations (not test stubs): deterministic,
  offline, no key, **zero SDK**.
- `ProviderFactory` selects an implementation by config string: default `mock`, unknown provider
  **throws** (never a silent fallback). `:app`'s `Wiring` calls it.
- Real backends (e.g. `OpenAiLlm`) live in a **gated sibling module** (`:adapters-openai`):
  - included from `settings.gradle.kts` only when the `realProviders` Gradle property is set (the
    Cargo-feature / SPM-trait analog); the default build never pulls an SDK.
  - the adapter **normalizes** vendor errors to `ProviderException` (`Transport` / `InvalidResponse`
    / `MissingCredentials`); program bugs propagate.
- The default build/test is fully offline; it never fetches a third-party SDK.
- Conformance: every type claiming to implement a port (mock and real) runs `ProviderConformanceTest`
  -- the same behavioral invariants. Hot-swapping is only safe when all plugs behave alike.
- Dependency direction: upstream `:domain` + `:kernel`; downstream `:app` selects by config. **Never**
  depended on by `:domain` / a feature module.
