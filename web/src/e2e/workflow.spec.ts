import { expect, test } from "@playwright/test";

test("runs a query and shows knowledge context", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("例如：查询本月销售额最高的五个商品").fill("查询商品销售额");
  await page.getByRole("button", { name: "生成并执行" }).click();
  await expect(page.getByText("查询完成")).toBeVisible();
  await expect(page.getByText("知识命中")).toBeVisible();
  await expect(page.getByText("销售指标口径.md")).toBeVisible();
});

test("processes a pending approval", async ({ page }) => {
  await page.goto("/approvals");
  await page.getByRole("button", { name: "通过" }).click();
  await page.getByRole("button", { name: "确认通过" }).click();
  await expect(page.getByText("已通过").first()).toBeVisible();
});

test("uploads a knowledge document", async ({ page }) => {
  await page.goto("/knowledge");
  const input = page.locator('input[type="file"]');
  await input.setInputFiles({ name: "退款规则.md", mimeType: "text/markdown", buffer: Buffer.from("退款按订单金额冲减") });
  await expect(page.getByText("退款规则.md")).toBeVisible();
});
