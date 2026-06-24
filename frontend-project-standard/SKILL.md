---
name: frontend-project-standard
description: >-
  Enforce a strict, type-safe, model-agnostic, AI-navigable TypeScript frontend
  project standard: TypeScript `strict` + stricter flags as a static gate
  (`tsc --noEmit`) + Zod runtime validation at every boundary + the escape hatches
  shut (`any` / non-null `!` / `@ts-ignore` → justified `@ts-expect-error` / unsafe
  `as`), no silent failures, a pnpm + Turborepo monorepo with package-per-domain deep
  structure, a zero-SDK zero-framework `domain` package behind provider interface
  seams with a default `MockProvider`, structured logging, Zod-validated env,
  type-aware ESLint + Prettier, a one-command zero-warning gate (tsc + eslint +
  prettier + vitest + build), a CLAUDE.md in every package, and scaffold/conformance
  scripts. Use whenever starting or scaffolding a new TypeScript / React / Next.js
  frontend project; setting up tsconfig / eslint / prettier / turbo / pnpm; deciding
  package or module structure; adding an LLM / embedding / vector-store dependency;
  wiring providers or adapters; setting up CI; or checking that an existing frontend
  project conforms. Apply it even when the user only says "start a frontend project",
  "set up the structure", or "add an LLM" without naming the standard.
---

# Frontend Project Standard

This skill is the guiding standard for **any** TypeScript frontend work. Apply it by default; don't wait to be asked.

Its spine: **trust is placed not in the model, but in the machine-checkable code that constrains it.** TypeScript is strongly typed at authoring time, but — like Python and unlike Rust/Swift — **its types are erased at runtime.** A `User` that the compiler proved is a `User` is just an object once it's running; a `fetch` response typed `as Product[]` is whatever the server actually sent. So the frontend needs *two* layers, exactly mirroring the Python sibling's mypy + pydantic: **`tsc` strict gives the static guarantee, and Zod at the boundary gives the runtime guarantee** — neither alone is enough. On top of that: keep the escape hatches shut (`any` / `!` / `@ts-ignore` / unsafe `as`), push every external dependency behind a provider interface so the model is hot-swappable, organize deep and name-navigable as a pnpm + Turborepo monorepo, and mechanize the implicit knowledge a human would otherwise hold in their head — via a zero-warning gate, a per-package contract, and drift guards. The agent's output ceiling equals the tightness of that loop.

Unlike Python's beartype, there is **no runtime type-checking import hook** in the browser/Node — instrumenting every internal call site is not a thing here. So the runtime layer is concentrated *at the boundaries only* (rule 2): the static gate covers the interior, Zod covers everything crossing in.

Baseline: **Node 22+**, **pnpm** workspace + **Turborepo**, ES modules (`"type": "module"`), latest stable **TypeScript** with a strict `tsconfig.base.json` extended by every package, **Zod** (boundaries + env), **ESLint** flat config with **typescript-eslint** type-aware rules (`strictTypeChecked` + `stylisticTypeChecked`, `projectService: true`) + **Prettier**, **Vitest**, and two thin composition-root shells — **React + Vite** (`apps/web-vite`) and **Next.js App Router** (`apps/web-next`). TS-first: no `.js` in `src/`; only tool configs tolerate `.mjs`/`.cjs` where a runtime hard-requires it.

This standard is the **project-level engineering charter** (the gate + architecture conventions). For *how to write the implementation inside a package*, it delegates to the existing implementation/design skills rather than restating them:

- **Component performance, memoization, render discipline** → `react-best-practices`.
- **Component composition, compound components, render props, UI-level dependency injection** → `composition-patterns`.
- **React 19 APIs** (`use`, actions, `useOptimistic`, ref-as-prop) → `react-expert`.
- **Next.js App Router mechanics** (server/client components, server actions, routing, streaming) → `nextjs-developer` and the `nextjs-*` family.
- **Visual design / taste / aesthetics** → `frontend-design`, `design-taste-frontend`, `impeccable`.
- **End-to-end browser testing** → `webapp-testing` (Playwright).

