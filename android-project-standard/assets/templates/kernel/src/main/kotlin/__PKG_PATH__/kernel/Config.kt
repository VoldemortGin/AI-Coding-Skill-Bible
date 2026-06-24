// 全局配置的唯一来源。优先级:默认值 < `configs/settings.json` < 环境变量(`APP_` 前缀,
// `__` 分隔嵌套)。kotlinx.serialization 解码为强类型;非法配置在加载时报错(parse, don't validate)。
//
// 无 settings.json、无 env 时必须以默认值加载成功(供离线测试)。零 SDK。

package __APP_ID__.kernel

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File

/** 检索相关配置。 */
@Serializable
public data class RetrieverConfig(
    /** 召回条数。 */
    val topK: Int = 5,
    /** 重排模型标识。 */
    val rerankModel: String = "mock-rerank",
)

/** 应用全局配置。`data class` 默认值即离线可跑的基线。 */
@Serializable
public data class AppConfig(
    /** LLM provider(组合根按此选实现);默认 `mock`,离线可跑。 */
    val llmProvider: String = "mock",
    /** 检索配置。 */
    val retriever: RetrieverConfig = RetrieverConfig(),
) {
    public companion object {
        private val json = Json { ignoreUnknownKeys = true }

        /**
         * 加载配置。默认值 < `configs/settings.json` < 环境变量(`APP_` 前缀,`__` 分隔嵌套)。
         *
         * @param settingsPath settings.json 路径;不存在则用默认值(不报错)。
         * @param env 环境变量字典;默认取进程环境。
         * @return 合并各层后的强类型配置。
         * @throws kotlinx.serialization.SerializationException 文件存在但内容非法时(不静默吞)。
         */
        public fun load(
            settingsPath: String = "configs/settings.json",
            env: Map<String, String> = System.getenv(),
        ): AppConfig {
            val file = File(settingsPath)
            val base =
                if (file.isFile) {
                    json.decodeFromString<AppConfig>(file.readText())
                } else {
                    AppConfig()
                }
            return base.withEnvOverrides(env)
        }
    }
}

/** 逐项应用 `APP_` 前缀的环境变量覆盖(`__` 分隔嵌套)。 */
private fun AppConfig.withEnvOverrides(env: Map<String, String>): AppConfig {
    var result = this
    env["APP_LLM_PROVIDER"]?.takeIf { it.isNotEmpty() }?.let {
        result = result.copy(llmProvider = it)
    }
    env["APP_RETRIEVER__TOP_K"]?.toIntOrNull()?.let {
        result = result.copy(retriever = result.retriever.copy(topK = it))
    }
    env["APP_RETRIEVER__RERANK_MODEL"]?.takeIf { it.isNotEmpty() }?.let {
        result = result.copy(retriever = result.retriever.copy(rerankModel = it))
    }
    return result
}
