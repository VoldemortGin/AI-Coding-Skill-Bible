// :kernel -- cross-cutting infra: Config / Logging / Prompts. Language-level libs only (Jackson =
// serde analog, SLF4J = tracing analog); zero vendor SDK. Pure java-library, offline-testable.
//
// The strict-compile + Error Prone + NullAway + Spotless + JaCoCo block below is per-module by
// design (the Java mirror of Android's per-module detekt/kotlin blocks): typed accessors (`libs.*`,
// `options.errorprone`) are reliable here, and every module carries its own contract, greppably.

import net.ltgt.gradle.errorprone.errorprone
import net.ltgt.gradle.nullaway.nullaway

plugins {
    `java-library`
    alias(libs.plugins.errorprone)
    alias(libs.plugins.nullaway)
    alias(libs.plugins.spotless)
    jacoco
}

// NullAway treats this package tree as @NonNull by default (JSpecify); `@Nullable` is the explicit,
// compiler-checked opt-out. Null becomes a compile error, not a runtime bomb.
nullaway {
    annotatedPackages.add("__PKG__")
}

tasks.withType<JavaCompile>().configureEach {
    // Target Java 21 regardless of the host JDK; -Werror + -Xlint make every warning fatal.
    // -parameters lets Jackson bind JSON to record components by name (no @JsonProperty noise).
    options.release.set(21)
    options.compilerArgs.addAll(listOf("-Werror", "-Xlint:all,-processing,-serial", "-parameters"))
    options.errorprone {
        disableWarningsInGeneratedCode.set(true)
        excludedPaths.set(".*/generated/.*")
        // NullAway as an ERROR: null-safety violations fail the build (the Kotlin null-safety /
        // Swift optional mirror). Escaping a single site: @SuppressWarnings("NullAway") // reason.
        nullaway {
            error()
        }
    }
}

spotless {
    // google-java-format owns formatting (the ktlint / cargo-fmt analog). Chosen over
    // palantir-java-format because only google-java-format's recent releases run on JDK 21..25+.
    java {
        googleJavaFormat(libs.versions.google.java.format.get())
        targetExclude("**/generated/**")
    }
}

// Tests are the immutable spec; coverage is in the gate. JaCoCo verification fails below 80% line
// coverage for this module (the Java mirror of a coverage floor; app is exempt -- see app/).
tasks.named<Test>("test") {
    useJUnitPlatform()
    finalizedBy(tasks.named("jacocoTestReport"))
}

tasks.named<JacocoCoverageVerification>("jacocoTestCoverageVerification") {
    dependsOn(tasks.named("test"))
    violationRules {
        rule {
            limit {
                counter = "LINE"
                minimum = "0.80".toBigDecimal()
            }
        }
    }
}

tasks.named("check") {
    dependsOn(tasks.named("jacocoTestCoverageVerification"))
}

dependencies {
    api(libs.jspecify)
    implementation(libs.jackson.databind)
    implementation(libs.slf4j.api)

    errorprone(libs.errorprone.core)
    errorprone(libs.nullaway)
    compileOnly(libs.errorprone.annotations)

    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.platform.launcher)
}
