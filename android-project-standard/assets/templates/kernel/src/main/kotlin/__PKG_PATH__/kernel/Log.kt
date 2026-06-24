// 集中日志。平台无关:默认写 stderr;Android 可在 :app 启动时设 `Log.sink` 路由到 android.util.Log。
//
// 隐私纪律(机械化为约定 + 评审项):**payload 绝不传进来**。`logProvenance` 只收码值/计数/版本,
// 不收答案/原文/向量/用户输入 —— 让"隐私不落盘"成为 API 形状本身,而非靠人记得脱敏。

package __APP_ID__.kernel

/** 集中日志命名空间:分类日志 + 血缘记录。无可变共享状态(sink 在启动时设一次)。 */
public object Log {
    /** 日志落点。默认 stderr;Android 在组合根改成 `{ line -> android.util.Log.i("app", line) }`。 */
    public var sink: (String) -> Unit = { line -> System.err.println(line) }

    public fun info(
        category: String,
        message: String,
    ) {
        sink("[$category] $message")
    }

    public fun error(
        category: String,
        message: String,
    ) {
        sink("[$category] ERROR $message")
    }

    /**
     * 记录一次 provider 调用的血缘。**只收码值/计数/版本** —— payload 不在此出现。
     *
     * @param source 数据来源标识(如 "embedder")。
     * @param impl 产出它的实现类型名。
     * @param version 实现/契约版本号。
     * @param count 产出条数(计数,非内容)。
     */
    public fun logProvenance(
        source: String,
        impl: String,
        version: String,
        count: Int,
    ) {
        sink("provenance source=$source impl=$impl version=$version count=$count")
    }
}