Cite them where relevant; don't duplicate their content. This standard owns the gate and the architecture; those skills own the implementation and the look.

## When starting a new project

```bash
python scripts/scaffold.py <scope> --target <dir> --domains retrieval generation
```

This mirrors `assets/templates/` into a conforming pnpm + Turborepo monorepo (`packages/kernel` + `packages/domain` + `packages/adapters` + a domain package per `--domains` + `apps/web-vite` + `apps/web-next` + a CLAUDE.md per package + `ci.sh` + ADR), and substitutes `__SCOPE__` (the npm scope; package names become `@<scope>/kernel`, `@<scope>/domain`, …). Module names (`kernel`, `domain`, `adapters`, `<domain>`) are project-independent — only the scope and the CLAUDE.md headers carry the literal name. Because pnpm's `packages/*` glob auto-includes new packages (like Cargo, no manifest injection), scaffolded domain packages need no edit to `pnpm-workspace.yaml`. Pass `--shells vite` or `--shells next` to emit only one shell. When adapting an existing repo, copy from `assets/templates/` by hand.

Then: `pnpm install` once, and `./ci.sh` (or `make check`) to verify.

## When working on existing code

Apply the rules below, keep new code strict, and verify structural invariants:

```bash
python scripts/check_conformance.py <project_root>
```

It parses `package.json` (plain JSON) and reads tsconfig via `npx tsc --showConfig` (falling back to tolerant parsing) and checks the mechanically enforceable invariants: `pnpm-workspace.yaml` + `turbo.json` present; `tsconfig.base.json` has `strict: true` plus the stricter flags (`noUncheckedIndexedAccess` et al.); **the `domain` package's deps/devDeps/peerDeps intersect neither the vendor-SDK blacklist nor the UI-framework blacklist (react / react-dom / next / vue / svelte / @angular/core)** — i.e. domain is zero-SDK *and* zero-framework; `eslint.config.*` carries the escape-hatch bans (`no-explicit-any`, `no-non-null-assertion`); `ci.sh` chains tsc/typecheck + eslint/lint + prettier/format + vitest/test + build; a CLAUDE.md exists at the root and in every `packages/*` and `apps/*`; `.env.example` present. Non-zero exit = violation, machine-readable. Everything else is enforced by the gate and by applying the standard.

## The non-negotiables

Full rationale in `references/standard.md`.

1. **Static: TypeScript `strict` + stricter flags is the static gate; keep the escape hatches shut.** `tsconfig.base.json` turns on `strict` *plus* `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noImplicitReturns`, `noFallthroughCasesInSwitch`, `noPropertyAccessFromIndexSignature`, `verbatimModuleSyntax`, `isolatedModules` — checked by `tsc --noEmit`. The escape hatches are *banned* by type-aware ESLint: no `any` (`no-explicit-any` + the `no-unsafe-*` family), no non-null `!` (`no-non-null-assertion`), no `@ts-ignore` (`ban-ts-comment` forces `@ts-expect-error` **with a description**), and `as` is a soft hatch the `no-unsafe-*` rules catch when it's dangerous — minimize it and justify it. A site that genuinely needs an exit takes the **controlled exit**: `// eslint-disable-next-line <rule> -- reason` or `@ts-expect-error -- reason` (explicit, auditable, greppable — the TS analog of a justified `# type: ignore`).

2. **Runtime: parse, don't validate — Zod at every boundary.** TS types are erased at runtime, so a value crossing *into* the program is untyped until parsed. Every boundary — `fetch`/API responses, form input, `env`, `localStorage`/`sessionStorage`, URL/search params, `postMessage`, **LLM output** — is parsed by a Zod schema at the entry point; `z.infer` derives the static type from the schema (one source of truth), and an invalid value throws *there*, not three layers deep. This is the exact role pydantic plays in the Python sibling; the difference is there's no import hook, so runtime checking lives only at boundaries.

3. **No silent failures.** No swallowed `catch` (handle or rethrow — never an empty `catch {}`); exhaustive `switch` with a `never` fallback (`switch-exhaustiveness-check`); no floating promises (`no-floating-promises` + `no-misused-promises`); a React error boundary at the app shell; vendor/network errors normalized at the adapter boundary into a `ProviderError`. Program bugs propagate — never `catch (e) {}` into a fallback.

