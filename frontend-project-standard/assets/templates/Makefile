.PHONY: check install typecheck lint fmt format test build dev clean

# 完成判据:一条门绿。
check:
	./ci.sh

install:
	pnpm install

typecheck:
	pnpm turbo run typecheck

lint:
	pnpm turbo run lint

# 就地格式化(写回)。
fmt:
	pnpm run format

# 只检查格式(不写回)。
format:
	pnpm run format:check

test:
	pnpm turbo run test

build:
	pnpm turbo run build

# 起开发服务(两壳并行)。
dev:
	pnpm turbo run dev

clean:
	rm -rf node_modules .turbo **/dist **/.next **/.turbo **/node_modules **/coverage
