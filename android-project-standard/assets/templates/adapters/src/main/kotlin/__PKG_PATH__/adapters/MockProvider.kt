// 确定性离线默认实现(default,不是测试桩):不联网、无需 key 也能跑通并通过测试;
// 同输入同输出,不被随机性污染。这是组合根的默认选择。

package __APP_ID__.adapters

import __APP_ID__.domain.Embedder
import __APP_ID__.domain.Llm

/** 确定性 mock LLM:回显被截断的 prompt 头部。 */
public class MockLlm : Llm {
    override suspend fun complete(prompt: String): String = "[mock] ${prompt.take(MAX_ECHO)}"

    private companion object {
        const val MAX_ECHO = 40
    }
}

/** 确定性 mock embedder(同输入同输出,保持数量)。 */
public class MockEmbedder : Embedder {
    override suspend fun embed(texts: List<String>): List<List<Double>> =
        texts.map { text ->
            val sum = text.sumOf { it.code }
            listOf((sum % SCALE) / SCALE.toDouble())
        }

    private companion object {
        const val SCALE = 1000
    }
}
