from __future__ import annotations

from app.graph.state import NL2SQLState


def make_finalize_node():
    def finalize(state: NL2SQLState) -> dict[str, object]:
        if state.get("final_answer"):
            return {"final_answer": state["final_answer"]}
        if state["status"] == "succeeded":
            result = state.get("query_result")
            return {"final_answer": f"查询完成，共返回 {result.row_count if result else 0} 行结果。"}
        return {"final_answer": state.get("safe_error") or "查询未完成。"}

    return finalize
