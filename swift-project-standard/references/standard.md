# Swift 项目标准(完整版)

面向 AI 主导开发的 Swift 工程标准。与 Python / Rust 姊妹标准同一条脊:**信任放在可被机器检验的代码上,而非模型。** Swift 与 Rust 最像:静态保证大半由编译器免费提供(类型、可选性、穷尽性,以及 Swift 6 起的编译期 data-race 安全),编译期强制、无类型擦除,所以**不需要外挂运行时类型检查**(Python 姊妹标准的 beartype 在这里是多余的)。本标准的重点是:把少数逃生舱关上、打开 Swift 6 严格并发、把每个外部依赖推到 protocol 后面、结构尽量深且命名即定位、并把人类的隐性兜底外化成会失败的工件。

> **定位**:本标准是**项目级工程标准(总纲 + 工程门 + 架构约定)**。"实现层怎么写"——并发、错误处理、协议设计、数据流、测试、网络、持久化——委托引用已有的 swift-* skill(`swift-concurrency` / `swift-error-handling` / `swift-protocols` / `swift-data-flow` / `swift-testing` / `swift-networking` / `swift-persistence` 等),本文在相关处指引"详见 …",不重写其内容。

**适用范围(分两层)**:下列约束分为**通用脊**与**AI 触发层**。

- **通用脊**(任何 Swift 项目都适用,与是否碰 AI 无关):Swift 6 语言模式 + 严格并发(complete)+ warnings-as-errors、零警告门、`throws`/typed throws(关死 `!`/`try!`/`as!`)、`Codable`+newtype 边界、SPM target-per-domain + 深命名、`os.Logger`、强类型 `AppConfig`、swift-format + SwiftLint 双门。
- **AI 触发层**(只在项目真的调用 LLM/embedding/向量库时启用):`Domain` protocol 缝 + 零-SDK domain target、`MockProvider` 作默认、bundled prompts + 严格渲染、`logProvenance`、约束下沉控制流。

不碰模型的库/CLI/app 应全量采用通用脊、整层跳过 AI 层;在那种项目里硬套 `MockProvider` 或提示词嵌入是 cargo-cult,不是合规。

基线:Swift 6.x、`// swift-tools-version: 6.0`(或更高)+ `swiftLanguageModes: [.v6]`、严格并发 complete、门禁 warnings-as-errors、`swift-format`(工具链自带)、`SwiftLint`(社区,`--strict`)、`Codable` + newtype、`os.Logger`、Codable `AppConfig`、`XcodeGen`(有 UI 时生成瘦 app 壳)。

---

## 1. 唯一的零警告门(完成的唯一判据)

`ci.sh` 一条 `set -euo pipefail` 脚本,人和 agent 共用,按"快→慢"排:

```bash
#!/usr/bin/env bash
set -euo pipefail
# 1. 格式(swift-format,工具链自带)
swift format lint --strict --recursive Sources Tests
# 2. lint(SwiftLint,管逃生舱禁令)
swiftlint --strict
# 3. 构建(警告即错误)
swift build -Xswiftc -warnings-as-errors
# 4. 测试(离线、Mock 默认、含 smoke + conformance)
swift test
# 5.(app 场景,存在 .xcodeproj 时)
# xcodebuild -scheme <App> -destination 'platform=iOS Simulator,name=iPhone 16' \
#   build test SWIFT_TREAT_WARNINGS_AS_ERRORS=YES SWIFT_STRICT_CONCURRENCY=complete
```

任一项非零即没完成。`-Xswiftc -warnings-as-errors` 是关键:它把警告一律提升为 error,且加在门禁层(不污染 `Package.swift`、对依赖友好)。如果实测某 6.x 版本支持 `SwiftSetting.treatAllWarnings(as: .error)`,可在 manifest 的库 target 里加一层;但门禁这条始终是强制点。用 pre-push hook 钉死;CI 镜像同一套。`swift format` 随工具链出厂;`swiftlint` 需 `brew install swiftlint` 一次(未装时门禁应说明并跳过 SwiftLint 步)。

