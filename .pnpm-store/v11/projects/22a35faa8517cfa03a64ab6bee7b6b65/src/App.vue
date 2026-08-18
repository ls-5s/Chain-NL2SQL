<script setup lang="ts">
import { Database, FileStack, ShieldCheck, Workflow } from "lucide-vue-next";

const navigation = [
  { label: "查询工作台", to: "/", icon: Workflow },
  { label: "审批中心", to: "/approvals", icon: ShieldCheck },
  { label: "知识库", to: "/knowledge", icon: FileStack },
];
</script>

<template>
  <div class="min-h-screen bg-stone-100 text-zinc-900">
    <header class="sticky top-0 z-20 border-b border-zinc-200 bg-white">
      <div class="mx-auto flex h-14 max-w-[1520px] items-center gap-3 px-4 sm:px-6">
        <div class="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-teal-700 text-white" aria-hidden="true"><Database :size="17" /></div>
        <span class="text-sm font-semibold">Chain-NL2SQL</span>
        <span class="hidden border-l border-zinc-200 pl-3 text-xs text-zinc-500 sm:inline">受控查询与知识上下文演示</span>
        <div class="ml-auto flex items-center gap-1 text-xs text-teal-800"><ShieldCheck :size="15" aria-hidden="true" />本地只读模式</div>
      </div>
    </header>
    <div class="mx-auto flex max-w-[1520px]">
      <aside class="hidden w-56 shrink-0 border-r border-zinc-200 bg-white p-3 md:block">
        <nav class="space-y-1" aria-label="主导航">
          <RouterLink v-for="item in navigation" :key="item.to" :to="item.to" class="nav-link">
            <component :is="item.icon" :size="17" aria-hidden="true" />{{ item.label }}
          </RouterLink>
        </nav>
      </aside>
      <main class="min-w-0 flex-1"><RouterView /></main>
    </div>
    <nav class="fixed inset-x-0 bottom-0 z-20 flex border-t border-zinc-200 bg-white p-1 md:hidden" aria-label="移动主导航">
      <RouterLink v-for="item in navigation" :key="item.to" :to="item.to" class="mobile-nav-link">
        <component :is="item.icon" :size="17" aria-hidden="true" />{{ item.label }}
      </RouterLink>
    </nav>
  </div>
</template>
