// node 专属:从 configs/settings.json 读取文件层配置。浏览器侧绝不 import 本模块
// (它静态依赖 node 内置)。文件不存在 → 空对象(用默认值);文件存在但非法 → 抛错
// (不静默吞掉)。

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { fileSchema, type FileConfig } from "./config.js";

/**
 * 从工作目录的 `configs/settings.json` 读取并校验文件层配置。
 *
 * @param cwd - 项目根目录;默认 `process.cwd()`。
 * @returns 校验后的文件层配置;文件不存在时返回空对象。
 * @throws {z.ZodError} 文件存在但内容不合法时。
 * @throws {Error} 文件存在但 JSON 损坏时。
 */
export function readSettingsFile(cwd: string = process.cwd()): FileConfig {
  const file = join(cwd, "configs", "settings.json");
  if (!existsSync(file)) {
    return {};
  }
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(file, "utf8"));
  } catch (error) {
    throw new Error(`failed to parse configs/settings.json: ${String(error)}`);
  }
  return fileSchema.parse(raw);
}
