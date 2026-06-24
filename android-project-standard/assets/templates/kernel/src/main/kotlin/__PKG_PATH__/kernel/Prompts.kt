// [AI 层] 提示词加载与严格渲染。
//
// classpath 资源(随 jar 出厂,无运行时路径问题 —— 对应 Swift Bundle.module / Rust include_str!)。
// 严格渲染:缺变量直接抛 PromptError.MissingVariable(对应 StrictUndefined),而非静默留空。
// 模板语法极简:`{{ name }}` 占位,缺值即报错。

package __APP_ID__.kernel

/** 提示词错误。 */
public sealed class PromptError(message: String) : Exception(message) {
    /** 找不到打包的提示词资源。 */
    public class ResourceNotFound(name: String) : PromptError("prompt resource not found: $name")

    /** 渲染时缺少变量。 */
    public class MissingVariable(key: String) : PromptError("missing prompt variable: $key")
}

/** 提示词命名空间:加载 + 严格渲染。 */
public object Prompts {
    /**
     * 加载打包提示词的原始文本(相对 `resources/prompts/` 的子路径,如 `rag/answer`)。
     *
     * @throws PromptError.ResourceNotFound 当资源不存在。
     */
    public fun load(name: String): String {
        val path = "/prompts/$name.md"
        val stream =
            Prompts::class.java.getResourceAsStream(path)
                ?: throw PromptError.ResourceNotFound(name)
        return stream.bufferedReader().use { it.readText() }
    }

    /**
     * 严格渲染:`{{ key }}` 全部替换;模板里出现但未提供的变量直接报错。
     *
     * @throws PromptError.MissingVariable 当模板引用了未提供的变量。
     */
    public fun render(
        template: String,
        variables: Map<String, String>,
    ): String {
        val builder = StringBuilder()
        var index = 0
        // 单出口循环(无 break/continue):未找到 `{{` 或缺闭合 `}}` 时把剩余文本当字面量、index 推到末尾。
        while (index < template.length) {
            val open = template.indexOf("{{", index)
            val close = if (open < 0) -1 else template.indexOf("}}", open + 2)
            if (open < 0 || close < 0) {
                // 无更多占位符(或有未闭合的 `{{`):剩余文本原样输出。
                builder.append(template, index, template.length)
                index = template.length
            } else {
                builder.append(template, index, open)
                val key = template.substring(open + 2, close).trim()
                val value = variables[key] ?: throw PromptError.MissingVariable(key)
                builder.append(value)
                index = close + 2
            }
        }
        return builder.toString()
    }

    /** 便捷:加载并渲染一个打包提示词。 */
    public fun renderNamed(
        name: String,
        variables: Map<String, String>,
    ): String = render(load(name), variables)
}
