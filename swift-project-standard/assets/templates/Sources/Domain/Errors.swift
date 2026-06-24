// 边界错误。具体 enum,可被 typed throws(Swift 6 `throws(ProviderError)`)精确标注。
//
// 纪律:厂商 SDK 的各色错误在 adapter 内归一到 ``ProviderError``;领域校验错误用
// ``DomainError``。程序 bug(不变量被破坏)照常 `fatalError`/`precondition`,不混进这里。
// 详见 swift-error-handling。

/// provider(LLM / Embedder / 真实 SDK)调用边界的归一化错误。
public enum ProviderError: Error, Sendable, Equatable {
    /// 缺少凭据(如未配置 API key)。
    case missingCredentials(String)
    /// 远端/传输层失败,附带可读说明。
    case transport(String)
    /// 响应不符合预期(空结果、格式错误等)。
    case invalidResponse(String)
}

/// 领域校验错误:外部输入违反类型约束时抛出。
public enum DomainError: Error, Sendable, Equatable {
    /// 数值越界。
    case outOfRange(Int, allowed: ClosedRange<Int>)
    /// 输入为空但要求非空。
    case emptyInput(String)
}
