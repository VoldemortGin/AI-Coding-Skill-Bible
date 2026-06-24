// 领域数据模型。Zod schema 把约束编码进类型:非法状态在边界即被拒绝
// (parse, don't validate)。`z.infer` 出静态类型,运行时 `.parse()` 把关。

import { z } from "zod";

/** 召回条数:整数,合法区间 1..100。越界即 parse 失败,而非沉默截断。 */
export const TopK = z.number().int().min(1).max(100);
/** {@link TopK} 的静态类型。 */
export type TopK = z.infer<typeof TopK>;

/** 检索到的文档片段(边界模型;来自外部检索结果时用 `Document.parse()` 把关)。 */
export const Document = z.object({
  /** 文档来源标识。 */
  id: z.string().min(1),
  /** 文本内容。 */
  text: z.string(),
});
/** {@link Document} 的静态类型。 */
export type Document = z.infer<typeof Document>;
