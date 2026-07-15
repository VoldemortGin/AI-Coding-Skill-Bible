#!/usr/bin/env bash
# The one zero-warning gate: the single "is it done?" judge shared by humans and agents. Any
# non-zero step fails the whole gate. Ordered fast -> slow:
#   1. format (Spotless / google-java-format)
#   2. compile (-Werror + Error Prone + NullAway -> a warning or a null-safety violation is fatal)
#   3. test (offline, mock default, JUnit 5: smoke + provider conformance)
#   4. coverage floor (JaCoCo verification; >= 80% line coverage on every non-app module)
set -euo pipefail

GRADLE="./gradlew --no-daemon --stacktrace"

# 1. format
$GRADLE spotlessCheck

# 2. compile (all modules; allWarnings + Error Prone + NullAway as errors)
$GRADLE compileJava

# 3. unit tests (offline, mock default, smoke + conformance)
$GRADLE test

# 4. coverage verification (tests are the immutable spec; the floor is in the gate)
$GRADLE jacocoTestCoverageVerification

echo "OK: all green"
