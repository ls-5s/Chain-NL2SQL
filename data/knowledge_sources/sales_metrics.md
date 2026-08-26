# 销售指标口径

## 销售额

销售额默认指已支付订单的订单金额汇总。查询销售额时，通常只统计 `orders.status = 'paid'` 的订单，并汇总 `orders.total_amount`。

## 订单明细金额

订单明细金额等于 `order_items.quantity * order_items.unit_price`。`unit_price` 是下单时的商品单价快照，不应直接用当前 `products.price` 替代历史明细价格。

## 订单金额与明细金额

`orders.total_amount` 是订单级金额快照；`order_items` 用于拆解订单中的商品、数量和单价。对同一订单进行明细汇总时，理论上应与订单金额保持一致，但统计订单数时应使用 `COUNT(DISTINCT orders.id)` 避免明细行造成重复计数。
