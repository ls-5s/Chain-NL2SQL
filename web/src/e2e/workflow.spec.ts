import { expect, test } from "@playwright/test";

test("runs a query and shows knowledge context", async ({ page }) => {
  const api = page.context().request;
  const login = await api.post("/api/v1/auth/login", {
    data: { username: "admin", password: "123456" },
  });
  expect(login.ok()).toBeTruthy();
  const upload = await api.post("/api/v1/knowledge", {
    multipart: {
      category: "指标口径",
      file: {
        name: "销售指标口径.md",
        mimeType: "text/markdown",
        buffer: Buffer.from("销售额 = 商品价格乘以数量。商品销售额按订单明细汇总。"),
      },
    },
  });
  expect(upload.status()).toBe(202);
  const uploaded = (await upload.json()) as { id: string };
  await expect
    .poll(
      async () => {
        const response = await api.get("/api/v1/knowledge");
        const documents = (await response.json()) as Array<{ id: string; status: string }>;
        return documents.find((document) => document.id === uploaded.id)?.status;
      },
      { timeout: 10_000 },
    )
    .toBe("indexed");

  await page.goto("/");
  await page.getByPlaceholder("例如：查询本月销售额最高的五个商品").fill("查询商品销售额");
  await page.getByRole("button", { name: "生成并执行" }).click();
  await expect(page.getByText("查询完成")).toBeVisible();
  await expect(page.getByText("知识命中")).toBeVisible();
  await expect(page.getByText("销售指标口径.md")).toBeVisible();
});
