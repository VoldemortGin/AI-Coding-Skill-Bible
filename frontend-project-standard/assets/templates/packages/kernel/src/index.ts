// kernel 公共 API(浏览器安全):config(Zod env)/ logging / prompts。零 UI 框架、零 SDK。
// node 专属的文件层读取(readSettingsFile)从 `@__SCOPE__/kernel/node` 子路径导出,
// 浏览器 bundle 不会拉到 node 内置。

export type {
  AppConfig,
  ClientConfig,
  FileConfig,
  LoadConfigOptions,
  RawEnv,
  ServerConfig,
} from "./config.js";
export { fileSchema, loadConfig } from "./config.js";

export type { LogFields, Logger, LogLevel, Provenance } from "./logging.js";
export { createLogger, logger, logProvenance } from "./logging.js";

export { PromptError, renderPrompt } from "./prompts.js";
