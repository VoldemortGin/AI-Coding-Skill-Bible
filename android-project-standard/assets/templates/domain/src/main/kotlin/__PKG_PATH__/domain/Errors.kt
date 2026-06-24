// 边界错误。sealed 层级 → `when` 穷尽由编译器保证(对应 Rust 的 Result<T,E> + thiserror、
// Swift 的 typed throws)。
//
// 纪律:厂商 SDK 的各色错误在 adapter 内归一到 [ProviderError];领域校验错误用 [DomainError]。
// 程序 bug(不变量被破坏)照常 `error(...)` / `require(...)`,不混进这里、不被 catch 吞掉。

package __APP_ID__.domain

/** provider(LLM / Embedder / 真实 SDK)调用边界的归一化错误。 */
public sealed class ProviderError(message: String) : Exception(message) {
    /** 缺少凭据(如未配置 API key)。 */
    public class MissingCredentials(detail: String) : ProviderError(detail)

    /** 远端/传输层失败。 */
    public class Transport(detail: String) : ProviderError(detail)

    /** 响应不符合预期(空结果、格式错误等)。 */
    public class InvalidResponse(detail: String) : ProviderError(detail)
}

/** 领域校验错误:外部输入违反类型约束时抛出。 */
public sealed class DomainError(message: String) : Exception(message) {
    /** 数值越界。 */
    public class OutOfRange(value: Int, allowed: IntRange) :
        DomainError("value out of range: $value not in $allowed")

    /** 输入为空但要求非空。 */
    public class EmptyInput(field: String) : DomainError("empty input: $field")
}
