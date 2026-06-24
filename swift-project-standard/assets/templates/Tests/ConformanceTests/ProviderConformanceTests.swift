// 一致性契约(conformance kit):任何号称实现了某 port 的类型(Mock 与真实后端)都必须
// 跑过同一组行为不变量 —— 可插拔只在所有插头行为一致时才安全。
//
// 真实 adapter 在启用 RealProviders trait / 有 key 时加进对应数组;默认只测 Mock。
// 用 Swift Testing 的参数化 `arguments:` 复用同一组断言。详见 swift-testing。

import Adapters
import Domain
import Testing

/// 把任意 `any Embedder` 包成可作为参数传入的具名 case(`arguments:` 要求 Sendable 元素)。
struct EmbedderCase: Sendable, CustomTestStringConvertible {
    let name: String
    let make: @Sendable () -> any Embedder
    var testDescription: String { name }
}

/// 把任意 `any LLM` 包成可作为参数传入的具名 case。
struct LLMCase: Sendable, CustomTestStringConvertible {
    let name: String
    let make: @Sendable () -> any LLM
    var testDescription: String { name }
}

@Suite("Provider conformance")
struct ProviderConformanceTests {
    static let embedders: [EmbedderCase] = [
        EmbedderCase(name: "MockEmbedder", make: { MockEmbedder() })
        // 启用真实后端时追加,例如:
        // EmbedderCase(name: "OpenAIEmbedder", make: { OpenAIProvider() }),
    ]

    static let llms: [LLMCase] = [
        LLMCase(name: "MockLLM", make: { MockLLM() })
    ]

    @Test("Embedder is deterministic", arguments: embedders)
    func embedderDeterministic(_ embedderCase: EmbedderCase) async throws {
        let embedder = embedderCase.make()
        let first = try await embedder.embed(["hello", "world"])
        let second = try await embedder.embed(["hello", "world"])
        #expect(first == second)
    }

    @Test("Embedder preserves input count", arguments: embedders)
    func embedderPreservesCount(_ embedderCase: EmbedderCase) async throws {
        let embedder = embedderCase.make()
        let vectors = try await embedder.embed(["a", "b", "c"])
        #expect(vectors.count == 3)
    }

    @Test("Embedder returns non-empty vectors", arguments: embedders)
    func embedderNonEmptyVectors(_ embedderCase: EmbedderCase) async throws {
        let embedder = embedderCase.make()
        let vectors = try await embedder.embed(["x"])
        #expect(vectors.allSatisfy { !$0.isEmpty })
    }

    @Test("LLM returns non-empty completion", arguments: llms)
    func llmNonEmpty(_ llmCase: LLMCase) async throws {
        let llm = llmCase.make()
        let output = try await llm.complete("ping")
        #expect(!output.isEmpty)
    }
}
