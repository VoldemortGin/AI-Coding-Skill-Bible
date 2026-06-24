// :app —— com.android.application:Compose UI + Hilt 组合根。依赖全部 module(组装根)。
// 唯一允许"按 config 选实现"的地方在 di/AppModule.kt(调 :adapters 的 ProviderFactory)。

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
    alias(libs.plugins.detekt)
    alias(libs.plugins.ktlint)
}

android {
    namespace = "__APP_ID__"
    compileSdk = 35

    defaultConfig {
        applicationId = "__APP_ID__"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    jvmToolchain(17)
    compilerOptions {
        allWarningsAsErrors.set(true) // 警告即错误(per-module 契约)
    }
}

detekt {
    buildUponDefaultConfig = true
    config.setFrom(rootProject.files("config/detekt/detekt.yml"))
}

// 生成绑定(UniFFI/JNI)在 polyglot Android host 里通常落在 :app 的 `uniffi/` 包:
// vendored 工件,治理移到手写 bridge,**绝不**进 detekt 源集(polyglot-core-standard 第 4 条)。
// ktlint 侧由根 .editorconfig 的 [**/uniffi/**] / [**/generated/**] 规则排除。
tasks.withType<io.gitlab.arturbosch.detekt.Detekt>().configureEach {
    exclude("**/uniffi/**", "**/generated/**")
}

dependencies {
    implementation(project(":kernel"))
    implementation(project(":domain"))
    implementation(project(":adapters"))
    // 领域 feature module 注入区(scaffold 按 --domains 追加 implementation(project(":<name>")))。
    // __DOMAIN_APP_DEPS__

    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.hilt.navigation.compose)

    debugImplementation(libs.compose.ui.tooling)
    debugImplementation(libs.compose.ui.tooling.preview)
}
