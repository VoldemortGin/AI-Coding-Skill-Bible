// 全局配置的唯一来源。优先级:默认值 < `configs/settings.json` < 环境变量(`APP_` 前缀,
// `__` 分隔嵌套)。Codable 解码为强类型;非法配置在加载时报错(parse, don't validate)。
//
// 无 settings.json、无 env 时必须以默认值加载成功(供离线测试)。无第三方依赖。

import Foundation

/// 检索相关配置。
public struct RetrieverConfig: Codable, Sendable, Equatable {
    /// 召回条数。
    public var topK: Int
    /// 重排模型标识。
    public var rerankModel: String

    /// 默认值:离线可跑。
    public init(topK: Int = 5, rerankModel: String = "mock-rerank") {
        self.topK = topK
        self.rerankModel = rerankModel
    }
}

/// 应用全局配置。
public struct AppConfig: Codable, Sendable, Equatable {
    /// LLM provider(组装根按此选实现);默认 `mock`,离线可跑。
    public var llmProvider: String
    /// 检索配置。
    public var retriever: RetrieverConfig

    /// 默认配置:无文件、无 env 时即用此值,保证离线主链路可跑通。
    public init(llmProvider: String = "mock", retriever: RetrieverConfig = RetrieverConfig()) {
        self.llmProvider = llmProvider
        self.retriever = retriever
    }
}

extension AppConfig {
    /// 加载配置。默认值 < `configs/settings.json` < 环境变量。
    ///
    /// - Parameters:
    ///   - configPath: settings.json 路径;`nil` 时用当前工作目录下 `configs/settings.json`。
    ///   - environment: 环境变量字典;默认取进程环境。
    /// - Returns: 合并各层后的强类型配置。
    /// - Throws: JSON 解码失败(类型不匹配等)时抛出底层 `DecodingError`。
    public static func load(
        configPath: String? = nil,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) throws -> AppConfig {
        var config = AppConfig()

        let path = configPath ?? "configs/settings.json"
        let url = URL(fileURLWithPath: path)
        if let data = try? Data(contentsOf: url) {
            // 文件存在但内容非法 → 抛错(不静默吞掉)。文件不存在 → 用默认值。
            config = try JSONDecoder().decode(AppConfig.self, from: data)
        }

        config.applyEnvironmentOverrides(environment)
        return config
    }

    /// 逐项应用 `APP_` 前缀的环境变量覆盖(`__` 分隔嵌套)。
    private mutating func applyEnvironmentOverrides(_ environment: [String: String]) {
        if let provider = environment["APP_LLM_PROVIDER"], !provider.isEmpty {
            llmProvider = provider
        }
        if let topKRaw = environment["APP_RETRIEVER__TOP_K"], let topK = Int(topKRaw) {
            retriever.topK = topK
        }
        if let model = environment["APP_RETRIEVER__RERANK_MODEL"], !model.isEmpty {
            retriever.rerankModel = model
        }
    }
}
