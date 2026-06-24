// 装配缝工厂:按 config 选具体实现。默认 mock;未知 provider 显式抛错,绝不沉默回退。
// :app 的 Hilt 组合根(AppModule)调用它注入 `Llm` / `Embedder`。
//
// 真实后端在 gated 的 `:adapters-openai` module 里;开启后在此 when 加一个分支(见 CLAUDE.md)。

package __APP_ID__.adapters

import __APP_ID__.domain.Embedder
import __APP_ID__.domain.Llm
import __APP_ID__.domain.ProviderError

/** provider 装配缝:config 字符串 → 实现。 */
public object ProviderFactory {
    /**
     * 按 provider 标识选 LLM 实现。
     *
     * @throws ProviderError.InvalidResponse 当 provider 未知(绝不沉默回退到默认)。
     */
    public fun makeLlm(provider: String): Llm =
        when (provider) {
            "mock" -> MockLlm()
            // "openai" -> OpenAiLlm()   // 仅当 gated :adapters-openai 启用时解开
            else -> throw ProviderError.InvalidResponse("unknown llmProvider: $provider")
        }

    /** 按 provider 标识选 Embedder 实现。默认 mock。 */
    public fun makeEmbedder(provider: String): Embedder =
        when (provider) {
            "mock" -> MockEmbedder()
            // "openai" -> OpenAiEmbedder()
            else -> throw ProviderError.InvalidResponse("unknown embedder provider: $provider")
        }
}
