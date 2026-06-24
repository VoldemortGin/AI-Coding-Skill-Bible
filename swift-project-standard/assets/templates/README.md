# __PACKAGE__

按 `swift-project-standard` 搭建的 SwiftPM 项目骨架:Swift 6 语言模式 + 严格并发、零警告质量门、关死逃生舱、`Codable` + newtype 边界、target-per-domain 深结构、零-SDK `Domain` protocol 缝 + 默认 `MockProvider`、`os.Logger` 隐私插值、强类型 `AppConfig`、swift-format + SwiftLint 双门。

## 布局

```
Sources/
  Kernel/      跨切面基础设施(Config / Logging / Prompts + bundled resources)
  Domain/      ports(protocols)+ models(newtype/Codable)+ 边界错误。零 SDK 依赖
  Adapters/    protocol 实现。默认 MockProvider(离线、无 key、零 SDK)
  Retrieval/   示例领域:向量检索(注入 any Embedder)
  Generation/  示例领域:RAG 生成(注入 any LLM + 严格提示词)
  App/         composition root(main.swift):按 config 选 provider、注入、跑 demo
Tests/
  SmokeTests/        无 key 也能跑绿:Mock 默认主链路
  ConformanceTests/  所有 provider 实现绑同一组行为不变量
```

依赖方向:领域 target → `Domain` + `Kernel`;`Adapters` → `Domain` + `Kernel`;`App` → 全部。`Domain` 零 SDK。

## 跑质量门(完成的唯一判据)

```bash
./ci.sh            # 格式 → lint → 构建(警告即错误)→ 测试
# 或
make check
```

单项:

```bash
make fmt           # swift format 写回
make lint          # swift format lint --strict + swiftlint --strict
make build         # swift build -Xswiftc -warnings-as-errors
make test          # swift test(smoke + conformance)
make run           # 跑 CLI demo
```

前置:`brew install swiftlint`(swift-format 随工具链自带,命令 `swift format`)。

## 启用真实 provider

默认完全离线、零 SDK。真实后端用 package trait `RealProviders` 门控:

```bash
swift build --traits RealProviders
```

并按 `Package.swift` 与 `Sources/Adapters/CLAUDE.md` 的注释解开 SDK 依赖、添加 `#if RealProviders` 包裹的 adapter(错误归一到 `ProviderError`)。

## 生成 Xcode app 壳

```bash
brew install xcodegen
make scaffold-xcode    # 用 project.yml 生成 __PACKAGE__App.xcodeproj(link AppCore)
make app               # 生成并打开
```

app target 只做 UI + 组装;领域逻辑全在 package 的 `AppCore` 库。
