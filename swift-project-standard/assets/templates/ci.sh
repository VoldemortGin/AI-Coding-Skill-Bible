#!/usr/bin/env bash
# 唯一的零警告门:人和 agent 共用的「是否完成」判据。任一项非零即整体失败。
# 顺序快→慢:格式 → lint → 构建(警告即错误)→ 测试。默认离线、Mock 默认。
set -euo pipefail

# 1. 格式(无输出即通过)
swift format lint --strict --recursive Sources Tests

# 2. lint(逃生舱 force_unwrapping/force_try/force_cast 为 error)
swiftlint --strict

# 3. 构建(警告即错误)
swift build -Xswiftc -warnings-as-errors

# 4. 测试(离线、Mock 默认、含 smoke + conformance)
swift test

# 5.(app 场景,存在 .xcodeproj 时;先 `make scaffold-xcode` 生成)
# xcodebuild -scheme __PACKAGE__App -destination 'platform=iOS Simulator,name=iPhone 16' \
#   build test SWIFT_TREAT_WARNINGS_AS_ERRORS=YES SWIFT_STRICT_CONCURRENCY=complete

echo "✓ 全绿"
