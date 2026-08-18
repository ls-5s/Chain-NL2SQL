<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useQueryStore } from "@/stores/query";
const queryStore = useQueryStore();
const responseStatus = computed(() => queryStore.response?.status === "succeeded" ? "查询完成" : queryStore.response?.status === "blocked" ? "请求已拦截" : queryStore.response?.status === "failed" ? "查询失败" : "");
onMounted(() => queryStore.loadDatabases());
</script>
<template>
  <section class="mx-auto max-w-6xl space-y-5 p-4 pb-20 sm:p-6">
    <div><h1 class="text-xl font-semibold">查询工作台</h1><p class="mt-1 text-sm text-zinc-500">以受控方式将自然语言转换为只读数据请求。</p></div>
    <form class="surface space-y-4 p-4" @submit.prevent="queryStore.runQuery">
      <label class="block text-sm font-medium" for="database">目标数据库</label>
      <select id="database" v-model="queryStore.databaseId" class="w-full rounded-md border border-zinc-300 px-3 py-2"><option v-for="database in queryStore.databases" :key="database" :value="database">{{ database }}</option></select>
      <label class="block text-sm font-medium" for="question">查询问题</label>
      <textarea id="question" v-model="queryStore.question" rows="4" class="w-full rounded-md border border-zinc-300 p-3" placeholder="例如：查询本月销售额最高的五个商品" />
      <p v-if="queryStore.errorMessage" class="text-sm text-red-700">{{ queryStore.errorMessage }}</p>
      <button type="submit" :disabled="!queryStore.canSubmit" class="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-400">{{ queryStore.isLoading ? "查询中…" : "生成并执行" }}</button>
    </form>
    <div v-if="queryStore.response" class="grid gap-5 lg:grid-cols-[3fr_2fr]">
      <article class="surface p-4"><h2 class="section-title">{{ responseStatus }}</h2><p class="mt-3 text-sm leading-6 text-zinc-700">{{ queryStore.response.final_answer }}</p></article>
      <aside class="surface p-4"><h2 class="section-title">知识命中</h2><ul class="mt-3 space-y-3"><li v-for="hit in queryStore.response.knowledge_hits" :key="hit.document_id" class="border-b border-zinc-100 pb-3"><p class="text-sm font-medium">{{ hit.title }}</p><p class="mt-1 text-xs leading-5 text-zinc-500">{{ hit.excerpt }}</p></li></ul></aside>
    </div>
  </section>
</template>
