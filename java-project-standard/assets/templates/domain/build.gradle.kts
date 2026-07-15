// :domain -- ports (interfaces) + models (records) + sealed boundary errors. ZERO vendor SDK /
// ZERO framework (a mechanically-checked invariant). Pure java-library: offline-testable, the one
// module every feature and adapter depends on, and which itself depends on nobody but jspecify.

import net.ltgt.gradle.errorprone.errorprone
import net.ltgt.gradle.nullaway.nullaway

plugins {
    `java-library`
    alias(libs.plugins.errorprone)
    alias(libs.plugins.nullaway)
    alias(libs.plugins.spotless)
    jacoco
}

nullaway {
    annotatedPackages.add("__PKG__")
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(21)
    options.compilerArgs.addAll(listOf("-Werror", "-Xlint:all,-processing,-serial", "-parameters"))
    options.errorprone {
        disableWarningsInGeneratedCode.set(true)
        excludedPaths.set(".*/generated/.*")
        nullaway {
            error()
        }
    }
}

spotless {
    java {
        googleJavaFormat(libs.versions.google.java.format.get())
        targetExclude("**/generated/**")
    }
}

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
    // jspecify supplies @Nullable only; no vendor SDK, no framework. The checker enforces this.
    api(libs.jspecify)

    errorprone(libs.errorprone.core)
    errorprone(libs.nullaway)
    compileOnly(libs.errorprone.annotations)

    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.platform.launcher)
}
