"""Create the deterministic Chinese e-commerce SQLite demo database."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

from app.demo import DEMO_TABLES


ROW_COUNT = 1000
_SEED_TABLES = (
    "用户", "商品分类", "供应商", "商品", "商品规格", "仓库", "收货地址", "用户分层", "库存",
    "库存流水", "购物车", "购物车明细", "订单", "订单明细", "支付记录", "退款记录", "物流单",
    "物流节点", "优惠券", "优惠券使用记录", "促销活动", "商品评价", "心愿单", "心愿单明细",
    "客服工单", "工单消息", "退货单", "退货明细", "会员积分账户", "积分流水",
)
_FOREIGN_KEY_COLUMNS = {
    "用户编号", "收货地址编号", "分类编号", "供应商编号", "商品编号", "商品规格编号",
    "仓库编号", "库存编号", "购物车编号", "订单编号", "订单明细编号", "支付记录编号",
    "物流单编号", "优惠券编号", "心愿单编号", "工单编号", "退货单编号", "积分账户编号",
}
_BOOLEAN_COLUMNS = {"是否默认", "是否选中", "是否异常", "可叠加", "是否匿名", "是否公开", "是否内部消息"}
_MONEY_COLUMNS = {"成本价", "销售价", "市场价", "采购价", "库存金额", "原价", "成交单价", "折扣金额", "税费金额", "商品金额", "运费金额", "优惠金额", "应付金额", "实付金额", "支付金额", "手续费", "退款金额", "优惠值", "最低消费金额", "预算金额", "已用预算", "期望价格"}
_INTEGER_MARKERS = ("数量", "积分", "排序", "层级", "得分", "天数", "容量", "图片", "附件", "优先级", "评分")


def initialize(database_path: Path, sql_path: Path) -> None:
    """Keep the public initializer API while rebuilding the Chinese schema."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(sql_path.read_text(encoding="utf-8"))
        if sql_path.name == "demo.sql":
            seed_demo_data(connection)
        connection.commit()
    finally:
        connection.close()


