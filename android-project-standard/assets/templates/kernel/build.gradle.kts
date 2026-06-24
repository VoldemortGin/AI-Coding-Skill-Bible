// :kernel —— 跨切面基础设施:Config / Logging / Prompts。无外部依赖、零 SDK(除语言级序列化)。
// 纯 kotlin("jvm") (非 Android),便于离线单测;Android 行为(如 android.util.Log)由 :app 注入 sink。

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.detekt)
    alias(libs.plugins.ktlint)
}

kotlin {
    explicitApi()
    jvmToolchain(17)
    compilerOptions {
        allWarningsAsErrors.set(true)
    }
}

detekt {
    buildUponDefaultConfig = true
    config.setFrom(rootProject.files("config/detekt/detekt.yml"))
}

dependencies {
    implementation(libs.kotlinx.serialization.json)

    testImplementation(libs.kotlin.test)
}