4. **Model-agnostic: every external AI dependency behind an interface in `domain`; SDKs only in `adapters`.** The `domain` package has **zero SDK *and* zero UI-framework dependencies** (the checker parses `package.json` to enforce both). Real SDKs are `optionalDependencies`/`peerDependencies`, lazy-loaded with dynamic `await import()` *inside `adapters` only*. The seam selects an impl by config (`adapters/factory.ts` or the app composition root); vendor errors normalize to `ProviderError`. A deterministic **MockProvider is the default** (not a test stub) so the main path, tests, and CI run fully offline with no SDK or key. A conformance kit binds Mock and real backends to the same invariants.

5. **Completion = one zero-warning gate, the agent's only correctness judge.** `./ci.sh` runs `pnpm install --frozen-lockfile` → `turbo run typecheck` (`tsc --noEmit`) → `turbo run lint` (`eslint --max-warnings 0`, type-aware) → `pnpm run format:check` (`prettier --check`) → `turbo run test` (`vitest run`, offline, Mock default, smoke + conformance) → `turbo run build` (both shells + packages), under `set -euo pipefail`. Turbo orchestrates caching and topological parallelism. Run it after every change; fix until green; never "looks fine, commit". Pin it with a pre-push hook; CI mirrors it.

6. **Framework-agnostic core.** `kernel`, `domain`, `adapters`, and every domain package import **zero React / Next / Vue** — only `apps/*` (the composition roots) touch a framework. The core is portable across shells (the same logic runs under Vite, Next, or a CLI); the checker enforces zero-framework on `domain`, and the rule extends by convention to the rest of the core.

## Structure: pnpm + Turborepo monorepo, package-per-domain

The depth comes from the **monorepo** (multiple packages), not from one package with deep folders. A pnpm workspace package ≈ a Cargo crate / an SPM target: package-level dependency isolation plus a resolvable graph. "Fix the reranker" should resolve to `packages/retrieval/...` with no search.

```
repo/
├── package.json              # root: private, packageManager=pnpm, scripts (turbo run …)
├── pnpm-workspace.yaml       # packages: ["packages/*", "apps/*"]
├── turbo.json                # pipeline: typecheck / lint / test / build (dependsOn topo)
├── tsconfig.base.json        # strict baseline, extended by every package
├── eslint.config.mjs         # flat, type-aware, shared
├── .prettierrc.json  .gitignore  .env.example
├── ci.sh  Makefile  README.md  CLAUDE.md   # root routing table
├── docs/adr/
├── configs/settings.json     # env-related structured config (non-secret)
├── packages/
│   ├── kernel/               # cross-cutting: config (Zod env) / logging / prompts. Zero framework, zero SDK
│   ├── domain/               # ports (interfaces) + models (Zod) + errors. Zero SDK, zero framework
│   ├── adapters/             # impls; the only place that touches SDKs; MockProvider default
│   ├── retrieval/  generation/   # example domain packages (scaffolded, not built-in)
└── apps/
    ├── web-vite/             # React + Vite thin shell (composition root)
    └── web-next/             # Next.js App Router thin shell (composition root)
```

- **Dependency direction**: `domain` (zero SDK, zero framework) ← domain packages (`retrieval`/`generation`, depend on `domain` + `kernel`) and `adapters` (depend on `domain` + `kernel`, + SDKs lazy-loaded); `kernel` is zero-framework zero-SDK; `apps/*` depend on everything (composition roots, the only place React/Next lives). **Framework-agnostic core** = `kernel`/`domain`/`adapters`/domain packages all zero React/Next.
- **pnpm `packages/*` glob auto-includes** new packages — no manifest edit, unlike a hand-maintained workspace list.
- **A `CLAUDE.md` in every package** (the layered-context rule applied per directory): the root one is a routing table (hard constraints + where to look); each package's states its responsibility, dependency direction, and local contract (`domain`'s "zero SDK, zero framework", `adapters`' "errors normalize", `kernel`'s "payloads never logged"). The checker requires one per package.

