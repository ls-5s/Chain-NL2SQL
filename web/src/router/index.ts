import { createRouter, createWebHistory } from "vue-router";

import { isAuthenticated } from "@/auth/auth";
import KnowledgeBaseView from "@/views/KnowledgeBaseView.vue";
import LoginView from "@/views/LoginView.vue";
import QueryView from "@/views/QueryView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/agent" },
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    {
      path: "/agent",
      name: "agent",
      component: QueryView,
      meta: { navLabel: "Agent", navDescription: "智能数据助理" },
    },
    {
      path: "/query",
      name: "query",
      component: QueryView,
      meta: { navLabel: "数据问答", navDescription: "自然语言查询" },
    },
    {
      path: "/rag",
      name: "rag",
      component: KnowledgeBaseView,
      meta: { navLabel: "RAG 资料库", navDescription: "检索增强知识管理" },
    },
    {
      path: "/knowledge",
      name: "knowledge",
      component: KnowledgeBaseView,
      meta: { navLabel: "知识库", navDescription: "业务规则与数据字典" },
    },
  ],
});

router.beforeEach((to) => {
  const authenticated = isAuthenticated();
  if (to.name === "login") {
    if (!authenticated) return true;
    const redirect = to.query.redirect;
    return typeof redirect === "string" &&
      redirect.startsWith("/") &&
      !redirect.startsWith("//") &&
      redirect !== "/login"
      ? redirect
      : "/query";
  }
  if (!authenticated) return { name: "login", query: { redirect: to.fullPath } };
  return true;
});
