// ports:所有外部 AI 依赖的最小 interface。
//
// 核心与领域逻辑只依赖这些 interface,绝不依赖具体 SDK。接口越窄能塞的实现越多,
// "换模型"从重构降级为加一个实现。`suspend` 是语言关键字(零依赖);失败抛 ProviderError。

package __APP_ID__.domain

/** 文本生成。 */
public interface Llm {
    /**
     * 用给定 prompt 生成回答。
     *
     * @throws ProviderError provider 调用失败时(在 adapter 边界归一)。
     */
    public suspend fun complete(prompt: String): String
}

/** 文本向量化。 */
public interface Embedder {
    /**
     * 批量嵌入文本;返回每条文本对应的向量。
     *
     * @throws ProviderError provider 调用失败时(在 adapter 边界归一)。
     */
    public suspend fun embed(texts: List<String>): List<List<Double>>
}
