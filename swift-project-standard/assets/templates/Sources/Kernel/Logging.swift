// 集中日志。`os.Logger` 统一日志,privacy 插值原生实现"隐私不落盘":
// payload 用 `.private`,码值/计数/耗时用 `.public`。非 Apple 平台回退到 stderr。
//
// 详见 swift-concurrency(Sendable)。Log 命名空间无可变全局状态,天然 Sendable。

import Foundation

#if canImport(os)
import os

/// 集中日志命名空间:分类 logger 工厂 + 血缘记录。
public enum Log {
    /// 统一 subsystem(可按需改成 bundle id)。
    public static let subsystem = "app"

    /// Kernel 跨切面日志。
    public static let kernel = Logger(subsystem: subsystem, category: "kernel")

    /// 按 category 造 logger。
    public static func make(category: String) -> Logger {
        Logger(subsystem: subsystem, category: category)
    }

    /// 记录一次 provider 调用的血缘。码值/计数公开,payload 不落盘。
    public static func logProvenance(source: String, impl: String, version: String, count: Int) {
        kernel.info(
            """
            provenance source=\(source, privacy: .public) \
            impl=\(impl, privacy: .public) version=\(version, privacy: .public) \
            count=\(count, privacy: .public)
            """
        )
    }
}

#else

/// 非 Apple 平台的最小回退:写 stderr。保持与 os.Logger 同样的 API 形状。
public struct Logger: Sendable {
    private let category: String

    public init(subsystem: String, category: String) {
        self.category = category
    }

    public func info(_ message: String) {
        FileHandle.standardError.write(Data("[\(category)] \(message)\n".utf8))
    }

    public func error(_ message: String) {
        FileHandle.standardError.write(Data("[\(category)] ERROR \(message)\n".utf8))
    }
}

/// 集中日志命名空间(stderr 回退版)。
public enum Log {
    /// 统一 subsystem。
    public static let subsystem = "app"

    /// Kernel 跨切面日志。
    public static let kernel = Logger(subsystem: subsystem, category: "kernel")

    /// 按 category 造 logger。
    public static func make(category: String) -> Logger {
        Logger(subsystem: subsystem, category: category)
    }

    /// 记录一次 provider 调用的血缘。
    public static func logProvenance(source: String, impl: String, version: String, count: Int) {
        kernel.info(
            "provenance source=\(source) impl=\(impl) version=\(version) count=\(count)"
        )
    }
}

#endif
