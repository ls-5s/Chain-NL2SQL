<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Check, ChevronDown, LoaderCircle, RefreshCw, Search, UploadCloud } from "lucide-vue-next";
import type { KnowledgeDocument } from "@/types/api";

const props = defineProps<{
  documents: KnowledgeDocument[];
  loading: boolean;
  refreshing: boolean;
  isAdmin: boolean;
  query: string;
  categoryFilter: string;
}>();

const emit = defineEmits<{
  (event: "update:query", value: string): void;
  (event: "update:categoryFilter", value: string): void;
  (event: "upload"): void;
  (event: "refresh"): void;
}>();

const categories = computed(() =>
  Array.from(new Set(props.documents.map((item) => item.category))).sort(),
);
const indexedCount = computed(
  () => props.documents.filter((item) => item.status === "indexed").length,
);
const processingCount = computed(
  () =>
    props.documents.filter((item) => item.status === "uploading" || item.status === "parsing")
      .length,
);
const failedCount = computed(
  () => props.documents.filter((item) => item.status === "failed").length,
);
const categoryOpen = ref(false);
const categoryMenu = ref<HTMLDivElement | null>(null);
const categoryOptions = computed(() => [
  { value: "all", label: "全部分类" },
  ...categories.value.map((item) => ({ value: item, label: item })),
]);
const selectedCategoryLabel = computed(
  () =>
    categoryOptions.value.find((item) => item.value === props.categoryFilter)?.label ?? "全部分类",
);

function selectCategory(value: string) {
  emit("update:categoryFilter", value);
  categoryOpen.value = false;
}
function toggleCategoryMenu() {
  categoryOpen.value = !categoryOpen.value;
}
function handleCategoryKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    categoryOpen.value = false;
    return;
  }
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    toggleCategoryMenu();
    return;
  }
  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
  event.preventDefault();
  const currentIndex = categoryOptions.value.findIndex(
    (item) => item.value === props.categoryFilter,
  );
  const offset = event.key === "ArrowDown" ? 1 : -1;
  const nextIndex =
    (currentIndex + offset + categoryOptions.value.length) % categoryOptions.value.length;
  selectCategory(categoryOptions.value[nextIndex].value);
}
function handleOutsidePointer(event: PointerEvent) {
  if (categoryMenu.value && !categoryMenu.value.contains(event.target as Node)) {
    categoryOpen.value = false;
  }
}
onMounted(() => window.addEventListener("pointerdown", handleOutsidePointer));
onBeforeUnmount(() => window.removeEventListener("pointerdown", handleOutsidePointer));
</script>

<template>
  <div class="rag-workspace" aria-label="RAG 资料库">
    <aside class="rag-sidebar" aria-label="资料库导航">
      <header class="rag-sidebar__header">
        <p class="eyebrow">KNOWLEDGE BASE</p>
        <h1>RAG 资料库</h1>
        <p>{{ documents.length }} 份资料</p>
      </header>
      <div class="rag-sidebar__body">
        <section class="rag-sidebar__stats" aria-label="资料库概览">
          <div>
            <strong>{{ documents.length }}</strong
            ><span>资料总数</span>
          </div>
          <div>
            <strong>{{ indexedCount }}</strong
            ><span>已完成索引</span>
          </div>
          <div>
            <strong>{{ processingCount }}</strong
            ><span>处理中</span>
          </div>
          <div>
            <strong>{{ failedCount }}</strong
            ><span>需要处理</span>
          </div>
        </section>
        <div class="filters">
          <label class="search-field">
            <Search :size="16" aria-hidden="true" />
            <input
              :value="query"
              type="search"
              placeholder="搜索文件名、分类或摘要"
              aria-label="搜索资料"
              @input="emit('update:query', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <div ref="categoryMenu" class="category-select">
            <button
              class="category-select__trigger"
              type="button"
              role="combobox"
              aria-label="按分类筛选"
              :aria-expanded="categoryOpen"
              aria-controls="category-options"
              @click="toggleCategoryMenu"
              @keydown="handleCategoryKeydown"
            >
              <span>{{ selectedCategoryLabel }}</span>
              <ChevronDown :class="{ 'category-select__chevron--open': categoryOpen }" :size="16" />
            </button>
            <Transition name="category-menu">
              <div
                v-if="categoryOpen"
                id="category-options"
                class="category-select__menu"
                role="listbox"
                aria-label="资料分类"
              >
                <p class="category-select__label">筛选分类</p>
                <button
                  v-for="option in categoryOptions"
                  :key="option.value"
                  class="category-select__option"
                  :class="{ 'category-select__option--active': option.value === categoryFilter }"
                  type="button"
                  role="option"
                  :aria-selected="option.value === categoryFilter"
                  @click="selectCategory(option.value)"
                >
                  <span>{{ option.label }}</span>
                  <Check v-if="option.value === categoryFilter" :size="15" />
                </button>
              </div>
            </Transition>
          </div>
        </div>
        <footer class="rag-sidebar__footer">
          <button
            class="primary-button"
            type="button"
            :disabled="!isAdmin"
            :title="!isAdmin ? '仅超级管理员可操作' : '上传资料'"
            @click="emit('upload')"
          >
            <UploadCloud :size="17" />上传资料
          </button>
          <button
            class="sidebar-refresh-button"
            type="button"
            title="刷新列表"
            aria-label="刷新列表"
            :disabled="loading || refreshing"
            @click="emit('refresh')"
          >
            <RefreshCw :class="{ spin: loading || refreshing }" :size="17" />刷新
          </button>
        </footer>
      </div>
    </aside>

    <section class="rag-content"><slot /></section>
  </div>
