"""类型化路径。两类分开:

- 包内自带资源(随发行物出厂的只读文件):用 importlib.resources 定位。
- 运行期可写目录(data/logs):从 settings 取,不写在包代码旁边。
"""
from importlib.resources import files
from pathlib import Path

from .settings import settings

_PKG = __name__.split(".")[0]  # 顶层包名,重命名安全

DATA_DIR: Path = settings.data_dir
LOG_DIR: Path = settings.log_dir


def resource_path(relative: str) -> Path:
    """包内自带资源的路径(假设文件系统安装,如 Docker/服务器部署)。

    zip 安装场景请改用 importlib.resources.as_file 上下文管理器。
    """
    return Path(str(files(_PKG))) / relative