## 2. 静态保证:编译器 + Swift 6 严格并发,逃生舱关死

不需要 mypy/beartype 那种外挂——Swift 类型在编译期强制,无类型擦除。"最严、无逃生舱"用原生方式表达。

**打开 Swift 6 语言模式 + 严格并发(complete)。** 在 `Package.swift`:

```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "__PACKAGE__",
    targets: [
        .target(name: "Domain", swiftSettings: [.swiftLanguageMode(.v6)]),
        // …其余 target 同样 .swiftLanguageMode(.v6)
    ],
    swiftLanguageModes: [.v6]   // 整包默认 v6:complete 严格并发即默认开启
)
```

Swift 6 语言模式默认即 complete 严格并发——编译期 data-race 安全,这是 Rust `Send`/`Sync` 的对应物:跨并发域传递的类型必须 `Sendable`,可变共享状态必须用 actor 隔离,编译器替你证明无数据竞争。(降级兼容场景可在库 target 显式 `swiftSettings: [.enableUpcomingFeature("StrictConcurrency")]`,但本标准以 v6 语言模式为准。并发实现细节详见 `swift-concurrency`。)

**逃生舱一律关死**,这是"无逃生舱"的字面实现:

- **`!` 强解包** —— 禁。用 `guard let` / `if let` / `??` 显式处理 nil。
- **`try!`** —— 禁。用 `try` 传播或 `do/catch` 处理。
- **`as!` 强转** —— 禁。用 `as?` + 处理失败分支。
- **隐式解包可选(`var x: T!`)** —— 禁(除 IBOutlet 等框架强制处)。
- **`@unchecked Sendable`** —— 禁(它绕过编译器的并发证明,等于自己打包票)。

SwiftLint 把前三者钉死(`force_unwrapping` / `force_try` / `force_cast`,见 §6 配置)。

**受控出口**:个别站点确需逃生(如已 `precondition` 过的不变量、框架契约),不在全局松绑,而是**逐处显式豁免并写理由**:

```swift
// swiftlint:disable:next force_unwrapping — URL 字面量在编译期已知合法,失败即编译期 bug
let url = URL(string: "https://api.example.com")!
```

这是 Python `# type: ignore[code] # 原因` / Rust `#[allow(clippy::...)] // 原因` 的 Swift 等价物:不是禁止,是让每次逃生**显式、可审计、可 grep**。

`@unchecked Sendable` / `nonisolated(unsafe)` 的受控用法同理:确需(包了一个自己保证线程安全的旧类型、或一个全局 `let` 常量)时,加 `// SAFETY: …` 说明为何手动保证成立,并在该 target 的 CLAUDE.md 记一笔。引入这类绕过由此成为一次显式、隔离、可审计的决策;其余代码仍靠编译器证明并发安全,`check_conformance` 仍绿。

## 3. 不静默失败:`throws` + typed throws + 具体 `Error`

对照 Rust 的 `Result<T, E>` + `thiserror`:Swift 用 `throws` + Swift 6 的 typed throws(`throws(E)`)+ 具体 `Error` enum 表达同一套"错误是签名的一部分、不能静默吞掉"。

- 可恢复错误用 `throws`。Swift 6 的 **typed throws** 把错误集合写进签名,是 Rust `Result<T, E>` 的对应:

```swift
public enum ProviderError: Error, Sendable {
    case unavailable(String)
    case decoding(String)
    case rateLimited
}

// typed throws:错误类型是签名的一部分,调用方 catch 时拿到精确类型
public protocol LLM: Sendable {
    func complete(_ prompt: String) async throws(ProviderError) -> String
}
```

