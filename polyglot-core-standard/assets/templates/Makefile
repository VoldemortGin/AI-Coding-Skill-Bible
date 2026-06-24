# __REPO__ — composed polyglot gate (polyglot-core-standard).
# One command judges the whole repo. Completion = `make check` green: every sub-tree's
# own zero-warning gate PLUS binding freshness. The ceiling is the weakest seam, so the
# gate must cross every seam — a host whose gate isn't wired in here is unguarded.
# Toolchains + generator versions are pinned in versions.toml. See CLAUDE.md (routing table).
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

.PHONY: check check-core check-hosts check-apple check-python check-bindings gen-bindings help

check: check-core check-hosts check-bindings ## The only correctness judge: core + hosts + binding freshness
	@echo "✓ composed gate green"

check-core: ## Rust core's own zero-warning gate (rust-project-standard)
	cd core && ./ci.sh

check-hosts: check-apple check-python ## Every host sub-tree's own gate

check-apple: ## Swift host gate (swift-project-standard, spine-only)
	cd apple && ./ci.sh

check-python: ## Python host gate (python-project-standard, spine-only)
	cd python && ./ci.sh

gen-bindings: ## Derive ALL host bindings + type stubs from the core (single source of truth)
	bash scripts/gen_bindings.sh

check-bindings: ## Drift guard: regenerated bindings must equal the committed ones (non-negotiable 5)
	bash scripts/check_bindings.sh

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'
