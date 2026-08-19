"""High-precision, database-free intent rules used before the LLM gate."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.domain import QueryIntent


@dataclass(frozen=True)
class RuleDecision:
    intent: QueryIntent
    confidence: float
    reason: str


# These terms are intentionally conservative and do not inspect database Schema.
_DATA_ACTIONS = ("查询", "统计", "多少", "几个", "列出", "排行", "排名", "趋势", "平均", "总计", "汇总", "筛选", "比较", "分析", "最高", "最低", "超过", "找出")
_DATA_OBJECTS = ("用户", "订单", "商品", "产品", "销售", "金额", "客户", "价格", "数量", "销量")
_GENERAL_PATTERNS = ("你好", "您好", "嗨", "天气", "谢谢", "感谢", "写一封", "写个", "写一份", "翻译", "润色", "学习", "是什么", "解释", "故事", "健身", "推荐", "为什么", "代码", "改得")
_AMBIGUOUS_PATTERNS = ("帮我看看", "帮我查一下", "查一下", "看看", "最近业务", "帮我总结", "总结一下")
_DETAIL_TERMS = ("数量", "金额", "价格", "销量", "销售", "趋势", "排行", "排名", "平均", "总计", "本月", "今年", "最近", "每天", "每月")


def classify_by_rules(question: str) -> RuleDecision | None:
    """Return only high-precision decisions; return None for LLM fallback."""

    text = " ".join(question.strip().split()).lower()
    if not text:
        return RuleDecision(QueryIntent.CLARIFICATION, 1.0, "问题为空")

    if any(pattern in text for pattern in _GENERAL_PATTERNS) and not any(
        action in text for action in _DATA_ACTIONS
    ):
        return RuleDecision(QueryIntent.GENERAL_CHAT, 0.98, "命中通用问答或写作表达")

    if any(pattern in text for pattern in _AMBIGUOUS_PATTERNS):
        return RuleDecision(QueryIntent.CLARIFICATION, 0.92, "表达了查看或总结意图，但缺少明确查询目标")

    has_action = any(action in text for action in _DATA_ACTIONS)
    has_object = any(obj in text for obj in _DATA_OBJECTS)
    if "数据" in text and not has_object:
        return RuleDecision(QueryIntent.CLARIFICATION, 0.90, "只有泛化的数据对象，没有明确业务指标")
    if has_action and has_object and not ("分析" in text and not any(term in text for term in _DETAIL_TERMS)):
        return RuleDecision(QueryIntent.DATA_QUERY, 0.96, "同时包含数据查询动作和业务数据对象")

    # A business-data mention without a concrete operation is deliberately ambiguous.
    if has_object:
        return RuleDecision(QueryIntent.CLARIFICATION, 0.90, "提到了业务数据对象，但缺少明确查询目标")

    return None
