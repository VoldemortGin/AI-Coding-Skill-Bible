# module: :app — contract

Responsibility: the runnable application + manual composition root.
- The one place implementations are selected by config: `Wiring.wire(config)` calls `:adapters`'s
  `ProviderFactory`, default Mock, unknown provider throws (no silent fallback). `Main` loads config,
  wires, runs.
- **No DI framework by design.** A hand-written wiring function is enough at this size. When wiring
  outgrows it (many singletons, scopes, lifecycles), introduce a DI container (Dagger, Guice) **here
  and nowhere else**, so the rest of the code keeps depending only on ports.
- The concrete SLF4J binding (slf4j-simple) is chosen here; library modules only emit events.
- Coverage exemption: `Main.main()` and wiring are exercised by running the app, so `:app` has no
  coverage floor (every other module enforces 80% line coverage). Keep real logic out of `:app`.
- Dependency direction: upstream every module; downstream none.
- If this repo is polyglot: the hand-written FFI bridge (consuming generated JNI/FFM bindings,
  re-typing generated exceptions into host values) is governed seam code; the generated bindings
  themselves are gate-excluded and never edited.
