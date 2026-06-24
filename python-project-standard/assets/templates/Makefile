check:                    # 完整门禁(唯一正确性判据);也可直接 ./ci.sh
	./ci.sh

dev-test:                 # 本地快速迭代:beartype 走 O1
	pytest

fmt:
	ruff format .
	ruff check --fix .
