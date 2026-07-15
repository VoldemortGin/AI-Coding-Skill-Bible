// Gradle settings: module registration + repositories.
// The base package fills in below; source directories use its slash form.
//
// Gradle has no Cargo-style `members = ["*"]` glob -- every module must be `include`d explicitly.
// Scaffold appends domain feature modules at the sentinel below (the template builds with zero).

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        mavenCentral()
    }
}

rootProject.name = "__PKG__"

// Fixed spine modules: composition root + cross-cutting infra + domain abstractions + impls.
include(":app")
include(":kernel")
include(":domain")
include(":adapters")
// Domain feature module injection point (scaffold appends `include(":<name>")` per --domains).
// __DOMAIN_MODULES__

// Real-backend adapters live in a gated module, off by default (the Cargo-feature / SPM-trait
// analog): a fully offline build never references it. Create :adapters-openai and set
// `-PrealProviders` to enable it.
if (providers.gradleProperty("realProviders").isPresent) {
    include(":adapters-openai")
}
