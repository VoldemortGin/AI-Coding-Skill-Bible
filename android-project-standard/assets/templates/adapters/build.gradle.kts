// :adapters —— :domain interface 的具体实现。默认 MockProvider(确定性、离线、无 key、零 SDK)。
// 真实后端(OpenAI 等)放在 gated 的独立 module(如 :adapters-openai),默认 build 不含 —— 见 CLAUDE.md。

plugins {
    alias(libs.plugins.kotlin.jvm)
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
    implementation(project(":domain"))
    implementation(project(":kernel"))

    testImplementation(libs.kotlin.test)
    testImplementation(libs.kotlinx.coroutines.test) // runTest:测 suspend port 契约
}
