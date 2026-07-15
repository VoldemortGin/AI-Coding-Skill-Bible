# module: :kernel — contract

Responsibility: cross-cutting infra -- `AppConfig` (typed record + layered load), `Log` (SLF4J facade
+ provenance + privacy), `Prompts` ([AI layer] classpath resources + strict rendering).
- **No vendor SDK** (Jackson = serde analog for config, SLF4J = tracing analog; both language-level).
- `AppConfig` must load successfully with no settings.json and no env, from defaults (offline tests
  depend on this).
- Logging discipline: **payloads (answers / source text / vectors / user input) never reach `Log`** --
  `logProvenance` has parameters only for codes / counts / versions. Privacy is the API shape. A
  concrete SLF4J binding is chosen at the composition root (`:app`), not here.
- Strict prompt rendering: a referenced-but-missing variable throws `PromptException.MissingVariable`
  (never a silent empty string). Resources live in `src/main/resources/prompts/`, shipped in the jar.
- Dependency direction: upstream none; downstream `:adapters` / feature modules / `:app` may depend
  on it.
