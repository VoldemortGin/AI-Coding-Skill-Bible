// swift-tools-version: 6.1
//
// SwiftPM manifest. 单一占位符 `__PACKAGE__`(包名 / 可执行名)。
// 工具版本 6.1:`traits:`(package traits = Cargo features 的对应物)需 6.1+ 才可用。
// 模块名与包名无关:`import Kernel` 等不随包名变化。
//
// 基线:Swift 6 语言模式(`.v6`)—— 编译期 data-race 安全(对应 Rust 的 Send/Sync)。
// 离线优先:默认 build/test 零第三方依赖、零 SDK、不联网。真实 SDK adapter 由
// package trait `RealProviders` 门控,见下方注释模板。
//
// 领域 target 由 scaffold.py 按 `--domains` 注入:它替换三处哨兵标记
// (`__DOMAIN_PRODUCT_TARGETS__` / `__DOMAIN_APP_DEPS__` / `__DOMAIN_TARGETS_*__`)。
// 哨兵都是合法 Swift 注释,模板本身(零领域)始终可编译。

import PackageDescription

let package = Package(
    name: "__PACKAGE__",
    platforms: [
        .macOS(.v13),
        .iOS(.v16),
    ],
    products: [
        // CLI / 纯 SPM 运行入口(composition root)。
        .executable(name: "__PACKAGE__", targets: ["App"]),
        // 供 Xcode app 壳 import 并自行组装。领域 target 由 scaffold 追加到此列表。
        .library(name: "AppCore", targets: ["Kernel", "Domain", "Adapters" /* __DOMAIN_PRODUCT_TARGETS__ */]),
    ],
    // SPM package traits = Cargo features 的对应物。默认全关:离线、零 SDK。
    // 启用真实 provider:`swift build --traits RealProviders`(并解开下方 SDK 依赖/target)。
    traits: [
        .default(enabledTraits: []),
        .trait(name: "RealProviders", description: "启用真实 LLM/Embedding SDK adapter(需 key、需联网)。"),
    ],
    dependencies: [
        // 默认无依赖。启用 RealProviders 时解开,例如:
        // .package(
        //     url: "https://github.com/MacPaw/OpenAI.git",
        //     from: "0.4.0"
        // ),
    ],
    targets: [
        // 跨切面基础设施:Config / Logging / Prompts。无外部依赖(Foundation/os)。
        // 声明 resources 以生成 `Bundle.module`,供 Prompts 按子目录定位 markdown。
        .target(
            name: "Kernel",
            exclude: ["CLAUDE.md"],
            resources: [
                .copy("Resources/Prompts")
            ],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
        // ports(protocols)+ models(newtype/Codable)+ 边界错误。
        // 零外部依赖、零 SDK(机械检查的不变量)。不依赖 Kernel,保持纯净。
        .target(
            name: "Domain",
            exclude: ["CLAUDE.md"],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
        // protocol 实现。默认 MockProvider(确定性、离线、无 key、零 SDK)。
        // 真实 adapter 用 trait 门控的依赖:
        //   dependencies: [
        //       "Domain", "Kernel",
        //       .product(name: "OpenAI", package: "OpenAI", condition: .when(traits: ["RealProviders"])),
        //   ],
        // 并在本 target 下加 `OpenAIProvider.swift`(用 `#if RealProviders` 包裹整文件,
        // 错误归一到 ProviderError)。默认 build 不拉取任何 SDK。
        .target(
            name: "Adapters",
            dependencies: ["Domain", "Kernel"],
            exclude: ["CLAUDE.md"],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
        // 领域 target 注入区:scaffold 在下面两行之间生成 `.target(...)` 块。
        // 每个领域只依赖 Domain + Kernel,绝不依赖 Adapters 或 SDK。
        // __DOMAIN_TARGETS_START__
        // __DOMAIN_TARGETS_END__
        // 可执行 composition root:加载 config、按 config 选 provider、跑 demo。
        // 领域无关(领域逻辑由生成的 target 承载;scaffold 把领域追加到 dependencies)。
        .executableTarget(
            name: "App",
            dependencies: ["Kernel", "Domain", "Adapters" /* __DOMAIN_APP_DEPS__ */],
            exclude: ["CLAUDE.md"],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
        // 无 key 也能跑绿:Mock 默认主链路(config + Mock providers + prompt 渲染)。
        .testTarget(
            name: "SmokeTests",
            dependencies: ["Kernel", "Domain", "Adapters"],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
        // 行为不变量契约:任何 provider 实现都须满足同一组测试。
        .testTarget(
            name: "ConformanceTests",
            dependencies: ["Domain", "Adapters"],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
    ]
)
