.PHONY: check fmt lint build test coverage wrapper clean help

# Completion judge: one gate green.
check:
	./ci.sh

# Format in place (write back).
fmt:
	./gradlew --no-daemon spotlessApply

# Lint only (format check + strict compile with Error Prone + NullAway).
lint:
	./gradlew --no-daemon spotlessCheck compileJava

# Compile (warnings-as-errors; all modules).
build:
	./gradlew --no-daemon compileJava

# All unit tests (offline, mock default).
test:
	./gradlew --no-daemon test

# Coverage floor (JaCoCo verification; >= 80% line coverage per non-app module).
coverage:
	./gradlew --no-daemon jacocoTestCoverageVerification

# Generate the Gradle wrapper (first time; needs a system gradle installed).
# Gradle 9.x is required to run on JDK 25 (and to support the pinned plugins).
wrapper:
	gradle wrapper --gradle-version 9.4.1

clean:
	./gradlew --no-daemon clean

help:
	@grep -E '^[a-zA-Z_-]+:.*' $(MAKEFILE_LIST) | grep -v '@grep' | awk 'BEGIN{FS=":"}{printf "  \033[36m%-10s\033[0m\n",$$1}'
