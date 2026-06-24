#!/usr/bin/env bash
# apple/ gate — the Swift host's own zero-warning gate; the composed repo gate
# (`make check-apple`) calls this. FAITHFUL MINIMAL version; see swift-project-standard for the
# FULL gate (xcodebuild warnings-as-errors, complete strict concurrency, smoke + conformance).
#
# SEAM RULE (non-negotiable 4): lint/format target `Sources` ONLY. `Generated/` is a vendored
# UniFFI artifact — excluded here, in .swiftlint.yml (`excluded:`), via Generated/.swift-format-ignore,
# and as `linguist-generated` in ../.gitattributes. Its `try!`/`as!` are generator output, not ours.
set -euo pipefail

swift format lint --strict --recursive Sources   # Generated/ deliberately not passed
swiftlint --strict                               # .swiftlint.yml excludes Generated/
# Build/test with warnings-as-errors once a Package.swift / .xcodeproj exists (per the host's
# own swift-project-standard scaffold), e.g.:
# swift build -Xswiftc -warnings-as-errors && swift test
echo "✓ apple gate green"