- **禁 `!`/`try!` 当错误处理**(§2);要么 `try` 传播,要么 `do/catch` 具体处理。
- **厂商错在 adapter 边界归一**到 `ProviderError`(网络/超时/API/解码);**程序 bug**(逻辑错、违反不变量)照常 `precondition`/trap 或上抛,**绝不**塞进降级路径吞掉。这与 Python"程序错照常上抛、外部错归一"、Rust"程序 bug panic、外部错归一 `ProviderError`"一致。
- 测试里的断言失败由测试框架报告,不算"静默失败"。

> 错误处理的实现细节(typed throws 何时用、`Result` vs `throws`、错误传播链、`Task` 取消)详见 `swift-error-handling`。

## 4. 边界:parse, don't validate —— `Codable` + newtype

每个跨边界的值(配置、LLM 输出、工具结果、文件、反序列化)在入口处用 `Codable` 解码成强类型值;**把约束编码进类型,让非法状态不可表示**,而非运行时 if 校验。

```swift
/// newtype:构造时即保证 1...100,之后类型本身就是"已校验"的证明。
public struct TopK: Codable, Sendable, Equatable {
    public let value: Int

    public init(_ value: Int) throws {
        guard (1...100).contains(value) else {
            throw DomainError.outOfRange("top_k 越界: \(value)")
        }
        self.value = value
    }

    // 解码即走校验 init:非法 JSON 在边界就 throw,不会渗进领域逻辑
    public init(from decoder: any Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(Int.self)
        try self.init(raw)
    }
}
```

这是 Python 用 pydantic、Rust 用 `serde` + newtype 在边界校验的 Swift 对应:pydantic 运行时校验并强转,Rust 用 `serde` + newtype,Swift 用 `Codable` + 带校验 `init` 把"已校验"变成编译期可携带的类型证明——下游函数签名收 `TopK` 就不必再防御性检查。需要"可失败但不抛"时用 failable `init?`;需要带原因时用 `init(_:) throws`。

## 5. 配置:分层强类型 `AppConfig`

`Kernel/Config.swift`:一个 `AppConfig: Codable & Sendable` + 分层加载器。优先级从低到高:**默认值 < 根级 `configs/settings.json` < 环境变量(`APP_` 前缀,`__` 分隔嵌套)**。非法配置在加载时报错,不拖到运行期。这是 pydantic-settings / figment 的 Swift 对应(分层来源 + env 覆盖 + 强类型)。

```swift
import Foundation

public struct RetrieverConfig: Codable, Sendable {
    public var topK: Int = 5
    public var rerankModel: String = "cohere/rerank-v4.0-fast"
}

public struct AppConfig: Codable, Sendable {
    public var isDebug: Bool = false
    public var retriever: RetrieverConfig = .init()

    /// 默认 < configs/settings.json < 环境变量 APP_*(__ 分隔嵌套)
    public static func load(
        settingsURL: URL? = nil,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) throws -> AppConfig {
        var config = AppConfig()                       // 1. 默认
        if let url = settingsURL, let data = try? Data(contentsOf: url) {
            config = try JSONDecoder().decode(AppConfig.self, from: data)  // 2. 文件
        }
        config.applyEnvironmentOverrides(environment)  // 3. 环境变量(APP_RETRIEVER__TOP_K=20 覆盖嵌套字段)
        return config
    }
}
```

`APP_RETRIEVER__TOP_K=20` 覆盖 `config.retriever.topK`。`AppConfig: Sendable` 让它能安全跨并发域传递。**进阶可选**:重度配置场景可引入 Apple `swift-configuration`(分层 provider、热加载、密钥源),但默认这套零依赖的 Codable 分层加载器已足够,不引第三方。

## 6. 日志/血缘/隐私:`os.Logger`,载荷不落盘

`Kernel/Logging.swift`,以 `os.Logger` 为统一日志。`os.Logger` 的 **privacy 插值原生实现"隐私不落盘"**——这是它优于 swift-log 的关键:

