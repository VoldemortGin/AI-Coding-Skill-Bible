// kernel 单测:配置默认值/env 覆盖、提示词严格渲染、打包资源加载。离线、零 SDK。

package __APP_ID__.kernel

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class KernelTest {
    @Test
    fun configLoadsDefaultsWhenNoFileNoEnv() {
        val config = AppConfig.load(settingsPath = "/nonexistent/path.json", env = emptyMap())
        assertEquals("mock", config.llmProvider)
        assertEquals(5, config.retriever.topK)
    }

    @Test
    fun envOverridesApplyOnTopOfDefaults() {
        val config =
            AppConfig.load(
                settingsPath = "/nonexistent/path.json",
                env = mapOf("APP_RETRIEVER__TOP_K" to "3"),
            )
        assertEquals(3, config.retriever.topK)
    }

    @Test
    fun strictRenderThrowsOnMissingVariable() {
        assertFailsWith<PromptError.MissingVariable> {
            Prompts.render("Hello {{ name }}", emptyMap())
        }
        assertEquals("Hello world", Prompts.render("Hello {{ name }}", mapOf("name" to "world")))
    }

    @Test
    fun bundledPromptLoadsFromClasspath() {
        val template = Prompts.load("rag/answer")
        assertTrue(template.contains("{{ context }}"))
        assertTrue(template.contains("{{ question }}"))
    }
}