</template>

<style scoped>
.rag-workspace {
  display: flex;
  width: 100%;
  height: calc(100vh - 64px);
  min-width: 0;
  min-height: 680px;
  overflow: hidden;
  border: 1px solid #d9e0da;
  border-radius: 10px;
  background: #f9fbf9;
  box-shadow: 0 20px 50px rgba(22, 40, 29, 0.08);
}
.rag-sidebar {
  display: flex;
  width: 318px;
  height: 100%;
  min-width: 318px;
  min-height: 0;
  flex: 0 0 318px;
  flex-direction: column;
  border-right: 1px solid #263d31;
  color: #edf5ef;
  background: #182820;
}
.rag-sidebar__header {
  padding: 25px 22px 18px;
  border-bottom: 1px solid rgba(228, 241, 231, 0.1);
}
.rag-sidebar__header .eyebrow {
  margin-bottom: 7px;
  color: #8ab99a;
}
.rag-sidebar__header h1 {
  margin: 0;
  color: #f7fbf8;
  font-size: 24px;
  font-weight: 720;
}
.rag-sidebar__header p:last-child {
  margin: 12px 0 0;
  color: #9db0a3;
  font-size: 12px;
}
.rag-sidebar__body {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  overflow-y: auto;
  padding: 17px 13px 15px;
  scrollbar-color: #476150 transparent;
  scrollbar-width: thin;
}
.rag-sidebar__body::-webkit-scrollbar {
  width: 7px;
}
.rag-sidebar__body::-webkit-scrollbar-thumb {
  border-radius: 8px;
  background: #476150;
}
.rag-sidebar__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin: 0 3px 14px;
  border: 1px solid rgba(205, 226, 211, 0.18);
  background: rgba(5, 15, 10, 0.24);
}
.rag-sidebar__stats div {
  display: grid;
  gap: 4px;
  padding: 11px 12px;
  background: rgba(255, 255, 255, 0.03);
}
.rag-sidebar__stats strong {
  color: #eaf5ed;
  font-size: 19px;
}
.rag-sidebar__stats span {
  color: #9db0a3;
  font-size: 11px;
}
.rag-sidebar__footer {
  display: grid;
  gap: 10px;
  margin-top: auto;
  padding-top: 18px;
}
.rag-sidebar__footer .primary-button,
.rag-sidebar__footer .sidebar-refresh-button {
  width: 100%;
}
.rag-sidebar__footer .primary-button {
  border: 1px solid #9fd2aa;
  color: #143322;
  background: #b9e6c2;
}
.rag-sidebar__footer .primary-button:hover {
  border-color: #c8efd0;
  background: #c8efd0;
}
.rag-sidebar__footer .sidebar-refresh-button {
  border: 1px solid transparent;
  color: #9db0a3;
}
.rag-sidebar__footer .sidebar-refresh-button:hover:not(:disabled) {
  color: #eaf5ed;
  background: rgba(136, 194, 149, 0.14);
}
.rag-content {
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
  background: #f9fbf9;
}
.filters {
  display: grid;
  gap: 10px;
  padding: 0;
}
.rag-sidebar .search-field {
  min-height: 38px;
  border-color: rgba(205, 226, 211, 0.18);
  border-radius: 7px;
  color: #98b4a0;
  background: rgba(5, 15, 10, 0.24);
}
.rag-sidebar .search-field:focus-within {
  border-color: #80bf91;
  box-shadow: 0 0 0 3px rgba(128, 191, 145, 0.12);
}
.rag-sidebar .search-field input {
  color: #edf5ef;
  background: transparent;
}
.rag-sidebar .search-field input::placeholder {
  color: #789080;
}
.search-field {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 8px;
  border: 1px solid #dce4dd;
  border-radius: 6px;
  padding: 0 10px;
  color: #7b887f;
}
.search-field input {
  height: 36px;
  border: 0;
  outline: 0;
  color: #3f5045;
  background: #fff;
  font-size: 12px;
}
.search-field input {
  width: 100%;
}
.category-select {
  position: relative;
  width: 100%;
}
.category-select__trigger {
  display: flex;
  width: 100%;
  min-height: 48px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid rgba(205, 226, 211, 0.22);
  border-radius: 10px;
  padding: 0 13px 0 15px;
  color: #e1eee4;
  background: #1c3026;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    box-shadow 160ms ease;
}
.category-select__trigger:hover,
.category-select__trigger[aria-expanded="true"] {
  border-color: #78b58b;
  background: #21382b;
  box-shadow: 0 0 0 3px rgba(128, 191, 145, 0.1);
}
.category-select__chevron--open {
  transform: rotate(180deg);
}
.category-select__menu {
  position: absolute;
  z-index: 10;
  top: calc(100% + 8px);
  right: 0;
  left: 0;
  display: grid;
  gap: 3px;
  border: 1px solid #3a5a46;
  border-radius: 11px;
  padding: 7px;
  background: #20372a;
  box-shadow: 0 16px 28px rgba(3, 12, 7, 0.32);
}
.category-select__label {
  margin: 2px 8px 4px;
  color: #86a995;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
}
.category-select__option {
  display: flex;
  min-height: 38px;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 0;
  border-radius: 7px;
  padding: 0 9px;
  color: #c1d2c5;
  background: transparent;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}
