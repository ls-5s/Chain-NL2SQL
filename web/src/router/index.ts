import { createRouter, createWebHistory } from "vue-router";

import QueryWorkspace from "@/views/QueryWorkspace.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "query-workspace", component: QueryWorkspace },
  ],
});
