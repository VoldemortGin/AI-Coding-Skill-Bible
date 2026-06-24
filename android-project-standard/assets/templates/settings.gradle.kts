// Gradle settings:模块注册 + 仓库。
// 唯一占位符:`__APP_ID__`(dotted 基础包名 / applicationId),`__PKG_PATH__`(其 `/` 形式,仅用于目录)。
//
// Gradle 没有 Cargo 的 `members = ["crates/*"]` glob —— 每个 module 必须显式 include。
// 因此 scaffold 把领域 module 注入文件末尾的注入哨兵(模板零领域时始终可构建)。

pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "__APP_ID__"

// 固定的脊柱 module:组合根 + 跨切面 infra + 领域抽象 + 实现。
include(":app")
include(":kernel")
include(":domain")
include(":adapters")
// 领域 feature module 注入区(scaffold 按 --domains 在此追加各领域的 include 行)。
// __DOMAIN_MODULES__
