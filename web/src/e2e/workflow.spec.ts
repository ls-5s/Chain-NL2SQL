import { expect, test } from "@playwright/test";

test("runs a query and shows knowledge context", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("例如：查询本月销售额最高的五个商品").fill("查询商品销售额");
  await page.getByRole("button", { name: "生成并执行" }).click();
  await expect(page.getByText("查询完成")).toBeVisible();
  await expect(page.getByText("知识命中")).toBeVisible();
  await expect(page.getByText("销售指标口径.md")).toBeVisible();
});
