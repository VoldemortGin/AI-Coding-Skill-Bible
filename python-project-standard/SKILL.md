---
name: python-project-standard
description: >-
  Enforce a strict, type-safe, model-agnostic, AI-navigable Python project standard:
  mypy --strict + beartype runtime type-checking + pydantic at boundaries + provider
  Protocol seams (zero-SDK core) + src layout with a real package name + domain-first
  deep structure + centralized config/logging/prompts + a one-command zero-warning gate
  + drift guards. Use this whenever starting or scaffolding a new Python project, service,
  or package; setting up pyproject/ruff/mypy/pytest; deciding where code, config, or prompts
  belong; adding type checking, runtime validation, or an LLM/embedding/vector-store
  dependency; organizing or deepening package structure; wiring providers; setting up CI or
  pre-commit; or checking that an existing Python project conforms. Apply it even when the
  user only says "start a Python project", "set up the repo", "add types", "wire up an LLM",
  or "structure this", without naming the standard.
---

# Python Project Standard

This skill is the guiding standard for **any** Python work. Apply it by default; don't wait to be asked.

Its spine: **trust is placed not in the model, but in the machine-checkable code that constrains it.** Dynamic Python's signal is too weak — code runs while doing the wrong thing. Tighten the scaffold instead: static types (mypy), runtime types (beartype), behavior (tests), a name-navigable layout, model-agnostic seams, and failing artifacts that mechanize the implicit knowledge a human would otherwise hold in their head. The agent's output ceiling equals the tightness of that feedback loop.

