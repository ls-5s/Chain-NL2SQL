<script setup lang="ts">
import { Database, ShieldCheck } from "lucide-vue-next";
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
    <main class="mx-auto min-w-0 max-w-[1520px]"><RouterView /></main>
  </div>
</template>
