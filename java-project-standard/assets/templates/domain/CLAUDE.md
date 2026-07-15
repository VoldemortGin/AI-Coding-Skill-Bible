# module: :domain — contract

Responsibility: ports (interfaces) + models (records) + sealed boundary errors. **Zero vendor SDK /
zero framework** (a mechanically-checked invariant).
- Defines abstractions and data only; concrete provider impls live in `:adapters`.
- Keep ports narrow (`throws ProviderException`); depend on jspecify only.
- Encode a constraint in a record's compact constructor where it earns its keep (e.g. `TopK`) --
  lightweight parse-don't-validate at real boundaries, not a newtype around every field.
- Errors are sealed hierarchies (`ProviderException`); `switch` over them is checked exhaustive by
  the compiler (make the sealed base `abstract` so only the permitted subtypes are possible).
- Dependency direction: upstream none (stay pure); downstream `:adapters` implements these ports and
  feature modules depend here. **Never** depend on `:adapters` / an SDK / a framework.
