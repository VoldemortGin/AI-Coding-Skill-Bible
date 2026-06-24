// [AI 层] 提示词加载与严格渲染。
//
// `Bundle.module` 从随构件出厂的 resources 里按子目录定位 markdown(无运行时路径问题)。
// 严格渲染:缺变量直接 throw ``PromptError/missingVariable(_:)``(对应 StrictUndefined),
// 而非静默留空。模板语法极简:`{{ name }}` 占位,缺值即报错。进阶可选 Stencil。

import Foundation

/// 提示词错误。
public enum PromptError: Error, Sendable, Equatable {
    /// 找不到打包的提示词资源。
    case resourceNotFound(String)
    /// 渲染时缺少变量。
    case missingVariable(String)
}

/// 提示词命名空间:加载 + 严格渲染。
public enum Prompts {
    /// 加载打包提示词的原始文本(相对 `Resources/Prompts` 的子路径,如 `rag/answer`)。
    ///
    /// - Parameter name: 提示词子路径(不含 `.md` 扩展名)。
    /// - Returns: 提示词模板的原始文本。
    /// - Throws: ``PromptError/resourceNotFound(_:)`` 当资源不存在。
    public static func load(_ name: String) throws -> String {
        guard
            let url = Bundle.module.url(
                forResource: name,
                withExtension: "md",
                subdirectory: "Prompts"
            )
        else {
            throw PromptError.resourceNotFound(name)
        }
        return try String(contentsOf: url, encoding: .utf8)
    }

    /// 严格渲染:`{{ key }}` 全部替换;模板里出现但未提供的变量直接报错。
    ///
    /// - Parameters:
    ///   - template: 含 `{{ key }}` 占位的模板文本。
    ///   - variables: 变量字典。
    /// - Returns: 所有占位符替换后的文本。
    /// - Throws: ``PromptError/missingVariable(_:)`` 当模板引用了未提供的变量。
    public static func render(_ template: String, variables: [String: String]) throws -> String {
        var output = ""
        var rest = Substring(template)

        while let open = rest.range(of: "{{") {
            output += rest[rest.startIndex..<open.lowerBound]
            let afterOpen = rest[open.upperBound...]
            guard let close = afterOpen.range(of: "}}") else {
                // 没有闭合标记:剩余文本原样输出(含未闭合的 `{{`)。
                output += rest[open.lowerBound...]
                return output
            }
            let key = afterOpen[afterOpen.startIndex..<close.lowerBound]
                .trimmingCharacters(in: .whitespaces)
            guard let value = variables[key] else {
                throw PromptError.missingVariable(key)
            }
            output += value
            rest = afterOpen[close.upperBound...]
        }

        output += rest
        return output
    }

    /// 便捷:加载并渲染一个打包提示词。
    ///
    /// - Parameters:
    ///   - name: 提示词子路径(不含 `.md` 扩展名)。
    ///   - variables: 变量字典。
    /// - Returns: 渲染后的文本。
    /// - Throws: ``PromptError`` 当资源缺失或变量缺失。
    public static func render(named name: String, variables: [String: String]) throws -> String {
        let template = try load(name)
        return try render(template, variables: variables)
    }
}
