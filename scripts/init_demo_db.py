"""根据 SQL fixture 创建确定性的 SQLite 演示数据库。"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def initialize(database_path: Path, sql_path: Path) -> None:
    # 确保本地运行和测试运行时目标目录都存在。
    database_path.parent.mkdir(parents=True, exist_ok=True)
    # 重建前删除旧文件，确保 fixture 输出确定。
    if database_path.exists():
        database_path.unlink()
    # 使用 sqlite3.executescript 一次应用 Schema 和种子数据。
    connection = sqlite3.connect(database_path)
    try:
        # 以 UTF-8 读取仓库中的 SQL fixture，保证文本处理一致。
        connection.executescript(sql_path.read_text(encoding="utf-8"))
        # 关闭文件前提交全部 Schema 和种子数据变更。
        connection.commit()
    finally:
        # 即使 fixture 执行失败也必须释放文件句柄。
        connection.close()


def main() -> None:
    # 暴露路径参数，便于测试和开发者指定临时数据库。
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("data/demo.sqlite"))
    parser.add_argument("--sql", type=Path, default=Path("data/fixtures/demo.sql"))
    args = parser.parse_args()
    initialize(args.database, args.sql)


if __name__ == "__main__":
    main()
