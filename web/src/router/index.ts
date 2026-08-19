import { createRouter, createWebHistory } from "vue-router";
import KnowledgeBaseView from "@/views/KnowledgeBaseView.vue";
import QueryView from "@/views/QueryView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/query" },
    { path: "/query", name: "query", component: QueryView, meta: { navLabel: "数据问答", navDescription: "自然语言查询" } },
    { path: "/knowledge", name: "knowledge", component: KnowledgeBaseView, meta: { navLabel: "知识库", navDescription: "业务规则与数据字典" } },
  ],
});
