// Root build: declare the shared plugins as `apply false` -- each module applies and configures them
// in its own `plugins {}` / `tasks` block (typed accessors are reliable there; a root `subprojects {}`
// makes `libs.*` and the errorprone/nullaway DSL flaky across Gradle versions). Strict compilation
// (-Werror + Error Prone + NullAway), Spotless, and the JaCoCo floor are all per-module contracts.

plugins {
    alias(libs.plugins.errorprone) apply false
    alias(libs.plugins.nullaway) apply false
    alias(libs.plugins.spotless) apply false
}
