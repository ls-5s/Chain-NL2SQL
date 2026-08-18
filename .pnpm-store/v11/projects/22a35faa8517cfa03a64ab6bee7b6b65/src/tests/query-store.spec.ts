import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useQueryStore } from "@/stores/query";

describe("query store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("starts with a disabled submit action", () => {
    const store = useQueryStore();

    expect(store.canSubmit).toBe(false);
  });

  it("clears the active request state", () => {
    const store = useQueryStore();
    store.question = "查询订单数量";
    store.errorMessage = "请求失败";

    store.reset();

    expect(store.question).toBe("");
    expect(store.errorMessage).toBeNull();
  });
});
