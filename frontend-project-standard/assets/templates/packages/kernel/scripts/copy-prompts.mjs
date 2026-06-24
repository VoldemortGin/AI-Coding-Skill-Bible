// 把 src/prompts 下的 .md 提示词随构建复制到 dist/prompts,使 dist 产物的
// `new URL('./prompts/...', import.meta.url)` 能在运行时定位到模板。跨平台(纯 node)。

import { cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "src", "prompts");
const dest = join(here, "..", "dist", "prompts");

if (existsSync(src)) {
  cpSync(src, dest, { recursive: true });
}