def seed_demo_data(connection: sqlite3.Connection, row_count: int = ROW_COUNT) -> None:
    """Populate all Chinese tables with related, deterministic business data."""
    if frozenset(_SEED_TABLES) != DEMO_TABLES:
        raise RuntimeError("Demo seed order must include every demo table exactly once.")
    for table in _SEED_TABLES:
        columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        rows = [tuple(_value_for(table, column, index) for column in columns) for index in range(1, row_count + 1)]
        connection.executemany(f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({placeholders})', rows)


def _value_for(table: str, column: str, index: int) -> Any:
    """Return a valid deterministic value; all foreign-key tables share 1,000 IDs."""
    timestamp = _timestamp(index)
    if column == "编号":
        return index
    if column == "上级分类编号":
        return None if index == 1 else ((index - 2) % 20) + 1
    if column in _FOREIGN_KEY_COLUMNS:
        return index
    if column in _BOOLEAN_COLUMNS:
        return int(index % 3 != 0)
    if column == "邮箱" or column == "联系邮箱":
        return f"demo{index:04d}@example.test"
    if "手机号" in column or column == "联系电话":
        return f"138{index:08d}"[-11:]
    if column == "经度":
        return round(116.0 + (index % 100) / 100, 6)
    if column == "纬度":
        return round(39.0 + (index % 100) / 100, 6)
    if column == "税率":
        return 0.13
    if column == "折扣比例":
        return round(0.70 + (index % 25) / 100, 2)
    if column in _MONEY_COLUMNS:
        return _money_value(table, column, index)
    if column == "重量克":
        return round(100 + index % 900 + 0.5, 2)
    if any(marker in column for marker in _INTEGER_MARKERS):
        return _integer_value(table, column, index)
    if column.endswith("时间") or column.endswith("日期"):
        return timestamp
    if column == "币种":
        return "CNY"
    if "状态" in column:
        return _status_value(table, column, index)
    if column in {"性别"}:
        return ("男", "女", "未知")[index % 3]
    if column in {"注册渠道", "渠道", "来源渠道", "支付渠道", "发放渠道", "使用渠道", "适用渠道"}:
        return ("小程序", "App", "官网", "线下门店")[index % 4]
    if column in {"省份", "收件省份"}:
        return ("广东省", "浙江省", "江苏省", "四川省", "北京市")[index % 5]
    if column in {"城市", "收件城市", "所在地", "注册地区"}:
        return ("深圳市", "杭州市", "南京市", "成都市", "北京市")[index % 5]
    if column in {"用户名称", "收件人", "联系人", "负责人", "操作人", "处理人", "受理人", "发送人", "签收人"}:
        return f"用户{index:04d}"
    if column == "商品名称" or column == "商品名称快照":
        return ("机械键盘", "显示器", "无线鼠标", "扩展坞")[index % 4] + f" {index:04d}"
    if column in {"品牌"}:
        return ("星云", "远航", "青岚", "极光")[index % 4]
    if column in {"支付方式"}:
        return ("微信支付", "支付宝", "银行卡", "余额支付")[index % 4]
    if column in {"承运商"}:
        return ("顺丰速运", "京东物流", "中通快递")[index % 3]
    if column in {"事件类型"}:
        return ("已揽收", "运输中", "派送中", "已签收")[index % 4]
    if column in {"变动类型"}:
        return ("采购入库", "订单出库", "盘点调整", "退货入库")[index % 4]
    if column in {"交易类型"}:
        return ("获取", "消耗", "冻结", "解冻")[index % 4]
    if column == "详细地址" or column == "收件详细地址" or column == "地址":
        return f"示例路{index % 100}号{index % 30 + 1:02d}室"
    if column == "出生日期":
        return f"{1980 + index % 25}-01-{index % 28 + 1:02d}"
    if column == "邮政编码":
        return f"{100000 + index % 900000:06d}"
    if column.endswith("号") or column.endswith("编码") or column.endswith("账户号"):
        return f"{table[:2]}{column[:2]}{index:06d}"
    if column in {"名称", "分层名称", "规格名称", "优惠券名称", "活动名称"}:
        return f"{table}{index:04d}"
    if column in {"描述", "商品描述", "备注", "主题", "标题", "评价内容", "消息内容", "事件说明", "商家回复", "失败原因", "取消原因", "退款原因", "退货原因", "质检结论"}:
        return f"{table}{column}示例{index:04d}"
    return f"{column}{index:04d}"


def _money_value(table: str, column: str, index: int) -> float:
    goods = round(80 + (index * 17.3) % 900, 2)
    if table == "订单":
        if column == "商品金额":
            return goods
        if column == "运费金额":
            return 0.0 if index % 5 else 12.0
        if column == "优惠金额":
            return round(goods * (0.05 if index % 4 else 0.15), 2)
        if column == "税费金额":
            return round(goods * 0.13, 2)
        if column == "应付金额":
            return round(goods + (0.0 if index % 5 else 12.0) + goods * 0.13 - goods * (0.05 if index % 4 else 0.15), 2)
        if column == "实付金额":
            return round(goods + (0.0 if index % 5 else 12.0) + goods * 0.13 - goods * (0.05 if index % 4 else 0.15), 2)
    if column == "退款金额":
        return round(goods * (0.2 if index % 3 else 0.8), 2)
    if column in {"优惠金额", "折扣金额"}:
        return round(goods * 0.1, 2)
    if column in {"成本价", "采购价"}:
        return round(goods * 0.62, 2)
    if column == "市场价":
        return round(goods * 1.2, 2)
    if column == "销售价" or column == "成交单价" or column == "原价" or column == "期望价格":
        return goods
    return round(5 + (index * 11.7) % 500, 2)


def _integer_value(table: str, column: str, index: int) -> int:
    if "评分" in column:
        return index % 5 + 1
    if "数量" in column:
        return 1 + index % 20
    if "积分" in column:
        return 100 + index * 10
    if column == "层级":
        return 1 + index % 3
    if column == "优先级":
        return 1 + index % 5
    return 1 + index % 100


def _status_value(table: str, column: str, index: int) -> str:
    values = {
        "账户状态": ("正常", "正常", "冻结"),
        "订单状态": ("已完成", "已完成", "待支付", "已取消"),
        "支付状态": ("支付成功", "支付成功", "待支付", "支付失败"),
        "履约状态": ("已签收", "运输中", "待发货"),
        "物流状态": ("已签收", "运输中", "待揽收"),
        "退款状态": ("退款完成", "审核中", "退款关闭"),
        "工单状态": ("已解决", "处理中", "待受理"),
        "退货状态": ("已完成", "待质检", "处理中"),
        "上架状态": ("已上架", "已上架", "已下架"),
        "库存状态": ("充足", "充足", "预警"),
        "审核状态": ("已通过", "待审核", "已拒绝"),
        "售后状态": ("无售后", "退款完成", "处理中"),
    }
    choices = values.get(column, ("有效", "有效", "停用"))
    return choices[index % len(choices)]


def _timestamp(index: int) -> str:
    return f"2026-{(index % 6) + 1:02d}-{(index % 28) + 1:02d}T{index % 24:02d}:{index % 60:02d}:00Z"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("data/demo.sqlite"))
    parser.add_argument("--sql", type=Path, default=Path("data/fixtures/demo.sql"))
    args = parser.parse_args()
    initialize(args.database, args.sql)


if __name__ == "__main__":
    main()
