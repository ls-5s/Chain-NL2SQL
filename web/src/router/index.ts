import { createRouter, createWebHistory } from "vue-router";
import KnowledgeBaseView from "@/views/KnowledgeBaseView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/knowledge" },
    { path: "/knowledge", name: "knowledge", component: KnowledgeBaseView, meta: { navLabel: "知识库", navDescription: "业务规则与数据字典" } },
  ],
});