.category-select__option:hover,
.category-select__option:focus-visible {
  color: #eff8f0;
  background: #2a4a37;
  outline: 0;
}
.category-select__option--active {
  color: #eaffed;
  background: #326d4c;
  font-weight: 700;
}
.category-menu-enter-active,
.category-menu-leave-active {
  transition:
    opacity 140ms ease,
    transform 140ms ease;
  transform-origin: top center;
}
.category-menu-enter-from,
.category-menu-leave-to {
  opacity: 0;
  transform: translateY(-5px) scale(0.98);
}
.sidebar-refresh-button {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 10px;
  padding: 0 12px;
  color: #555b57;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
.sidebar-refresh-button:hover:not(:disabled) {
  color: #202123;
  background: #eeeeee;
}
.sidebar-refresh-button:disabled {
  cursor: default;
  opacity: 0.55;
}
.primary-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 7px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
}
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 1100px) {
  .rag-workspace {
    display: block;
    height: auto;
    min-height: 0;
  }
  .rag-sidebar {
    width: auto;
    height: auto;
    min-width: 0;
    flex: none;
    border-right: 0;
    border-bottom: 1px solid #263d31;
    padding: 14px 12px 12px;
  }
  .rag-sidebar__body {
    display: block;
    overflow: visible;
    padding: 0;
  }
  .rag-sidebar__footer {
    display: flex;
    margin-top: 12px;
    padding-top: 0;
  }
  .rag-sidebar__footer > button {
    flex: 1;
  }
  .rag-content {
    overflow: visible;
  }
}
@media (max-width: 700px) {
  .rag-sidebar__footer {
    display: grid;
  }
  .rag-sidebar__footer > button {
    width: 100%;
  }
}
</style>