```swift
#if canImport(os)
import os

public enum Log {
    public static let kernel = Logger(subsystem: subsystem, category: "kernel")
    public static func make(category: String) -> Logger {
        Logger(subsystem: subsystem, category: category)
    }
    private static let subsystem = Bundle.main.bundleIdentifier ?? "__PACKAGE__"
}

/// 血缘:每条 AI 产物带来源 + 产出它的实现/版本号,多实现可并存可审计。
public func logProvenance(source: String, impl: String, version: String, count: Int) {
    // 码值/计数/耗时用 .public(可见、可聚合);载荷绝不在这里出现
    Log.make(category: "provenance").info(
        "provenance source=\(source, privacy: .public) impl=\(impl, privacy: .public) version=\(version, privacy: .public) count=\(count, privacy: .public)"
    )
}
#else
// 非 Apple 平台回退(Linux 等):最小 print 实现,或引 swift-log 作进阶可选
#endif
```

纪律:

- **隐私**:payload(答案、原文、向量值、用户输入)一律 `\(x, privacy: .private)`,**绝不**用 `.public`;码值/计数/耗时/枚举码用 `.public`。`os.Logger` 的 privacy 插值让"隐私不落盘"由日志框架在系统层强制,而不是靠人记得脱敏。把这条写进 `Kernel` 的 CLAUDE.md 当硬纪律。
- **库代码只取 logger 发事件**(`Log.make(category:)`),不在库里配置日志后端。
- **`#if canImport(os)` 回退**:非 Apple 平台没有 `os`,回退到 `print` 或引 `swift-log` 作进阶可选(swift-log 的 `Logger.MetadataValue` 区分 `.public`/`.private` 不如 os 原生,故 Apple 平台优先 `os.Logger`)。

> 血缘进、隐私出 —— 与 §10 的"约束下沉"配套。

## 7. 提示词:`Bundle.module` + 严格渲染

提示词放 `Sources/Kernel/Resources/Prompts/<domain>/*.md`,在 `Package.swift` 的 `Kernel` target 声明 `resources: [.copy("Resources/Prompts")]`(或 `.process`),用 **`Bundle.module`** 加载——SPM 自动生成 `Bundle.module` 指向该 target 的资源,dev 与发布行为一致,无运行时路径问题。

```swift
public enum PromptError: Error, Sendable {
    case notFound(String)
    case missingVariable(String)   // 缺变量直接报错,对应 Python StrictUndefined
}

public func renderPrompt(_ name: String, variables: [String: String]) throws -> String {
    guard let url = Bundle.module.url(forResource: name, withExtension: "md", subdirectory: "Prompts"),
          let template = try? String(contentsOf: url, encoding: .utf8) else {
        throw PromptError.notFound(name)
    }
    return try strictRender(template, variables: variables)  // 缺变量 throw missingVariable
}
```

**严格渲染**:模板里出现但 `variables` 没提供的占位符,**直接 throw `PromptError.missingVariable`**,而非静默替成空串——对应 Python Jinja2 的 `StrictUndefined`、Rust minijinja 的 `UndefinedBehavior::Strict`,契合"不静默失败"。调用方用 `try` 传播,不 `try!`(以过门)。**进阶可选**:需要循环/条件等模板逻辑时引 `Stencil`(Swift 的 Jinja 同类);默认这套占位符替换 + 缺变量报错已覆盖多数提示词场景。

提示词从此随包出厂(进 `Bundle.module`),改提示词 = 改仓库 + 重新构建(更规范);运行时热换提示词是另一层功能(外部提示词存储),不在此。

## 8. 结构:深 SPM package,target-per-domain

深度来自**package**(多 target),不是一个 target 里堆深文件夹。SPM target ≈ Cargo crate:target 级依赖隔离 + 可解析的 `Package.swift`。"修 reranker"应定位到 `Sources/Retrieval/...`,无需搜索。

