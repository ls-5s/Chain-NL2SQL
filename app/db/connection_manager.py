"""管理 SQLite 连接的生命周期、中断和释放。"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def open_sqlite_readonly(database_path: str | Path) -> sqlite3.Connection:
    """为一次操作创建新的只读连接。"""

    # 构造 SQLite URI 前先解析相对路径。
    path = Path(database_path).expanduser().resolve()
    # 提前失败，避免 SQLite 创建文件或静默选择其他文件。
    if not path.is_file():
        raise FileNotFoundError("Configured SQLite database does not exist.")
    # mode=ro 即使后续误执行写操作也会由 SQLite 拒绝。
    uri = f"file:{path.as_posix()}?mode=ro"
    # 连接是短生命周期对象，并可能被超时回调使用。
    return sqlite3.connect(uri, uri=True, check_same_thread=False)
