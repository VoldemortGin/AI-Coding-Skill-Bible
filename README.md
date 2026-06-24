# AI Coding Skill Bible

A set of **project-standard skills** for AI coding agents (Claude Code, Codex, …) — engineering charters that make an agent's output *trustworthy by construction* rather than by hope.

## The spine

> Trust is placed not in the model, but in the machine-checkable code that constrains it.

Every standard does the same four things, each in its own language:

1. **Keep the escape hatches shut and turn the strictest static checks on** — the compiler/type-checker and lints are the guarantee, not the prompt.
2. **Push every external dependency behind a provider interface** so the model (or any SDK) is hot-swappable, with a deterministic mock as the default.
3. **Organize deep and name-navigable** — module-per-domain, names that resolve to paths with no search.
4. **Mechanize the implicit knowledge** a human would otherwise hold — a one-command zero-warning gate, a `CLAUDE.md` contract in every module, and drift guards.

The agent's output ceiling equals the tightness of that loop.

## The standards

| Skill | Language / scope | Static gate (highlights) |
|-------|------------------|--------------------------|
| `rust-project-standard` | Rust crate / workspace | `clippy -D warnings` + `rustfmt` + `cargo-deny` |
| `swift-project-standard` | Swift / SwiftUI (SPM) | Swift 6 complete strict concurrency + swift-format + SwiftLint + warnings-as-errors |
| `python-project-standard` | Python package | ruff + mypy + runtime type-checking, parse-don't-validate at boundaries |
| `frontend-project-standard` | TypeScript / React / Next (pnpm monorepo) | `tsc` strict + Zod at every boundary + ESLint + Prettier |
| `android-project-standard` | Kotlin / Android (Gradle) | detekt + ktlint + `allWarningsAsErrors` + library `explicitApi()` |
| `polyglot-core-standard` | Cross-language seam | one canonical Rust core + derived UniFFI/PyO3 bindings + composed gate |

The first five govern a **single language's internals**. **`polyglot-core-standard`** governs the **cross-language seam**: one canonical Rust core + thin hosts in each language, with generated bindings as vendored, gate-excluded artifacts and a composed `make check` as the only correctness judge. The two layers are complementary — a polyglot repo applies the core standard *at the seam* and the matching per-language standard *inside each host*.

## What's in each skill

```
<skill>/
  SKILL.md                      # entry: frontmatter + spine + non-negotiables + structure
  references/standard.md        # the full standard with rationale + per-module contracts
  scripts/scaffold.py           # generate a conforming project
  scripts/check_conformance.py  # verify the mechanically-enforceable structural invariants
  assets/templates/             # exact boilerplate: configs, a CLAUDE.md per module, gate scripts, skeleton
```

## Using them

**As agent skills** — symlink (or copy) each directory into your skills dir:

```bash
git clone https://github.com/VoldemortGin/AI-Coding-Skill-Bible.git
cd AI-Coding-Skill-Bible
for d in *-project-standard polyglot-core-standard; do
  ln -sfn "$PWD/$d" ~/.claude/skills/"$d"
done
```

The agent then applies the matching standard **by default** whenever you start or scaffold a project, set up tooling/CI, decide module structure, add an LLM/embedding/vector-store dependency, wire providers, or check conformance — even when you don't name the standard explicitly.

**Scaffold a new conforming project:**

```bash
cd <skill> && python scripts/scaffold.py <name> [--domains ingestion retrieval ...]
```

**Check an existing project:**

```bash
python <skill>/scripts/check_conformance.py <project_root>
```

**As a human charter** — read each `SKILL.md` (the gate + architecture conventions) and `references/standard.md` (the full rationale) as the engineering charter for that language.

## Design notes

- **Scale along two axes, size *and* domain.** Each standard has a *universal spine* that holds for any project in its language, plus an *AI-triggered layer* (the provider seam + mock-as-default + prompt discipline) that only switches on once the project actually calls a model. A pure library/CLI takes the spine and skips the AI layer — bolting on a mock provider where there's no model is cargo-culting, not conformance.
- **The gate is the only judge.** "Looks fine" is never the bar; `./ci.sh` / `make check` green is. Pin it with a pre-push hook; mirror it in CI.

## License

[MIT](LICENSE) © 2026 Han Lin — use, adapt, and share freely.

---

*These standards are model-agnostic and intentionally opinionated. Adapt the thresholds to your project; keep the spine.*