```
repo/
├── Package.swift              # SPM,tools 6.0,v6 语言模式,traits,products,targets,resources
├── .swift-format  .swiftlint.yml  .gitignore  .env.example
├── ci.sh  Makefile  project.yml    # project.yml = XcodeGen 瘦 app 壳
├── README.md  CLAUDE.md            # 根级路由表
├── docs/adr/
├── configs/
│   └── settings.json               # 环境相关结构化配置(非 secret;env 可逐项覆盖)
├── Sources/
│   ├── Kernel/                     # 跨切面:Config / Logging / Prompts(+ CLAUDE.md + Resources/Prompts/)
│   ├── Domain/                     # Ports(protocols)+ Models + Errors,零 SDK(+ CLAUDE.md)
│   ├── Adapters/                   # protocol 实现;MockProvider 默认,真实 SDK trait 门控(+ CLAUDE.md)
│   ├── Retrieval/                  # 示例领域 target(+ CLAUDE.md)
│   ├── Generation/                 # 示例领域 target(+ CLAUDE.md)
│   └── App/                        # 可执行 + 组装根(+ CLAUDE.md)
│       └── main.swift
└── Tests/
    ├── SmokeTests/                 # 无 key 也能跑绿(Mock 默认主链路)
    └── ConformanceTests/           # 所有 provider 实现绑同一组行为不变量
```

要点:

- **target 命名避开 std**:基础设施 target 叫 `Kernel` 不叫 `Core`。`Kernel`/`Domain`/`Adapters`/领域名都**与项目名无关**——`import Kernel` 这类路径不依赖包名;只有 `Package.swift` 的包名、可执行名、CLAUDE.md 标题用到 `__PACKAGE__`(唯一占位符)。
- **依赖方向**:领域 target → `Domain`(ports)+ `Kernel`,**不**依赖 `Adapters` 或 SDK;`Adapters` → `Domain` + `Kernel`(实现其协议);`App` → 全部(组装根)。`Domain` 零 SDK(机械可查的不变量)。
- **products**:
  - `.executable(name: "__PACKAGE__", targets: ["App"])` —— CLI / 纯 SPM 运行入口。
  - `.library(name: "AppCore", targets: ["Kernel", "Domain", "Adapters", <domains...>])` —— 供 Xcode app 壳 import 并自行组装。
- **依赖注入在组装根**:`App/main.swift` 按 `config` 选具体 adapter(默认 Mock),以 `any LLM` 注入下游。这是 Swift 惯用的 DI(构造在边缘、协议存在类型向下传),对应 Python 的 `ports/factory.py`、Rust 的 `app` 组装根 `match`。`any LLM` 是 Rust `Box<dyn Llm>` 的对应。

### 8.1 每个 target 一个 CLAUDE.md(分层上下文)

把"分层上下文"落到目录:根 `CLAUDE.md` 是**路由表**(只放硬约束 + 去哪找),每个 target 目录的 `CLAUDE.md` 写本 target 的职责、依赖方向、本地契约(如 `Domain` 的"零 SDK"、`Adapters` 的"错误归一"、`Kernel` 的"载荷不落盘")。`check_conformance.py` 要求每个 `Sources/<Target>` 都有。好处:agent 进到某 target 工作时,就近拿到的是这一层的精确约束,而非读一份大文档被噪声稀释。

### 8.2 可导航性

命名即路径,是导航层面的"类型即接口契约";SPM 把它提到 target 级。按能力分(不按 `Models/`/`Utils/` 分),一直拆到叶子文件只剩单一职责。深结构 + 一致命名,让"哪段代码在哪"无需搜索。

## 9. 模型无关:provider 协议缝 + 零-SDK 的 Domain

模型是可热插拔的商品。把正确性、可测性、可审计性从具体模型里抽出来,钉在 protocol 与确定性代码上。

- **每个外部依赖 = `Domain` 里一个最小 protocol**(`LLM`/`Embedder`/`Reranker`/向量库/解析器),且 `: Sendable`。领域逻辑只依赖 protocol。让 protocol **保持可被 `any` 存在类型擦除**(避免 `Self` 返回与 `associatedtype` 阻碍 `any` 的方法,或在确需泛型时用 protocol witness 结构体)。

