# apple/ — Swift host (swift-project-standard, spine-only)

A thin host over the core. Conforms to **swift-project-standard**'s *universal spine*:
Swift 6 language mode + complete strict concurrency + warnings-as-errors, the escape
hatches shut (`!`/`try!`/`as!`/IUO/`@unchecked Sendable`), `Codable` + newtypes at
boundaries, `os.Logger`, the swift-format + SwiftLint double gate via `./ci.sh`.
**No AI layer** — this host renders results the core computes; it never calls a model
(bolting `MockProvider` on here would be cargo-culting, not conformance).

## Seam-local contract (polyglot-core-standard)

- **`Generated/__REPO___core.swift` is a vendored UniFFI artifact**: `linguist-generated`,
  **excluded** from swift-format and SwiftLint (`.swiftlint.yml` `excluded:` +
  `.swift-format` ignore), and **never hand-edited**. Regenerate via `make gen-bindings`.
  The escape-hatch bans do **not** apply to it — its `try!`/`as!` are generator output.
- **All core calls go through a thin hand-written wrapper** (e.g. `Sources/.../CoreClient.swift`)
  — the governed FFI seam. It re-types the generated `throws` into host-native values and a
  Swift `enum` error. The escape-hatch bans, strict concurrency, and newtype rules apply to
  the wrapper, NOT to the generated file.
- **Never hand-copy a core struct** — consume the generated type, or wrap it in a host
  newtype. A core contract change arrives via regeneration, not a manual edit.
