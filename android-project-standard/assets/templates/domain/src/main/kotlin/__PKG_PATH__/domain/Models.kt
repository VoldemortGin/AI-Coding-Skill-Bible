// 领域数据模型。用 value class newtype 带校验,把约束编码进类型:
// 非法状态不可表示(parse, don't validate)。边界处经 kotlinx.serialization 解码。

package __APP_ID__.domain

import kotlinx.serialization.KSerializer
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.descriptors.SerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder

/**
 * 召回条数 newtype。合法区间 1..100;越界在工厂构造时抛 [DomainError.OutOfRange],而非沉默截断。
 *
 * 用 `private constructor` + 工厂 [of] 强制一切构造走校验:拿到 `TopK` 即"已校验"的类型证明,
 * 下游签名收 `TopK` 就不必再防御性检查。
 */
@Serializable(with = TopKSerializer::class)
@JvmInline
public value class TopK private constructor(public val value: Int) {
    public companion object {
        /** 合法区间。 */
        public val VALID_RANGE: IntRange = 1..100

        /**
         * 构造并校验。
         *
         * @throws DomainError.OutOfRange 当 [value] 不在 [VALID_RANGE]。
         */
        public fun of(value: Int): TopK {
            if (value !in VALID_RANGE) throw DomainError.OutOfRange(value, VALID_RANGE)
            return TopK(value)
        }
    }
}

/** 解码即走校验工厂:非法 JSON 在边界就抛,不渗进领域逻辑。 */
internal object TopKSerializer : KSerializer<TopK> {
    override val descriptor: SerialDescriptor = PrimitiveSerialDescriptor("TopK", PrimitiveKind.INT)

    override fun serialize(
        encoder: Encoder,
        value: TopK,
    ) {
        encoder.encodeInt(value.value)
    }

    override fun deserialize(decoder: Decoder): TopK = TopK.of(decoder.decodeInt())
}

/** 检索到的文档片段(边界可序列化模型)。 */
@Serializable
public data class Document(public val id: String, public val text: String)
