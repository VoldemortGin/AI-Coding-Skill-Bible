# __APP_ID__

按 `android-project-standard` 搭建的 Gradle multi-module 项目骨架:Kotlin 编译器 null-safety + `allWarningsAsErrors` + `explicitApi`、零警告质量门、关死逃生舱(detekt)、kotlinx.serialization + value class newtype 边界、module-per-domain 深结构、零-SDK `:domain` interface 缝 + 默认 `MockProvider`、Hilt 组合根注入、ktlint + detekt 双 lint gate。

## 布局

```
settings.gradle.kts          # 模块注册(Gradle 无 glob,显式 include)
build.gradle.kts             # 根:仅声明插件(apply false);各 module 自行 apply ktlint/detekt
gradle/libs.versions.toml    # version catalog:钉死所有版本
config/detekt/detekt.yml     # detekt:lint + 逃生舱禁令(!!/as/lateinit/GlobalScope = error)
.editorconfig                # ktlint 格式规则
ci.sh  Makefile              # 唯一零警告门
configs/settings.json        # 环境相关结构化配置(非 secret;env 可逐项覆盖)
kernel/      跨切面基础设施(Config / Logging / Prompts + bundled resources);kotlin("jvm"),零 SDK
domain/      interface(ports)+ model(value class newtype)+ sealed 边界错误。零 SDK 零框架
adapters/    interface 实现。默认 MockProvider(离线、无 key、零 SDK)+ ProviderFactory 装配缝
app/         com.android.application:Compose UI + Hilt 组合根(按 config 注入实现)
```

依赖方向(单向):领域 feature / `:adapters` → `:domain` + `:kernel`;`:app` → 全部。`:domain` 绝不依赖 `:adapters` / SDK。

## 跑质量门(完成的唯一判据)

```bash
./gradlew wrapper --gradle-version 8.11.1   # 首次:生成 wrapper(需本机装 gradle)
./ci.sh                                      # ktlint → detekt → 编译(-Werror)→ test
# 或
make check
```

单项:

```bash
make fmt     # ktlintFormat 写回
make lint    # ktlintCheck + detekt
make build   # compileDebugKotlin(allWarningsAsErrors)
make test    # 单元测试(smoke + conformance)
```

## 启用真实 provider

默认完全离线、零 SDK。真实后端(如 OpenAI)放在 **gated 的独立 module**(如 `:adapters-openai`),
只在按 gradle property 开启时 `include`,并在 adapter 内把厂商错误归一到 `ProviderError`。见 `adapters/CLAUDE.md`。

## 与 polyglot-core-standard 的关系

本骨架治理 **Kotlin host 内部**。若本仓是「Rust core + 多语言绑定」的 polyglot 仓:
共享逻辑只在 core;UniFFI/JNI 生成绑定是 vendored 工件(`linguist-generated` / gate-excluded / never-edited);
本 module 的 `./ci.sh` 接入 polyglot 的 `make check-android` 那一格。接缝治理见 polyglot-core-standard。
