// 结构化日志:分级、JSON 输出、敏感字段红化、血缘记录。浏览器 / node 双端安全
// (只用 console,不依赖 node 专属 API)。pino 等进阶 logger 可在此处替换实现而不动调用方。
//
// 隐私纪律:已知敏感字段(token / key / password / secret / authorization)在序列化前
// 红化为 "[REDACTED]";绝不打印原始 payload。

/** 日志级别(由低到高)。 */
export type LogLevel = "debug" | "info" | "warn" | "error";

/** 结构化字段:可序列化的任意键值。 */
export type LogFields = Record<string, unknown>;

const LEVEL_ORDER: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

/** 命中即红化的敏感字段名(小写匹配,子串)。 */
const SENSITIVE_KEYS = ["token", "key", "password", "secret", "authorization", "apikey"] as const;

function isSensitive(key: string): boolean {
  const lower = key.toLowerCase();
  return SENSITIVE_KEYS.some((needle) => lower.includes(needle));
}

/** 递归红化敏感字段(对象 / 数组深入;命中字段名即替换值)。 */
function redact(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(redact);
  }
  if (value !== null && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = isSensitive(k) ? "[REDACTED]" : redact(v);
    }
    return out;
  }
  return value;
}

/** 结构化 logger。 */
export interface Logger {
  debug(message: string, fields?: LogFields): void;
  info(message: string, fields?: LogFields): void;
  warn(message: string, fields?: LogFields): void;
  error(message: string, fields?: LogFields): void;
  /** 派生一个带固定上下文字段的子 logger。 */
  child(context: LogFields): Logger;
}

/** 一次 provider 调用的血缘元数据(用于审计「答案从哪来」)。 */
export interface Provenance {
  /** 数据来源(如 "embedder" / "llm" / "retriever")。 */
  readonly source: string;
  /** 具体实现名(如 "MockEmbedder")。 */
  readonly impl: string;
  /** 实现版本。 */
  readonly version: string;
  /** 处理 / 返回的条目数。 */
  readonly count: number;
}

/** 由 env 读取的最低输出级别(默认 info)。 */
function thresholdFromEnv(): LogLevel {
  const raw = typeof process !== "undefined" ? (process.env["LOG_LEVEL"]?.toLowerCase() ?? "") : "";
  if (raw === "debug" || raw === "info" || raw === "warn" || raw === "error") {
    return raw;
  }
  return "info";
}

function emit(level: LogLevel, threshold: LogLevel, message: string, fields: LogFields): void {
  if (LEVEL_ORDER[level] < LEVEL_ORDER[threshold]) {
    return;
  }
  const record = {
    level,
    time: new Date().toISOString(),
    message,
    ...(redact(fields) as LogFields),
  };
  const line = JSON.stringify(record);
  // 双端安全:console 在浏览器与 node 都存在;按级别分流。
  switch (level) {
    case "error":
      console.error(line);
      return;
    case "warn":
      console.warn(line);
      return;
    case "debug":
    case "info":
      console.log(line);
      return;
  }
}

/**
 * 造一个结构化 logger。
 *
 * @param context - 固定上下文字段(每条日志都带)。
 * @returns logger 实例。
 */
export function createLogger(context: LogFields = {}): Logger {
  const threshold = thresholdFromEnv();
  const make = (ctx: LogFields): Logger => ({
    debug: (message, fields) => {
      emit("debug", threshold, message, { ...ctx, ...fields });
    },
    info: (message, fields) => {
      emit("info", threshold, message, { ...ctx, ...fields });
    },
    warn: (message, fields) => {
      emit("warn", threshold, message, { ...ctx, ...fields });
    },
    error: (message, fields) => {
      emit("error", threshold, message, { ...ctx, ...fields });
    },
    child: (childCtx) => make({ ...ctx, ...childCtx }),
  });
  return make(context);
}

/** 默认 kernel logger。 */
export const logger: Logger = createLogger({ scope: "kernel" });

/**
 * 记录一次 provider 调用的血缘(码值 / 计数公开,绝不打印 payload)。
 *
 * @param provenance - 血缘元数据。
 * @param log - 目标 logger;默认 kernel logger。
 */
export function logProvenance(provenance: Provenance, log: Logger = logger): void {
  log.info("provenance", {
    source: provenance.source,
    impl: provenance.impl,
    version: provenance.version,
    count: provenance.count,
  });
}
