// ports:所有外部 AI 依赖的最小协议接口。
//
// 核心与领域逻辑只依赖这些协议,绝不依赖具体 SDK。接口越窄能塞的实现越多,
// "换模型"从重构降级为加一个实现。协议保持可被 `any` 存在类型擦除
// (无 `Self`/associatedtype 要求阻碍 `any LLM` / `any Embedder`),以便组装根注入。
//
// 详见 swift-protocols(some vs any、存在类型)与 swift-concurrency(Sendable、async)。

/// 文本生成。
public protocol LLM: Sendable {
    /// 用给定 prompt 生成回答。
    ///
    /// - Throws: provider 调用失败时抛出 ``ProviderError``。
    func complete(_ prompt: String) async throws -> String
}

/// 文本向量化。
public protocol Embedder: Sendable {
    /// 批量嵌入文本;返回每条文本对应的向量。
    ///
    /// - Throws: provider 调用失败时抛出 ``ProviderError``。
    func embed(_ texts: [String]) async throws -> [[Double]]
}
