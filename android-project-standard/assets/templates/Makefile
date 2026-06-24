.PHONY: check fmt lint build test wrapper clean help

# 完成判据:一条门绿。
check:
	./ci.sh

# 就地格式化(写回)。
fmt:
	./gradlew --no-daemon ktlintFormat

# 只跑 lint(ktlint + detekt)。
lint:
	./gradlew --no-daemon ktlintCheck detekt

# 编译(警告即错误;app + 依赖的 JVM module)。
build:
	./gradlew --no-daemon compileDebugKotlin

# 全部单元测试(离线、Mock 默认)。
test:
	./gradlew --no-daemon test

# 生成 Gradle wrapper(首次;需本机装 gradle)。
wrapper:
	gradle wrapper --gradle-version 8.11.1

clean:
	./gradlew --no-daemon clean

help:
	@grep -E '^[a-zA-Z_-]+:.*' $(MAKEFILE_LIST) | grep -v '@grep' | awk 'BEGIN{FS=":"}{printf "  \033[36m%-10s\033[0m\n",$$1}'
