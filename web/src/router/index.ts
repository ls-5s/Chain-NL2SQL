import { createRouter, createWebHistory } from "vue-router";

import { isAuthenticated } from "@/auth/auth";
import Agentyout from "@/layouts/Agentyout.vue";
import LoginView from "@/views/LoginView.vue";
import AgentView from "@/views/AgentView.vue";
import RagView from "@/views/RagView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/agent" },
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    {
      path: "/agent",
      name: "agent",
      component: Agentyout,
      meta: {
        navLabel: "Agent",
        navDescription: "智能数据助理",
      },
      children: [{ path: "", name: "agent-home", component: AgentView }],
    },

    {
      path: "/rag",
      name: "rag",
      component: RagView,
      meta: { navLabel: "RAG 资料库", navDescription: "检索增强知识管理" },
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
      : "/agent";
  }
  if (!authenticated) return { name: "login", query: { redirect: to.fullPath } };
  return true;
});
