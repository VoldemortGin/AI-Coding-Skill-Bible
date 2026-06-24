// 全局配置:Zod 校验(t3-env 模式),server / client 各一 schema。分层合并:
// 默认值 < 文件层(configs/settings.json)< 环境变量。非法即在加载时抛错
// (parse, don't validate)。无文件、无 env 时以默认值成功加载(供离线测试)。
//
// 本模块**浏览器安全**:不 import 任何 node 内置。文件层从哪来由调用方注入
// (node 侧用 `config-node.ts` 的 `readSettingsFile()`;浏览器侧传 `{}`)。
// secrets 只来自 server env,绝不读进 client、绝不落日志、绝不进 bundle。

import { z } from "zod";

/** 服务端配置 schema(含可含 secret 的项;只在 node / server 读取)。 */
const serverSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  /** 装配缝:选 LLM provider。默认 mock(离线、无 key)。 */
  LLM_PROVIDER: z.string().min(1).default("mock"),
  /** 召回条数:1..100,越界即拒绝加载。env 是字符串,先 coerce 再校验。 */
  RETRIEVER_TOP_K: z.coerce.number().int().min(1).max(100).default(5),
});

/** 客户端配置 schema(公开、可进 bundle;不得放 secret)。 */
const clientSchema = z.object({
  NEXT_PUBLIC_APP_NAME: z.string().min(1).default("app"),
});

/** 结构化文件配置(configs/settings.json;非 secret)。全部可选,作为中间层。 */
export const fileSchema = z
  .object({
    llmProvider: z.string().min(1).optional(),
    retriever: z
      .object({
        topK: z.number().int().min(1).max(100).optional(),
        rerankModel: z.string().min(1).optional(),
      })
      .optional(),
  })
  .partial();

/** 服务端强类型配置。 */
export type ServerConfig = z.infer<typeof serverSchema>;
/** 客户端强类型配置。 */
export type ClientConfig = z.infer<typeof clientSchema>;
/** 文件层配置。 */
export type FileConfig = z.infer<typeof fileSchema>;

/** 合并后的应用配置。 */
export interface AppConfig {
  readonly server: ServerConfig;
  readonly client: ClientConfig;
  /** 重排模型标识(来自文件层,带默认值)。 */
  readonly rerankModel: string;
}

/** 一个原始环境记录(`process.env` 形状:键到可选字符串)。 */
export type RawEnv = Record<string, string | undefined>;

/** {@link loadConfig} 的可选输入(供测试与浏览器注入,绕开真实进程环境与文件系统)。 */
export interface LoadConfigOptions {
  /** 原始 env;默认取 `process.env`(浏览器无 `process` 时为空)。 */
  readonly env?: RawEnv;
  /** 已解析的文件层配置;默认空(node 侧用 `readSettingsFile()` 显式传入)。 */
  readonly file?: FileConfig;
}

/**
 * 加载并校验配置。分层:默认值 < 文件 < env。
 *
 * @param options - 注入点(env / file)。
 * @returns 合并、校验后的强类型配置。
 * @throws {z.ZodError} env / 文件不合法时抛出(不静默吞掉)。
 */
export function loadConfig(options: LoadConfigOptions = {}): AppConfig {
  const env = options.env ?? readProcessEnv();
  const file = options.file ?? {};

  // env 优先于文件层:文件层只在对应 env 缺省时生效。
  const merged: RawEnv = { ...env };
  if (merged["LLM_PROVIDER"] === undefined && file.llmProvider !== undefined) {
    merged["LLM_PROVIDER"] = file.llmProvider;
  }
  if (merged["RETRIEVER_TOP_K"] === undefined && file.retriever?.topK !== undefined) {
    merged["RETRIEVER_TOP_K"] = String(file.retriever.topK);
  }

  const server = serverSchema.parse(merged);
  const client = clientSchema.parse(merged);
  const rerankModel = file.retriever?.rerankModel ?? "mock-rerank";

  return { server, client, rerankModel };
}

/** 安全读取进程环境(浏览器无 `process` 时回退空对象)。 */
function readProcessEnv(): RawEnv {
  if (typeof process === "undefined") {
    return {};
  }
  return process.env;
}
