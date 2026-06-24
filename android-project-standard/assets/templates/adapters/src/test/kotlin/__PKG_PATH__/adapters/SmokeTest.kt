// 冒烟测试:无 key、离线也能跑通主链路 —— 默认 config + Mock 实现 + 严格提示词渲染 + newtype 校验。
// 跨 :domain + :kernel + :adapters(adapters 依赖另两者,test 源集可见)。

package __APP_ID__.adapters

import __APP_ID__.domain.DomainError
import __APP_ID__.domain.ProviderError
import __APP_ID__.domain.TopK
import __APP_ID__.kernel.AppConfig
import __APP_ID__.kernel.PromptError
import __APP_ID__.kernel.Prompts
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class SmokeTest {
    @Test
    fun mockProvidersRunEndToEndWithoutKey() =
        runTest {
            val config = AppConfig.load(settingsPath = "/nonexistent.json", env = emptyMap())
            val llm = ProviderFactory.makeLlm(config.llmProvider)
            val embedder = ProviderFactory.makeEmbedder(config.llmProvider)

            val vectors = embedder.embed(listOf("a", "b", "c"))
            assertEquals(3, vectors.size)
            assertTrue(vectors.all { it.isNotEmpty() })

            val answer = llm.complete("ping")
            assertTrue(answer.startsWith("[mock]"))
        }

    @Test
    fun unknownProviderThrowsNoSilentFallback() {
        assertFailsWith<ProviderError.InvalidResponse> {
            ProviderFactory.makeLlm("does-not-exist")
        }
    }

    @Test
    fun strictPromptRenderingThrowsOnMissingVariable() {
        assertFailsWith<PromptError.MissingVariable> {
            Prompts.render("Hello {{ name }}", emptyMap())
        }
        assertEquals("Hello world", Prompts.render("Hello {{ name }}", mapOf("name" to "world")))
    }

    @Test
    fun topKRejectsOutOfRangeValues() {
        assertFailsWith<DomainError.OutOfRange> { TopK.of(0) }
        assertFailsWith<DomainError.OutOfRange> { TopK.of(101) }
        assertEquals(10, TopK.of(10).value)
    }
}