```swift
// Domain/Ports.swift —— 零 SDK
public protocol LLM: Sendable {
    func complete(_ prompt: String) async throws(ProviderError) -> String
}

public protocol Embedder: Sendable {
    func embed(_ texts: [String]) async throws(ProviderError) -> [[Float]]
}
```

```swift
// Adapters/MockProvider.swift —— 默认实现:确定性、离线、无需 key、零 SDK
public struct MockLLM: LLM {
    public init() {}
    public func complete(_ prompt: String) async throws(ProviderError) -> String {
        "mock-answer(\(prompt.count))"               // 确定性:同输入同输出
    }
}

public struct MockEmbedder: Embedder {
    public init() {}
    public func embed(_ texts: [String]) async throws(ProviderError) -> [[Float]] {
        texts.map { [Float($0.count), 0, 0] }        // 确定性、数量保持
    }
}
```

- **`Domain` target 零厂商 SDK 依赖**:机械可查的不变量——`check_conformance.py` 用 `swift package dump-package` 出 JSON 解析 `Domain` 的依赖,与 SDK 黑名单取交集即报错。比 grep import 更干净:SPM 让依赖按 target 显式声明。
- **真实 SDK 在 trait 门控的独立 target**:用 SPM **package traits**(Cargo features 的精确对应)。真实后端如 `AdaptersOpenAI` 是一个独立 target,依赖 SDK,由 trait 门控:

```swift
// Package.swift(节选):package traits 门控真实后端,默认 build/test 完全离线、不拉 SDK
let package = Package(
    name: "__PACKAGE__",
    traits: [.trait(name: "RealProviders")],            // 默认不启用
    dependencies: [
        // 仅当 RealProviders 启用时才解析 SDK 依赖
        // .package(url: "https://github.com/...", from: "x.y.z"),
    ],
    targets: [
        .target(
            name: "AdaptersOpenAI",
            dependencies: [
                "Domain", "Kernel",
                // .product(name: "OpenAISDK", package: "...", condition: .when(traits: ["RealProviders"])),
            ]
        )
    ]
)
```

这是 Python"厂商包进可选 extras + lazy import"、Rust"`optional` 依赖 + feature 门控"的 Swift 对应:trait 未启用时,整段 SDK 依赖排除出解析,默认离线。

- **厂商错归一**:真实 adapter 内把 SDK 错误 `map` 成 `ProviderError`,程序错照常上抛:

```swift
// AdaptersOpenAI/OpenAIProvider.swift(真实后端写法示意)
public struct OpenAIProvider: LLM {
    public func complete(_ prompt: String) async throws(ProviderError) -> String {
        do {
            return try await sdkCall(prompt)          // 调真实 SDK
        } catch let error as SDKError {
            throw ProviderError.unavailable(error.localizedDescription)  // 边界归一
        }
        // 程序 bug(违反不变量)不在此 catch,照常上抛
    }
}
```

- **MockProvider 作默认**(不是测试桩):可执行、测试、CI 默认走 Mock,跑得快、稳、免费、不被随机性污染。"无 key 也能 demo/test 跑绿"设成硬验收(`Tests/SmokeTests`)。
- **一致性契约(conformance kit,`Tests/ConformanceTests`)**:任何号称实现了某 protocol 的类型(Mock 与真实后端)都跑同一组行为不变量——可插拔只在所有实现行为一致时才安全:

```swift
import Testing
@testable import Adapters

func assertEmbedderContract(_ embedder: some Embedder) async throws {
    let texts = ["a", "b"]
    let first = try await embedder.embed(texts)
    let second = try await embedder.embed(texts)
    #expect(first == second)            // 确定性
    #expect(first.count == texts.count) // 数量保持
}

@Test func mockObeysContract() async throws {
    try await assertEmbedderContract(MockEmbedder())
}
// 真实后端在启用 RealProviders trait / 有 key 时加一个 @Test 复用同一函数。
```