Baseline: **Python 3.13**, mypy `--strict`, ruff, beartype, pydantic v2 + pydantic-settings, Jinja2, Hypothesis. Modern idioms only (no `from __future__ import annotations` — it stringifies all annotations and fights beartype's runtime resolution; quote forward/self references as needed; no `typing.List`, prefer PEP 695 `type`/`class Box[T]`).

## When starting a new project

```bash
python scripts/scaffold.py <package_name> --target <dir> --domains ingestion retrieval generation agents
```

This mirrors `assets/templates/` into a conforming project (src layout, `core/`, `ports/`+`adapters/`, prompts, CLAUDE.md, ADR, `ci.sh`, drift check, smoke/conformance tests) and substitutes `__PACKAGE_NAME__`. When adapting an existing repo, copy from `assets/templates/` by hand — the Python templates use relative imports and `__name__`, so only `pyproject.toml` carries the literal name.

Then: `uv sync` once (editable install), and `./ci.sh` (or `make check`) to verify.

## When working on existing code

Apply the rules below, keep new code strict, and verify structural invariants:

```bash
python scripts/check_conformance.py <project_root>
```

It checks the mechanically enforceable invariants (src layout, real package name, claw hook present, `core/__init__.py` empty, `settings.py` is a leaf, **no vendor SDK imported outside `adapters/`**, mypy strict). Everything else is enforced by the gate and by applying the standard.

## The non-negotiables

Full rationale in `references/standard.md`.

1. **Static: mypy `--strict`, no bare `Any`.** Annotate every parameter and return; parameterize generics; PEP 695 `type` aliases; `# type: ignore` needs a code, a reason, and is tracked debt.

2. **Runtime: beartype via a central switch + claw hook — never hand-applied `@beartype`, never commented out.** Switch is `settings.beartype_on` (default **on**; only production sets `APP_BEARTYPE_ON=false`). Hook at the very top of the package `__init__.py`; `On` strategy when `CI` is set, else `O1`.

3. **beartype import-ordering (top footgun).** The hook only instruments modules imported *after* it, and `sys.modules` caching makes anything loaded before it permanently unchecked. So: before the hook, import only `settings`; `core/settings.py` is a **leaf** (no first-party imports); `core/__init__.py` (and any package on the path from the top `__init__.py` to `settings`) is **empty**. This is automatic for every entry point because importing anything from the package runs `__init__.py` first — *as long as you enter through the package* (`import pkg.X`, `python -m pkg.cli`, console script, `uv run`). Never run a package module as a loose file.

4. **Boundaries: pydantic.** Every value crossing a process boundary (LLM output, tool results, HTTP, files, deserialization) is parsed and validated by a pydantic model at the entry point. Rule: crossing a process boundary → pydantic (validate + coerce); internal contract → beartype.

5. **Model-agnostic: every external AI dependency behind a `ports/` Protocol; SDKs only in `adapters/`.** Core and domain code import zero vendor SDKs (the checker enforces this). One assembly seam (`ports/factory.py`) selects the impl by env; SDKs are lazy-imported inside adapters; vendor errors normalize to `ProviderError` (program errors propagate — never `except Exception` into a fallback). A deterministic **MockProvider is the default** (not a test stub) so the main path runs offline/CI with no SDK or key. A conformance kit binds Mock and real backends to the same invariants.

6. **No silent failures.** beartype violations, Jinja2 `StrictUndefined`, normalized provider errors — all prefer a loud, located failure over silently-wrong behavior. No bare `except`.

7. **Completion = one zero-warning gate, the agent's only correctness judge.** `./ci.sh` runs `ruff format --check` → `ruff check` → `mypy` → `check_drift.py` → `CI=1 pytest` (beartype `On` + smoke + `filterwarnings=["error"]`), `set -euo pipefail`. Run it after every change; fix until green; never "looks fine, commit". Pin it with a pre-push hook.

## Structure: src layout, named package, no rootutils

- **Always src layout** (`src/<name>/`) with a **real package name** from day one (never `import src`). **No `rootutils`/`.project-root`** — install editable (`uv sync`) and `import pkg` works everywhere. Find files via `importlib.resources`/`PackageLoader` (package-shipped) and settings+env (root content).
- **All reusable logic in `src/<pkg>/`**, even if only `scripts/`/`tests/` call it (maximizes beartype coverage). Test-only scaffolding stays in `tests/`.
- **`core/`** = cross-cutting infra: `settings.py` (pydantic-settings, leaf), `paths.py`, `logging.py` (`setup_logging()` once at the entry; library code only `getLogger`; `log_provenance()` + `SENSITIVE_FIELDS` keep payloads out of logs), `prompts.py`.
- **`ports/` + `adapters/`** = the model-agnostic seam (rule 5).
- **`configs/settings.yaml`** merged into `Settings` via `YamlConfigSettingsSource` (typed replacement for Hydra config files). **`prompts/` inside the package**, loaded by `PackageLoader`, shipped in the wheel.

## Navigability: domain-first, names map to locations

Naming-as-path is to navigation what types are to interface contracts. "Fix the reranker" should resolve to `retrieval/reranking/` with no search.

- **Domain-first, not layer-first** (group by capability, not by `models/`/`utils/`). Nest 3–4 levels; leaf modules have real content. A domain package holds `models.py` (its pydantic contracts) + impl + a thin-re-exporting `__init__.py` (post-hook, so re-export is fine and aids navigation). Cross-domain contracts → top-level `schemas/`. See `references/standard.md` §7.9.

## Principles for AI-touching code (advisory)

Beyond types — for any code where a model produces output. These are upper-level discipline; not all mechanically checkable.

- **Constrain, don't ask.** Push non-negotiable properties (no fabrication, must-cite, no privilege escalation) into deterministic control flow so the model *physically cannot* violate them — don't rely on the prompt. Synthesize answers from structured values in code; discard model prose on the critical path.
- **Narrow the emission surface.** Don't let the model freely generate key payloads — make it pick from controlled options or call tools that return tri-state (found/not_found/unrecognized); take final numbers from tool results, not model text.
- **Guardrails are deterministic, independent, never pluggable.** Intent parsing can be swapped; safety decisions are deterministic code re-evaluated from raw input, not trusting a pluggable component's output.

## Driving AI on big work (advisory)

Treat AI as supervisable labor, not unsupervised autopilot. (A heavier version is arguably a sibling skill.)

- **Decision-first: write a numbered, immutable ADR (`docs/adr/`) before coding** — context + chosen option + rejected alternatives and why. AI fills within locked boundaries; rejected-reasons stop it re-walking excluded paths.
- **TDD red-light first; tests are the immutable spec.** Write the failing test, then implement to green; never weaken a test to pass. Attach the failing test as a subagent's acceptance criteria.
- **Numbered steps, each independently green; one commit per step through the full gate.** No giant diffs.
- **Adversarial independent review.** After writing, run a separate, hostile, multi-perspective review ("assume it's wrong; falsify it"), prioritizing artifacts tests can't cover (diagrams, docs, tradeoffs) — the same agent that writes and praises confirms its own bias.

## Scale to project size

The model-agnostic layer, ADRs, and drift guards are real overhead — overkill for a 200-line tool. Present them as **triggered, scalable patterns** ("the moment you call an LLM/embedding/vector store, put it behind a Protocol"; "drill a package down the moment it takes a second responsibility"), not blanket mandates.

## Resources

- `references/standard.md` — the full standard with rationale and complete code for every module (read for the why, edge cases, or exact module contents).
- `assets/templates/` — exact boilerplate, mirroring a project layout; `__PACKAGE_NAME__` is the only placeholder. Includes `ports/`+`adapters/` (model-agnostic seam), `ci.sh`, `CLAUDE.md`, `docs/adr/`, `scripts/check_drift.py`, and smoke/conformance tests.
- `scripts/scaffold.py` — generate a conforming new project.
- `scripts/check_conformance.py` — verify structural invariants (incl. zero-SDK-outside-adapters).
