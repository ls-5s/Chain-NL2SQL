import { createRouter, createWebHistory } from "vue-router";

import QueryWorkspace from "@/views/QueryWorkspace.vue";
import ApprovalView from "@/views/ApprovalView.vue";
import KnowledgeBaseView from "@/views/KnowledgeBaseView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "query-workspace",
      component: QueryWorkspace,
    },
   
  ],
});