> **`any` vs `some` 与 protocol witness 的取舍**:领域逻辑需要在运行时按 config 选实现、或装异构集合时用 `any LLM`(存在类型,动态派发,对应 `Box<dyn>`);编译期单一具体类型、追求静态派发性能时用 `some LLM`(不透明类型)。协议带 `associatedtype` / `Self` 约束而又必须存在化时,用 protocol witness 结构体(把方法包成存值闭包)绕过。这套取舍详见 `swift-protocols`,本标准只规定"缝在 `Domain`、默认 Mock、零 SDK"这一架构约束。

## 10. 让 AI 输出可信:约束下沉控制流,而非写进 Prompt

Prompt 是软约束,温度/越狱/长上下文都能绕过;只有沉到代码的约束才从"概率性遵守"变成"结构上不可能违反"。本节偏原则(不像结构那样能完全机械检验),但对 AI-touching 代码是上位纪律。

- **Constrain, don't ask**:对不可妥协属性(不编造、必引用、不越权),让模型物理上无法违反——命中事实时答案由代码从结构化值确定性合成、模型散文整段丢弃;无事实时编排层改写成"查不到"。迁移:列"绝不能发生"清单,逐条问"模型能否在听话的同时仍违反它",凡"能"的就移出模型。
- **收窄发射面**:不让模型自由生成关键载荷——让它从一个 **Swift `enum`**(带 associated value、`@frozen` 时穷尽匹配)里选、或调返回三态(`case found`/`notFound`/`unrecognized`)的工具,最终值取自工具结果而非模型文本。Swift 的 `enum` + 穷尽 `switch` 天然就是受控发射面,且编译器保证你处理了每个 case。
- **安全门确定性、独立、永不可插拔**:理解类(意图解析)可替换;安全决策(越权/敏感隔离)做成确定性代码,从原始输入独立重判,不信任可插拔组件的输出。可替换的是智能,不是护栏。
- **血缘进、隐私出**:见 §6(`logProvenance` + `.private`/`.public` 纪律)。

## 11. 把隐性兜底外化成会失败的工件

人靠经验、记忆判断"做完没""文档过时没";agent 没有这些,只优化能观测到的反馈。每加一个会失败的检查,就把一份隐性知识变成 agent 无法悄悄绕过的硬约束。

- **加宽的零警告门**(§1):swift-format `--strict` + SwiftLint `--strict` + build(`-warnings-as-errors`)+ test(smoke + conformance);app 场景加 `xcodebuild`(严格并发 + warnings-as-errors)。任一项非零即没完成。人和 agent 共用同一条判据,用 pre-push hook 钉死。
- **漂移守卫**:描述代码的 markdown 带 `covers:` 元数据,被覆盖的路径失效即红(可移植 Python 标准的 `check_drift.py`)。Swift 这边还有两道天然反漂移:DocC 文档构建会校验符号链接;`@Test` / XCTest 把"文档/README 里的代码示例"做成会编译运行的测试,文档骗不了人。
- **自描述工件从真实代码派生**:架构/依赖图从 `swift package dump-package`(manifest JSON)/ `swift package show-dependencies`(依赖图)内省派生,而非手画;手维护的图必然腐烂,腐烂的图比没有更危险——会自信地误导后续 agent。
- **分层上下文**(§8.1):根路由表 + 每 target 就近契约,而非一份大文档读到底。上下文窗口稀缺,"什么都塞"稀释信号。

## 12. 驾驭 AI 做大工作:可拆分、可逐步验证、可对抗审查

把 AI 当可监督的劳力,而非无监督自动驾驶。这是工作流层(可作另一个姊妹技能),轻量版规则:

- **先决策再编码(ADR,`docs/adr/`)**:架构/产品决策写成编号、不可变的 ADR(背景 + 选定 + 被否决备选及理由)。AI 最擅长明确约束下填实现,最不可靠的是替你做含糊取舍;否决理由还防它重走已排除的路。
- **TDD 红灯先行,测试即不可动摇的规格**:每个改动先写会失败的测试(Swift Testing `@Test` 或 XCTest),再实现到绿,**绝不**为通过而弱化测试;给 subagent 的任务直接附失败测试当验收。测试写法详见 `swift-testing`。
- **拆成编号步骤、每步独立绿灯**:大重构拆有序步骤,每步一次提交、跑完整门禁再进入下一步,绝不攒巨型 diff——把失败爆炸半径压到一步之内。
- **分解→并行→综合**:主 agent 拆边界清晰、规格完整的子任务并行分派,逐个审 diff 并在提交前过门。
- **对抗式独立复审**:写完后另起独立、带敌意的多视角复审("假设它有错,去证伪"),优先审测试盖不到的产物(图、文档、取舍)——同一 agent 既写又夸会系统性确认偏差。

---

## 附:Python / Rust 姊妹标准的映射速查

| 关注点 | Python 标准 | Rust 标准 | Swift 标准 |
|---|---|---|---|
| 静态类型 | mypy `--strict` | 编译器(免费) | 编译器(免费,无类型擦除) |
| 运行时类型 | beartype + claw hook | 不需要 | 不需要(编译期强制) |
| "无逃生舱" | 禁裸 `Any` | `#![forbid(unsafe_code)]` | 关死 `!`/`try!`/`as!`/`@unchecked Sendable` + Swift 6 严格并发(complete) |
| 不静默失败 | 无裸 `except`、StrictUndefined | `Result`/`thiserror`、clippy 限 `unwrap` | `throws` + typed `throws(E)` + 具体 `Error`;SwiftLint 禁强解包;边界归一 `ProviderError` |
| 逃生须记录 | `# type: ignore[code] # 原因` | `#[allow(clippy::...)] // 原因` | `// swiftlint:disable:next force_unwrapping — 原因` |
| 边界校验 | pydantic | `serde` + newtype | `Codable` + newtype(parse don't validate) |
| 结构 | src 布局 + 包内 domain-first 深目录 | Cargo workspace + crate-per-domain | SPM package + target-per-domain |
| 模型无关 | `ports/`+`adapters/`,核心零 SDK import | `domain`(trait)+`adapters`,domain 零 SDK 依赖 | `Domain`(protocol)+`Adapters`,Domain 零 SDK 依赖 |
| 可选后端 | optional extras + lazy import | `optional` 依赖 + feature 门控 | package traits + `.when(traits:)` 门控 |
| 装配缝 | `ports/factory.py` | `app` 组装根 `match` | `App` 组装根按 config 选实现;`any LLM` ↔ `Box<dyn>` |
| 配置 | pydantic-settings + yaml | figment + toml | Codable `AppConfig` + 分层加载(默认 < settings.json < env `APP_*`) |
| 日志/血缘/隐私 | logging + log_provenance + SENSITIVE_FIELDS | tracing + log_provenance | `os.Logger` + privacy 插值(`.private`/`.public`)+ logProvenance |
| 提示词 | PackageLoader(随 wheel) | `include_str!`(编译期嵌入) | `Bundle.module`(SPM resources)+ 严格渲染 |
| 门禁 | ruff+mypy+drift+pytest | fmt+clippy -D+doc+test+cargo-deny | swift-format `--strict` + swiftlint `--strict` + build(-warnings-as-errors)+ test |
| 分层上下文 | 根 CLAUDE.md + 就近契约 | 根 CLAUDE.md + 每 crate CLAUDE.md | 根 CLAUDE.md + 每 target CLAUDE.md |
| 脚手架/合规 | scaffold.py / check_conformance.py | scaffold.py / check_conformance.py | scaffold.py / check_conformance.py(`swift package dump-package` 解析 manifest) |
