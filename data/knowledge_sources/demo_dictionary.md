# Demo 数据字典

## users

用户主表。`users.id` 是主键，`name` 是用户名称，`email` 是邮箱，`created_at` 是用户创建日期。

## products

商品目录。`products.id` 是主键，`name` 是商品名称，`category` 是商品分类，`price` 是当前商品价格。

## orders

订单主表。`orders.id` 是主键，`user_id` 关联 `users.id`，`status` 保存订单状态，`total_amount` 保存订单金额，`created_at` 保存下单日期。

## order_items

订单明细表。`order_items.id` 是主键，`order_id` 关联 `orders.id`，`product_id` 关联 `products.id`，`quantity` 是购买数量，`unit_price` 是下单时的单价快照。

## 关联关系

用户与订单通过 `orders.user_id = users.id` 关联。订单与商品通过 `order_items.order_id = orders.id` 和 `order_items.product_id = products.id` 关联。