## Navigability

Naming-as-path is to navigation what types are to interface contracts — and the monorepo lifts it to the package level. Group by capability, not by `components/`/`utils/`. Nest until leaf files have a single clear responsibility. A name should resolve to a path with no search.

## Principles for AI-touching code (advisory)

Beyond the type system — for any code where a model produces output. Upper-level discipline; not all mechanically checkable.

- **Constrain, don't ask.** Push non-negotiable properties (no fabrication, must-cite, no privilege escalation) into deterministic control flow so the model *physically cannot* violate them — don't rely on the prompt. Synthesize answers from typed values in code; discard model prose on the critical path.
- **Narrow the emission surface.** Make the model pick from a TypeScript union literal or a Zod `enum`, or call a tool returning a tri-state result (`found`/`not_found`/`unrecognized`); take final values from tool results, not free-form model text. A discriminated union exhaustively `switch`ed is the natural controlled surface.
- **Guardrails are deterministic, independent, never pluggable.** Intent parsing can be swapped; safety decisions are deterministic code re-evaluated from raw input, not trusting a pluggable component's output.

## Driving AI on big work (advisory)

Treat AI as supervisable labor, not unsupervised autopilot.

- **Decision-first: a numbered, immutable ADR (`docs/adr/`) before coding** — context + chosen option + rejected alternatives and why. Rejected-reasons stop it re-walking excluded paths.
- **TDD red-light first; tests are the immutable spec.** Write the failing Vitest test, then implement to green; never weaken a test to pass. Attach the failing test as a subagent's acceptance criteria.
- **Numbered steps, each independently green; one commit per step through the full gate.** No giant diffs.
- **Adversarial independent review.** After writing, run a separate, hostile, multi-perspective review prioritizing what tests can't cover (diagrams, docs, tradeoffs).

## Scale to project size

Scale along **two axes, not one** — size *and* domain. The standard has a **universal spine** that holds for any frontend project whether or not it touches AI: TypeScript `strict` + stricter flags, the zero-warning gate (tsc + eslint + prettier + vitest + build), no silent failures, Zod at boundaries, pnpm + Turborepo package-per-domain + deep naming-as-path, structured logging, Zod-validated env, type-aware ESLint + Prettier. The rest is an **AI-triggered layer** that only switches on once the project actually calls an LLM / embedding / vector store: the `domain` interface seam + zero-SDK domain package, `MockProvider`-as-default, bundled prompts + strict rendering, `logProvenance`, and the constrain-don't-ask discipline. **A pure presentation site / marketing page / dashboard that never calls a model should take the spine in full and skip the AI layer outright** — bolting `MockProvider` or prompt-embedding onto such a project is cargo-culting, not conformance.

On the size axis: this standard's baseline *is* a monorepo, because pnpm + Turborepo cost almost nothing to stand up and the package boundaries pay off immediately. A small project starts as **one app plus a couple of packages** and grows packages as capabilities split out ("split a package out the moment it takes a second responsibility") — the layout is the same, just shallower. The provider seam, ADRs, and drift guards are real overhead; present them as **triggered, scalable patterns** ("the moment you call an LLM/embedding/vector store, put it behind an interface in `domain`"), not blanket mandates.

## Resources

- `references/standard.md` — the full standard with rationale and complete code for every module (read for the why, edge cases, or exact module contents).
- `assets/templates/` — exact boilerplate, mirroring a monorepo layout; `__SCOPE__` is the only placeholder. Includes `packages/{kernel,domain,adapters}`, `apps/{web-vite,web-next}`, `tsconfig.base.json`, `eslint.config.mjs`, `.prettierrc.json`, `turbo.json`, `pnpm-workspace.yaml`, `ci.sh`, a per-package CLAUDE.md, `docs/adr/`, `configs/settings.json`, and smoke/conformance tests.
- `scripts/scaffold.py` — generate a conforming monorepo.
- `scripts/check_conformance.py` — verify structural invariants (incl. `domain`-zero-SDK-and-zero-framework and per-package CLAUDE.md).
