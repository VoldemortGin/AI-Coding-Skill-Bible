// 根 build:只声明全部插件(`apply false`)—— 各 module 在自己的 plugins{} 块里 apply。
//
// 两个 lint gate 在每个 module 内 apply(ktlint + detekt):那里类型安全访问器(`detekt {}`、
// `libs.*`)可靠;`subprojects { configure<…> }` 里 catalog 访问器跨 Gradle 版本不稳,故不用。
// ktlint 自动读根 .editorconfig(全仓统一格式);detekt 各 module 指向 config/detekt/detekt.yml。
// 编译期严格(allWarningsAsErrors + explicitApi)也在各 module 的 kotlin{} 块(per-module 契约)。

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.hilt) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.detekt) apply false
    alias(libs.plugins.ktlint) apply false
}
