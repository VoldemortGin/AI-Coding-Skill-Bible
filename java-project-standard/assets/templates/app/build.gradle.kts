// :app -- the runnable application and manual composition root. Depends on every module. The one
// place implementations are selected by config (Wiring). No DI framework by design; see app/CLAUDE.md
// for when and how to introduce one.

import net.ltgt.gradle.errorprone.errorprone
import net.ltgt.gradle.nullaway.nullaway

plugins {
    application
    alias(libs.plugins.errorprone)
    alias(libs.plugins.nullaway)
    alias(libs.plugins.spotless)
    jacoco
}

application {
    mainClass.set("__PKG__.app.Main")
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

// COVERAGE EXEMPTION: :app is the composition root -- Main.main() and wiring are exercised by
// running the app, not by unit tests, so no coverage floor is enforced here (Wiring still has a
// unit test). Every other module enforces the 80% line-coverage gate. Keep real logic out of :app.

dependencies {
    implementation(project(":kernel"))
    implementation(project(":domain"))
    implementation(project(":adapters"))
    // Domain feature modules are appended here by scaffold.
    // __DOMAIN_APP_DEPS__

    // A concrete SLF4J binding is chosen once, at the composition root (library code only emits).
    runtimeOnly(libs.slf4j.simple)

    errorprone(libs.errorprone.core)
    errorprone(libs.nullaway)
    compileOnly(libs.errorprone.annotations)

    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.platform.launcher)
}
