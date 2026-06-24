.PHONY: check fmt lint build test dev-test run app scaffold-xcode clean

# 完成判据:一条门绿。
check:
	./ci.sh

# 就地格式化(写回)。
fmt:
	swift format --in-place --recursive Sources Tests

# 只跑 lint。
lint:
	swift format lint --strict --recursive Sources Tests
	swiftlint --strict

# 构建(警告即错误)。
build:
	swift build -Xswiftc -warnings-as-errors

# 全部测试。
test:
	swift test

# 开发期快速测试(默认 build 配置)。
dev-test:
	swift test --parallel

# 跑 CLI demo(composition root)。
run:
	swift run __PACKAGE__

# 生成瘦 Xcode app 壳并打开。
app: scaffold-xcode
	open __PACKAGE__App.xcodeproj

# 用 XcodeGen 生成 .xcodeproj(link 本地 package 的 AppCore 库)。
scaffold-xcode:
	xcodegen generate

clean:
	rm -rf .build DerivedData __PACKAGE__App.xcodeproj
