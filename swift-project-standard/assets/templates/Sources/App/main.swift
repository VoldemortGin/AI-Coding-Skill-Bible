// 组装根(composition root):读配置、按配置选 provider(默认 Mock)、跑一次 demo。
//
// 领域无关:只用 Kernel + Domain + Adapters 演示主链路。领域 target 由 scaffold 生成,
// 生成后在此 import 并注入(scaffold 不改写本文件,保持装配缝示例最小且始终可编译)。
//
// 可执行 target 用 `main.swift` 顶层代码(因此本文件不可用 `@main`,二选一)。
// 唯一装配缝在 `makeLLM` / `makeEmbedder`:未知 provider 显式报错,绝不沉默回退。

import Adapters
import Domain
import Kernel

/// 装配缝:按配置选 LLM 实现。默认 mock(离线);真实后端在 RealProviders trait 下解开。
func makeLLM(_ config: AppConfig) throws -> any LLM {
    switch config.llmProvider {
    case "mock":
        return MockLLM()
    // case "openai":
    //     #if RealProviders
    //     return OpenAIProvider()
    //     #else
    //     throw ProviderError.missingCredentials("openai 需 --traits RealProviders 构建")
    //     #endif
    default:
        throw ProviderError.invalidResponse("未知 llmProvider: \(config.llmProvider)")
    }
}

/// 装配缝:按配置选 Embedder 实现。默认 mock。
func makeEmbedder(_ config: AppConfig) -> any Embedder {
    MockEmbedder()
}

func run() async throws {
    let config = try AppConfig.load()
    Log.kernel.info("started provider=\(config.llmProvider, privacy: .public)")

    let llm = try makeLLM(config)
    let embedder = makeEmbedder(config)

    // 用 Embedder 演示一次向量化(领域逻辑由 scaffold 生成的 target 承载并注入)。
    let vectors = try await embedder.embed(["Swift 6 enforces data-race safety at compile time."])
    Log.logProvenance(
        source: "embedder",
        impl: "\(type(of: embedder))",
        version: "1",
        count: vectors.count
    )

    // 渲染打包的提示词(严格渲染:缺变量直接报错),再交给 LLM 生成。
    let prompt = try Prompts.render(
        named: "rag/answer",
        variables: [
            "context": "Swift keeps concurrency safe via compile-time data-race checking.",
            "question": "How does Swift keep concurrency safe?",
        ]
    )
    let answer = try await llm.complete(prompt)
    print(answer)
}

try await run()
