import { createRouter, createWebHistory } from "vue-router";

import { isAuthenticated } from "@/auth/auth";
import Agentyout from "@/layouts/Agentyout.vue";
import LoginView from "@/views/LoginView.vue";
import AgentView from "@/views/AgentView.vue";
import RagView from "@/views/RagView.vue";
import DatabasesView from "@/views/DatabasesView.vue";
import McpView from "@/views/McpView.vue";
import MembersView from "@/views/MembersView.vue";

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
    {
      path: "/databases",
      name: "databases",
      component: DatabasesView,
      meta: { navLabel: "数据库", navDescription: "数据库资源管理" },
    },
    {
      path: "/mcp",
      name: "mcp",
      component: McpView,
      meta: { navLabel: "MCP", navDescription: "MCP 工具连接" },
    },
    {
      path: "/members",
      name: "members",
      component: MembersView,
      meta: { navLabel: "成员", navDescription: "成员与权限管理" },
    },
  ],
});

router.beforeEach(async (to) => {
  const authenticated = await isAuthenticated();
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
