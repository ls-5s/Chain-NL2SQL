"""Workflow construction boundary.

Nodes are introduced incrementally during P0. Keeping graph construction here avoids
mixing LangGraph wiring with node business logic.
"""

from __future__ import annotations


def build_query_graph() -> object:
    # 节点完成后只在此文件注册边和条件路由，保持节点实现可单独测试。
    raise NotImplementedError("Register graph nodes before building the workflow.")
