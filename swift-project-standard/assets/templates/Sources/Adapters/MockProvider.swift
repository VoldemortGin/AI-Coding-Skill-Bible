// 确定性离线默认实现(default,不是测试桩):不联网、无需 key 也能跑通并通过测试;
// 同输入同输出,不被随机性污染。这是组装根的默认选择。
//
// 真实后端(如 OpenAIProvider)用 package trait `RealProviders` 门控,放在本 target
// 下用 `#if RealProviders` 包裹整文件,错误归一到 ProviderError —— 默认 build 不拉 SDK。

import Domain

/// 确定性 mock LLM:回显被截断的 prompt 头部。
public struct MockLLM: LLM {
    public init() {}

    public func complete(_ prompt: String) async throws -> String {
        let head = String(prompt.prefix(40))
        return "[mock] \(head)"
    }
}

/// 确定性 mock embedder(同输入同输出,保持数量)。
public struct MockEmbedder: Embedder {
    public init() {}

    public func embed(_ texts: [String]) async throws -> [[Double]] {
        texts.map { text in
            let sum = text.utf8.reduce(0) { $0 + Int($1) }
            return [Double(sum % 1000) / 1000.0]
        }
    }
}
