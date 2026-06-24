// 一致性契约(conformance kit):任何号称实现了某 port 的类型(Mock 与真实后端)都必须
// 跑过同一组行为不变量 —— 可插拔只在所有插头行为一致时才安全。
//
// 真实 adapter(启用 gated module / 有 key 时)把工厂加进对应 list 即复用同一组断言。

package __APP_ID__.adapters

import __APP_ID__.domain.Embedder
import __APP_ID__.domain.Llm
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ProviderConformanceTest {
    private val embedders: List<Pair<String, () -> Embedder>> =
        listOf(
            "MockEmbedder" to { MockEmbedder() },
            // "OpenAiEmbedder" to { OpenAiEmbedder() },
        )
    private val llms: List<Pair<String, () -> Llm>> =
        listOf(
            "MockLlm" to { MockLlm() },
        )

    @Test
    fun embedderIsDeterministic() =
        runTest {
            for ((name, make) in embedders) {
                val embedder = make()
                val first = embedder.embed(listOf("hello", "world"))
                val second = embedder.embed(listOf("hello", "world"))
                assertEquals(first, second, "$name 应确定性:同输入同输出")
            }
        }

    @Test
    fun embedderPreservesInputCount() =
        runTest {
            for ((name, make) in embedders) {
                val vectors = make().embed(listOf("a", "b", "c"))
                assertEquals(3, vectors.size, "$name 应保持输入数量")
            }
        }

    @Test
    fun embedderReturnsNonEmptyVectors() =
        runTest {
            for ((name, make) in embedders) {
                val vectors = make().embed(listOf("x"))
                assertTrue(vectors.all { it.isNotEmpty() }, "$name 不应返回空向量")
            }
        }

    @Test
    fun llmReturnsNonEmptyCompletion() =
        runTest {
            for ((name, make) in llms) {
                assertTrue(make().complete("ping").isNotEmpty(), "$name 应返回非空回答")
            }
        }
}
