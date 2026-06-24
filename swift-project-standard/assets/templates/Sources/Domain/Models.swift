// 领域数据模型。用 newtype / 值类型带校验,把约束编码进类型:
// 非法状态不可表示(parse, don't validate)。边界处用 Codable 解码。

/// 召回条数 newtype。合法区间 1...100;越界在构造时抛错,而非沉默截断。
public struct TopK: Codable, Equatable, Sendable {
    /// 校验后的值,保证落在 1...100。
    public let value: Int

    /// 合法区间。
    public static let validRange = 1...100

    /// 构造并校验。
    ///
    /// - Parameter value: 期望的召回条数。
    /// - Throws: ``DomainError/outOfRange(_:allowed:)`` 当 `value` 不在 1...100。
    public init(_ value: Int) throws {
        guard Self.validRange.contains(value) else {
            throw DomainError.outOfRange(value, allowed: Self.validRange)
        }
        self.value = value
    }

    /// 从外部数据解码时同样走校验:非法 JSON 直接解码失败,不放进系统。
    public init(from decoder: any Decoder) throws {
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(Int.self)
        try self.init(raw)
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(value)
    }
}

/// 检索到的文档片段(边界 Codable 模型)。
public struct Document: Codable, Equatable, Sendable {
    /// 文档来源标识。
    public let id: String
    /// 文本内容。
    public let text: String

    /// 构造文档片段。
    public init(id: String, text: String) {
        self.id = id
        self.text = text
    }
}
