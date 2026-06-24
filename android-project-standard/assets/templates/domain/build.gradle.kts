// :domain —— interface(ports)+ model + 边界错误。**零 SDK / 零框架**(机械检查的不变量)。
// 纯 kotlin("jvm") library(非 Android module),因此可单测离线、可 explicitApi。

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.detekt)
    alias(libs.plugins.ktlint)
}

kotlin {
    explicitApi() // 库 module:公共 API 必须显式 public(否则编译报错)
    jvmToolchain(17)
    compilerOptions {
        allWarningsAsErrors.set(true) // 警告即错误(per-module 契约)
    }
}

// detekt(lint + 逃生舱禁令):指向全仓单一配置;ktlint 自动读根 .editorconfig。
detekt {
    buildUponDefaultConfig = true
    config.setFrom(rootProject.files("config/detekt/detekt.yml"))
}

dependencies {
    // 语言级序列化(serde 的对应物),非厂商 SDK。
    implementation(libs.kotlinx.serialization.json)

    testImplementation(libs.kotlin.test)
}
