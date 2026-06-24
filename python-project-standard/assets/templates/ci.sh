#!/usr/bin/env bash
# 唯一的零警告门:人和 agent 共用的「是否完成」判据。任一项非零即整体失败。
set -euo pipefail

ruff format --check .
ruff check .
mypy .
python scripts/check_drift.py          # 文档/工件漂移守卫
CI=1 pytest                            # 运行时类型(beartype On)+ 行为 + 冒烟 + warnings-as-errors
echo "✓ 全绿"
