"""入口:启动时配置日志一次,然后跑业务。用 `python -m <pkg>.cli` 或 console_script 运行。"""
from .core.logging import setup_logging


def main() -> None:
    setup_logging()
    # TODO: 业务逻辑(经 ports.factory 取 provider)
    

if __name__ == "__main__":
    main()
