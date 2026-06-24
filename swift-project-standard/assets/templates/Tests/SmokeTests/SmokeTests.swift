// 冒烟测试:无 key、离线也能跑通主链路 —— 加载默认 config、用 MockLLM/MockEmbedder、
// 渲染一个 prompt、校验缺变量报错。领域无关(领域 target 由 scaffold 生成,自带其测试)。
// 用 Swift Testing(Swift 6.x 自带)。
//
// 详见 swift-testing(@Test / #expect / #require)。

import Adapters
import Domain
import Kernel
import Testing

@Suite("Smoke: offline main chain")
struct SmokeTests {
    @Test("AppConfig loads with defaults when no file and no env")
    func configLoadsDefaults() throws {
        let config = try AppConfig.load(configPath: "/nonexistent/path.json", environment: [:])
        #expect(config.llmProvider == "mock")
        #expect(config.retriever.topK == 5)
    }

    @Test("Environment overrides apply on top of defaults")
    func envOverrides() throws {
        let config = try AppConfig.load(
            configPath: "/nonexistent/path.json",
            environment: ["APP_LLM_PROVIDER": "mock", "APP_RETRIEVER__TOP_K": "3"]
        )
        #expect(config.retriever.topK == 3)
    }

    @Test("Mock providers run end to end without a key")
    func mainChain() async throws {
        let embedder = MockEmbedder()
        let llm = MockLLM()

        let vectors = try await embedder.embed(["a", "b", "c"])
        #expect(vectors.count == 3)
        #expect(vectors.allSatisfy { !$0.isEmpty })

        let answer = try await llm.complete("ping")
        #expect(!answer.isEmpty)
        #expect(answer.hasPrefix("[mock]"))
    }

    @Test("Strict prompt rendering throws on missing variable")
    func strictPromptThrows() throws {
        #expect(throws: PromptError.self) {
            try Prompts.render("Hello {{ name }}", variables: [:])
        }
        let rendered = try Prompts.render("Hello {{ name }}", variables: ["name": "world"])
        #expect(rendered == "Hello world")
    }

    @Test("Bundled prompt loads via Bundle.module")
    func bundledPromptLoads() throws {
        let template = try Prompts.load("rag/answer")
        #expect(template.contains("{{ context }}"))
        #expect(template.contains("{{ question }}"))
    }

    @Test("TopK rejects out-of-range values")
    func topKValidation() throws {
        #expect(throws: DomainError.self) {
            _ = try TopK(0)
        }
        #expect(throws: DomainError.self) {
            _ = try TopK(101)
        }
        let valid = try TopK(10)
        #expect(valid.value == 10)
    }
}
