#!/usr/bin/env bash
# 唯一的零警告门:人和 agent 共用的「是否完成」判据。任一项非零即整体失败。
# 顺序快→慢:类型 → lint → 格式 → 测试 → 构建(两壳)。默认离线、Mock 默认。
set -euo pipefail

# 0. 依赖(锁文件冻结,保证可复现)
pnpm install --frozen-lockfile

# 1. 类型门:tsc --noEmit(各包)
pnpm turbo run typecheck

# 2. lint(类型感知;逃生舱 any/非空!/危险 as 为 error;--max-warnings 0)
pnpm turbo run lint

# 3. 格式(prettier --check;不写回)
pnpm run format:check

# 4. 测试(vitest run;离线、Mock 默认、含 smoke + conformance)
pnpm turbo run test

# 5. 构建(vite + next 两壳 + 包构建)
pnpm turbo run build

echo "✓ 全绿"
