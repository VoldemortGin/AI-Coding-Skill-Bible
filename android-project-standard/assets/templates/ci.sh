#!/usr/bin/env bash
# 唯一的零警告门:人和 agent 共用的「是否完成」判据。任一项非零即整体失败。
# 顺序快→慢:格式(ktlint)→ lint(detekt)→ 编译(警告即错误)→ 测试(离线、Mock 默认)。
# 编译期 `allWarningsAsErrors = true` 在各 module 的 kotlin{} 块打开 —— 第 3 步即 -Werror。
set -euo pipefail

GRADLE="./gradlew --no-daemon --stacktrace"

# 1. 格式(ktlint;无输出即通过)
$GRADLE ktlintCheck

# 2. lint + 逃生舱禁令(detekt;`!!`/UnsafeCast/lateinit/GlobalScope 为 error)
$GRADLE detekt

# 3. 编译(allWarningsAsErrors=true → 警告即错误;编译 app + 其依赖的全部 JVM module)
$GRADLE compileDebugKotlin

# 4. 单元测试(离线、Mock 默认、含 smoke + conformance)
$GRADLE test

echo "✓ 全绿"
