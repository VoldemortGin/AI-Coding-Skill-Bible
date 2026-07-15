# 1. Record architecture decisions

- Status: accepted
- Date: YYYY-MM-DD

## Context
Architecture / product decisions must pin direction before AI writes code, and record *why*
alternatives were rejected so the excluded paths are not re-walked.

## Decision
Every significant decision is a numbered, immutable ADR (context + chosen option + rejected
alternatives and why). AI fills in the implementation within locked boundaries.

## Consequences
Direction is auditable; AI does not make ambiguous trade-offs for us, nor re-walk excluded paths.
