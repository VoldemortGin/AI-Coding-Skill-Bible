#!/usr/bin/env bash
# 唯一的零警告门:人和 agent 共用的「是否完成」判据。任一项非零即整体失败。
set -euo pipefail

cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings   # 警告即错误
RUSTDOCFLAGS="-D warnings" cargo doc --no-deps --all-features
cargo test --all-features                                  # 单测 + 文档测试 + 冒烟
cargo deny check                                           # license / 安全 / 依赖
echo "✓ 全绿"
