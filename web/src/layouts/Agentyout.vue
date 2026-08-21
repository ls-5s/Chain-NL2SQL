<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  type ComponentPublicInstance,
} from "vue";
import {
  Clock3,
  Ellipsis,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Puzzle,
  Search,
  SquarePen,
  Trash2,
  X,
} from "lucide-vue-next";

import { provideAgentConversationStore } from "@/composables/agentConversations";

const AGENT_SIDEBAR_COLLAPSED_STORAGE_KEY = "chain-nl2sql-agent-sidebar-collapsed-v1";

const store = provideAgentConversationStore();
const searchQuery = ref("");
const searchOpen = ref(false);
const searchModalOpen = ref(false);
const searchInput = ref<HTMLInputElement | null>(null);
const drawerOpen = ref(false);
const desktopCollapsed = ref(readCollapsedPreference());
const conversationTitleRefs = new Map<string, HTMLSpanElement>();
const conversationTitleViewportRefs = new Map<string, HTMLSpanElement>();
const overflowingConversationIds = ref<Record<string, boolean>>({});
const conversationMarqueeDistances = ref<Record<string, number>>({});
let titleResizeObserver: ResizeObserver | null = null;
let measurementScheduled = false;

const filteredConversations = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase();
  if (!query) return store.recentConversations.value;
  return store.recentConversations.value.filter((conversation) =>
    conversation.title.toLocaleLowerCase().includes(query),
  );
});

function readCollapsedPreference() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(AGENT_SIDEBAR_COLLAPSED_STORAGE_KEY) === "true";
}

function setDesktopCollapsed(collapsed: boolean) {
  desktopCollapsed.value = collapsed;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(AGENT_SIDEBAR_COLLAPSED_STORAGE_KEY, String(collapsed));
  }
}

function openSidebar() {
  if (typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches) {
    drawerOpen.value = true;
    return;
  }
  setDesktopCollapsed(false);
}

function createConversation() {
  store.createConversation();
  drawerOpen.value = false;
}

function selectConversation(conversationId: string) {
  store.selectConversation(conversationId);
  drawerOpen.value = false;
  closeSearch();
}

function closeSearch() {
  searchQuery.value = "";
  searchOpen.value = false;
  searchModalOpen.value = false;
}

function openSearch() {
  if (typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches) {
    searchOpen.value = true;
    void nextTick(() => searchInput.value?.focus());
    return;
  }

  searchModalOpen.value = true;
  void nextTick(() => searchInput.value?.focus());
}

type TemplateRefValue = Element | ComponentPublicInstance | null;

function setConversationTitleRef(id: string, element: TemplateRefValue) {
  if (element instanceof HTMLSpanElement) {
    conversationTitleRefs.set(id, element);
  } else {
    conversationTitleRefs.delete(id);
  }
}

function setConversationTitleViewportRef(id: string, element: TemplateRefValue) {
  const previous = conversationTitleViewportRefs.get(id);
  if (previous && titleResizeObserver) titleResizeObserver.unobserve(previous);

  if (element instanceof HTMLSpanElement) {
    conversationTitleViewportRefs.set(id, element);
    titleResizeObserver?.observe(element);
  } else {
    conversationTitleViewportRefs.delete(id);
  }
}

function requestConversationTitleMeasurement() {
  if (measurementScheduled) return;
  measurementScheduled = true;
  void nextTick(() => {
    measurementScheduled = false;
    measureConversationTitles();
  });
}

function recordsEqual<T extends boolean | number>(left: Record<string, T>, right: Record<string, T>) {
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) return false;
  return leftKeys.every((key) => left[key] === right[key]);
}

function measureConversationTitles() {
  const nextOverflowing: Record<string, boolean> = {};
  const nextDistances: Record<string, number> = {};

  for (const conversation of filteredConversations.value) {
    const title = conversationTitleRefs.get(conversation.id);
    const viewport = conversationTitleViewportRefs.get(conversation.id);
    if (!title || !viewport) continue;

    const distance = Math.max(0, title.scrollWidth - viewport.clientWidth);
    nextOverflowing[conversation.id] = distance > 1;
    nextDistances[conversation.id] = distance;
  }

  if (!recordsEqual(overflowingConversationIds.value, nextOverflowing)) {
    overflowingConversationIds.value = nextOverflowing;
  }
  if (!recordsEqual(conversationMarqueeDistances.value, nextDistances)) {
    conversationMarqueeDistances.value = nextDistances;
  }
}

function isConversationTitleOverflowing(id: string) {
  return Boolean(overflowingConversationIds.value[id]);
}

function conversationTitleStyle(id: string): Record<string, string> {
  return { "--conversation-marquee-distance": `${conversationMarqueeDistances.value[id] ?? 0}px` };
}

watch(filteredConversations, requestConversationTitleMeasurement, { flush: "post" });

onMounted(() => {
  if (typeof ResizeObserver !== "undefined") {
    titleResizeObserver = new ResizeObserver(requestConversationTitleMeasurement);
    for (const viewport of conversationTitleViewportRefs.values())
      titleResizeObserver.observe(viewport);
  }
  window.addEventListener("resize", requestConversationTitleMeasurement);
  requestConversationTitleMeasurement();
});

onBeforeUnmount(() => {
  titleResizeObserver?.disconnect();
  window.removeEventListener("resize", requestConversationTitleMeasurement);
});
</script>

<template>
  <div class="agent-layout" :class="{ 'agent-layout--collapsed': desktopCollapsed }">
    <button
      class="agent-sidebar-toggle"
      type="button"
      aria-label="打开会话列表"
      title="打开会话列表"
      @click="openSidebar"
    >
      <PanelLeftOpen :size="19" aria-hidden="true" />
    </button>

    <button
      v-if="drawerOpen"
      class="agent-sidebar-backdrop"
      type="button"
      aria-label="关闭会话列表"
      @click="drawerOpen = false"
    />

    <aside
      class="agent-sidebar"
      :class="{ 'agent-sidebar--open': drawerOpen }"
      aria-label="会话列表"
    >
      <header class="agent-sidebar__header">
        <template v-if="searchOpen">
          <label class="agent-search">
            <Search :size="17" aria-hidden="true" />
            <input
              v-model="searchQuery"
              type="search"
              placeholder="搜索会话"
              aria-label="搜索会话"
            />
            <button type="button" aria-label="关闭搜索" title="关闭搜索" @click="closeSearch">
              <X :size="16" aria-hidden="true" />
            </button>
          </label>
        </template>
        <template v-else>
          <div class="agent-sidebar__brand" aria-label="Chain">
            <strong>Chain</strong>
          </div>
          <div class="agent-sidebar__header-actions">
            <button
              class="agent-sidebar__collapse"
              type="button"
              aria-label="收起会话列表"
              title="收起会话列表"
              @click="setDesktopCollapsed(true)"
            >
              <PanelLeftClose :size="19" aria-hidden="true" />
            </button>
            <button
              class="agent-sidebar__close"
              type="button"
              aria-label="关闭会话列表"
              title="关闭会话列表"
              @click="drawerOpen = false"
            >
              <X :size="19" aria-hidden="true" />
            </button>
          </div>
        </template>
      </header>

      <div class="agent-sidebar__body">
        <button
          class="agent-sidebar__new-button"
          type="button"
          :disabled="store.isBusy.value"
          @click="createConversation"
        >
          <SquarePen :size="20" :stroke-width="1.9" aria-hidden="true" />
          <span>新聊天</span>
        </button>

        <div v-if="store.initializationError.value" class="agent-sidebar__load-error" role="alert">
          <span>{{ store.initializationError.value }}</span>
          <button type="button" :disabled="store.isBusy.value" @click="store.initialize">
            重试加载
          </button>
        </div>

        <nav class="agent-sidebar__shortcuts" aria-label="Agent 功能">
          <button
            class="agent-sidebar__search-link"
            type="button"
            aria-label="搜索会话"
            title="搜索会话"
            @click="openSearch"
          >
            <Search :size="21" :stroke-width="1.8" aria-hidden="true" />搜索
          </button>
          <span aria-disabled="true"
            ><Clock3 :size="21" :stroke-width="1.8" aria-hidden="true" />已安排</span
          >
          <span aria-disabled="true"
            ><Puzzle :size="21" :stroke-width="1.8" aria-hidden="true" />插件</span
          >
          <span aria-disabled="true"
            ><Ellipsis :size="22" :stroke-width="2.2" aria-hidden="true" />更多</span
          >
        </nav>

        <section class="agent-sidebar__history" aria-label="最近会话">
          <h2>最近</h2>
          <p v-if="!filteredConversations.length" class="agent-sidebar__empty">没有匹配的会话</p>
          <ul v-else>
            <li v-for="conversation in filteredConversations" :key="conversation.id">
              <div
                class="agent-sidebar__conversation-row"
                :class="{
                  'agent-sidebar__conversation-row--active':
                    conversation.id === store.activeConversationId.value,
                }"
              >
                <button
                  class="agent-sidebar__conversation"
                  type="button"
                  :disabled="store.isBusy.value"
                  :title="conversation.title"
                  @click="selectConversation(conversation.id)"
                >
                  <span
                    class="agent-sidebar__conversation-title-viewport"
                    :ref="(element) => setConversationTitleViewportRef(conversation.id, element)"
                  >
                    <span
                      class="agent-sidebar__conversation-title"
                      :class="{
                        'agent-sidebar__conversation-title--overflowing':
                          isConversationTitleOverflowing(conversation.id),
                      }"
                      :style="conversationTitleStyle(conversation.id)"
                      :ref="(element) => setConversationTitleRef(conversation.id, element)"
                      >{{ conversation.title }}</span
                    >
                  </span>
                </button>
                <button
                  class="agent-sidebar__delete"
                  type="button"
                  :disabled="store.isBusy.value"
                  :aria-label="`删除会话 ${conversation.title}`"
                  title="删除会话"
                  @click="store.deleteConversation(conversation.id)"
                >
                  <Trash2 :size="15" aria-hidden="true" />
                </button>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </aside>

    <div
      v-if="searchModalOpen"
      class="agent-search-modal-layer"
      role="presentation"
      @mousedown.self="closeSearch"
    >
      <section
        class="agent-search-modal"
        role="dialog"
        aria-modal="true"
        aria-label="搜索会话"
        @keydown.esc="closeSearch"
      >
        <div class="agent-search-modal__header">
          <Search :size="22" aria-hidden="true" />
          <input
            ref="searchInput"
            v-model="searchQuery"
            type="search"
            placeholder="搜索..."
            aria-label="搜索会话"
          />
          <button type="button" aria-label="关闭搜索" title="关闭搜索" @click="closeSearch">
            <X :size="24" aria-hidden="true" />
          </button>
        </div>
        <div class="agent-search-modal__body">
          <h2>最近聊天</h2>
          <p v-if="!filteredConversations.length" class="agent-search-modal__empty">
            没有匹配的会话
          </p>
          <ul v-else>
            <li v-for="conversation in filteredConversations" :key="conversation.id">
              <button
                type="button"
                :disabled="store.isBusy.value"
                @click="selectConversation(conversation.id)"
              >
                <MessageCircle :size="24" :stroke-width="1.8" aria-hidden="true" />
                <span>{{ conversation.title }}</span>
              </button>
            </li>
          </ul>
        </div>
      </section>
    </div>

    <section class="agent-layout__content">
      <RouterView />
    </section>
  </div>
</template>

<style scoped>
.agent-layout {
  display: flex;
  width: 100%;
  min-width: 0;
  height: 100vh;
  min-height: 0;
  overflow: hidden;
  background: #ffffff;
  font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", system-ui, sans-serif;
  font-weight: 400;
  letter-spacing: 0;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

.agent-sidebar {
  z-index: 2;
  display: flex;
  width: 304px;
  flex: 0 0 304px;
  flex-direction: column;
  border-right: 1px solid #e6e6e6;
  background: #fbfbfb;
}

.agent-sidebar__header {
  display: flex;
  height: 62px;
  flex: 0 0 62px;
  align-items: center;
  gap: 10px;
  padding: 0 13px 0 16px;
}

.agent-sidebar__brand {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: baseline;
  gap: 5px;
  color: #202123;
}

.agent-sidebar__brand strong {
  font-size: 21px;
  font-weight: 700;
}

.agent-sidebar__header-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 3px;
}

.agent-sidebar__icon-button,
.agent-sidebar__collapse,
.agent-sidebar__close,
.agent-sidebar__new-button,
.agent-sidebar__search-link,
.agent-search button,
.agent-sidebar__delete {
  border: 0;
  background: transparent;
  font: inherit;
}

.agent-sidebar__icon-button,
.agent-sidebar__collapse,
.agent-sidebar__close {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 7px;
  color: #747474;
  cursor: pointer;
}

.agent-sidebar__icon-button:hover,
.agent-sidebar__icon-button:focus-visible,
.agent-sidebar__collapse:hover,
.agent-sidebar__collapse:focus-visible,
.agent-sidebar__close:hover,
.agent-sidebar__close:focus-visible {
  outline: 0;
  color: #202123;
  background: #eeeeee;
}

.agent-sidebar__close {
  display: none;
}

.agent-search {
  display: flex;
  width: 100%;
  height: 38px;
  align-items: center;
  gap: 8px;
  border: 1px solid #d7d7d7;
  border-radius: 7px;
  padding: 0 7px 0 10px;
  color: #757575;
  background: #ffffff;
}

.agent-search:focus-within {
  border-color: #8ba496;
  box-shadow: 0 0 0 3px rgba(65, 126, 96, 0.11);
}

.agent-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: #202123;
  background: transparent;
  font:
    21px "Microsoft YaHei",
    "PingFang SC",
    "Segoe UI",
    system-ui,
    sans-serif;
}

.agent-search button {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  border-radius: 5px;
  color: inherit;
  cursor: pointer;
}

.agent-search button:hover,
.agent-search button:focus-visible {
  outline: 0;
  background: #f0f0f0;
}

.agent-sidebar__body {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 1px 9px 16px;
  scrollbar-color: #cccccc transparent;
  scrollbar-width: thin;
}

.agent-sidebar__load-error {
  display: grid;
  gap: 8px;
  margin: 10px 5px 12px;
  border: 1px solid #f0d6d6;
  border-radius: 7px;
  padding: 10px;
  color: #9b3f3f;
  background: #fff7f7;
  font-size: 12px;
  line-height: 1.45;
}

.agent-sidebar__load-error button {
  width: fit-content;
  border: 0;
  border-radius: 5px;
  padding: 5px 8px;
  color: #8c3030;
  background: #f9e4e4;
  font: inherit;
  cursor: pointer;
}

.agent-sidebar__load-error button:hover:not(:disabled),
.agent-sidebar__load-error button:focus-visible {
  outline: 0;
  background: #f2d4d4;
}

.agent-sidebar__load-error button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.agent-sidebar__body::-webkit-scrollbar {
  width: 7px;
}

.agent-sidebar__body::-webkit-scrollbar-thumb {
  border-radius: 8px;
  background: #cccccc;
}

.agent-sidebar__new-button {
  display: flex;
  width: 100%;
  height: 43px;
  align-items: center;
  gap: 10px;
  border-radius: 10px;
  padding: 0 12px;
  color: #202123;
  background: #ebebeb;
  font-size: 21px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
}

.agent-sidebar__new-button:hover:not(:disabled),
.agent-sidebar__new-button:focus-visible:not(:disabled) {
  outline: 0;
  background: #e3e3e3;
}

.agent-sidebar__new-button:disabled,
.agent-sidebar__conversation:disabled,
.agent-sidebar__delete:disabled {
  cursor: default;
  opacity: 0.55;
}

.agent-sidebar__shortcuts {
  display: grid;
  gap: 1px;
  margin: 8px 0 25px;
}

.agent-sidebar__shortcuts a,
.agent-sidebar__shortcuts button,
.agent-sidebar__shortcuts span {
  display: flex;
  width: 100%;
  height: 38px;
  align-items: center;
  gap: 10px;
  border-radius: 7px;
  padding: 0 11px;
  color: #303030;
  font-size: 21px;
  line-height: 1;
  text-align: left;
  text-decoration: none;
}

.agent-sidebar__shortcuts a:hover,
.agent-sidebar__shortcuts a:focus-visible,
.agent-sidebar__shortcuts button:hover,
.agent-sidebar__shortcuts button:focus-visible {
  outline: 0;
  background: #eeeeee;
}

.agent-sidebar__shortcuts button {
  cursor: pointer;
}

.agent-sidebar__shortcuts span[aria-disabled="true"] {
  cursor: default;
}

.agent-sidebar__history {
  min-height: 0;
}

.agent-sidebar__history h2 {
  margin: 0;
  padding: 0 11px 9px;
  color: #919191;
  font-size: 17px;
  font-weight: 400;
}

.agent-sidebar__history ul {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-sidebar__conversation-row {
  position: relative;
  height: 38px;
  border-radius: 7px;
}

.agent-sidebar__conversation {
  display: flex;
  min-width: 0;
  width: 100%;
  height: 38px;
  align-items: center;
  border: 0;
  border-radius: 7px;
  padding: 0 35px 0 11px;
  color: #343434;
  background: transparent;
  font:
    21px "Microsoft YaHei",
    "PingFang SC",
    "Segoe UI",
    system-ui,
    sans-serif;
  text-align: left;
  cursor: pointer;
}

.agent-sidebar__conversation-title-viewport {
  display: block;
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  white-space: nowrap;
}

.agent-sidebar__conversation-title {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: top;
}

.agent-sidebar__conversation:hover .agent-sidebar__conversation-title--overflowing,
.agent-sidebar__conversation:focus-visible .agent-sidebar__conversation-title--overflowing {
  max-width: none;
  overflow: visible;
  text-overflow: clip;
  animation: conversation-marquee 7s linear infinite;
}

@keyframes conversation-marquee {
  0%,
  14% {
    transform: translateX(0);
  }

  48%,
  72% {
    transform: translateX(calc(-1 * var(--conversation-marquee-distance)));
  }

  86%,
  100% {
    transform: translateX(0);
  }
}

.agent-sidebar__conversation-row:hover,
.agent-sidebar__conversation-row:focus-within,
.agent-sidebar__conversation-row--active {
  outline: 0;
  background: #eeeeee;
}

.agent-sidebar__delete {
  position: absolute;
  top: 50%;
  right: 5px;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 5px;
  color: #777777;
  cursor: pointer;
  transform: translateY(-50%);
  opacity: 0;
}

.agent-sidebar__conversation-row:hover .agent-sidebar__delete,
.agent-sidebar__conversation-row:focus-within .agent-sidebar__delete,
.agent-sidebar__conversation-row--active .agent-sidebar__delete {
  opacity: 1;
}

.agent-sidebar__delete:hover:not(:disabled),
.agent-sidebar__delete:focus-visible:not(:disabled) {
  outline: 0;
  color: #a0424a;
  background: #f9e9ea;
}

.agent-sidebar__empty {
  margin: 16px 11px;
  color: #929292;
  font-size: 13px;
}

.agent-layout__content {
  min-width: 0;
  flex: 1;
}

.agent-sidebar-toggle,
.agent-sidebar-backdrop {
  display: none;
}

.agent-layout--collapsed .agent-sidebar {
  display: none;
}

.agent-layout--collapsed .agent-sidebar-toggle {
  position: fixed;
  top: 10px;
  left: 66px;
  z-index: 10;
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid #e4e4e4;
  border-radius: 7px;
  color: #4d4d4d;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  cursor: pointer;
}

.agent-sidebar-toggle:hover,
.agent-sidebar-toggle:focus-visible {
  outline: 0;
  color: #202b26;
  background: #ffffff;
}

.agent-search-modal-layer {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: rgba(30, 35, 32, 0.14);
}

.agent-search-modal {
  display: flex;
  width: min(1080px, calc(100vw - 64px));
  max-height: min(690px, calc(100vh - 64px));
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #d9d9d9;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.18);
}

.agent-search-modal__header {
  display: flex;
  min-height: 88px;
  align-items: center;
  gap: 14px;
  padding: 0 26px;
  color: #818181;
}

.agent-search-modal__header input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: #303030;
  background: transparent;
  font:
    21px "Microsoft YaHei",
    "PingFang SC",
    "Segoe UI",
    system-ui,
    sans-serif;
}

.agent-search-modal__header input::placeholder {
  color: #919191;
}

.agent-search-modal__header button {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border: 0;
  border-radius: 8px;
  color: #252525;
  background: transparent;
  cursor: pointer;
}

.agent-search-modal__header button:hover,
.agent-search-modal__header button:focus-visible {
  outline: 0;
  background: #f1f1f1;
}

.agent-search-modal__body {
  min-height: 0;
  overflow-y: auto;
  padding: 10px 26px 24px;
  scrollbar-color: #d0d0d0 transparent;
  scrollbar-width: thin;
}

.agent-search-modal__body::-webkit-scrollbar {
  width: 9px;
}

.agent-search-modal__body::-webkit-scrollbar-thumb {
  border-radius: 8px;
  background: #d4d4d4;
}

.agent-search-modal__body h2 {
  margin: 0 0 15px;
  color: #747474;
  font-size: 17px;
  font-weight: 400;
}

.agent-search-modal__body ul {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-search-modal__body li button {
  display: flex;
  width: 100%;
  min-height: 54px;
  align-items: center;
  gap: 18px;
  border: 0;
  border-radius: 9px;
  padding: 0 10px;
  color: #292929;
  background: transparent;
  font:
    21px "Microsoft YaHei",
    "PingFang SC",
    "Segoe UI",
    system-ui,
    sans-serif;
  text-align: left;
  cursor: pointer;
}

.agent-search-modal__body li button:hover,
.agent-search-modal__body li button:focus-visible {
  outline: 0;
  background: #f4f4f4;
}

.agent-search-modal__body li button:disabled {
  cursor: default;
  opacity: 0.55;
}

.agent-search-modal__empty {
  margin: 30px 10px;
  color: #999999;
  font-size: 16px;
}

@media (max-width: 760px) {
  .agent-search-modal-layer {
    display: none;
  }

  .agent-layout--collapsed .agent-sidebar {
    display: flex;
  }

  .agent-sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 56px;
    z-index: 91;
    width: min(304px, calc(100vw - 56px));
    flex-basis: min(304px, calc(100vw - 56px));
    box-shadow: 12px 0 28px rgba(0, 0, 0, 0.16);
    transform: translateX(calc(-100% - 8px));
    transition: transform 0.2s ease;
  }

  .agent-sidebar--open {
    transform: translateX(0);
  }

  .agent-sidebar__collapse {
    display: none;
  }

  .agent-sidebar__close {
    display: grid;
  }

  .agent-sidebar__brand strong {
    font-size: 19px;
  }

  .agent-search input,
  .agent-sidebar__new-button,
  .agent-sidebar__shortcuts a,
  .agent-sidebar__shortcuts span,
  .agent-sidebar__conversation {
    font-size: 18px;
  }

  .agent-sidebar-toggle,
  .agent-layout--collapsed .agent-sidebar-toggle {
    position: fixed;
    top: 10px;
    left: 66px;
    z-index: 10;
    display: grid;
    width: 36px;
    height: 36px;
    place-items: center;
    border: 1px solid #e4e4e4;
    border-radius: 7px;
    color: #4d4d4d;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    cursor: pointer;
  }

  .agent-sidebar-backdrop {
    position: fixed;
    inset: 0 0 0 56px;
    z-index: 90;
    display: block;
    border: 0;
    background: rgba(0, 0, 0, 0.26);
    cursor: pointer;
  }
}

@media (max-width: 520px) {
  .agent-sidebar {
    left: 52px;
    width: min(304px, calc(100vw - 52px));
    flex-basis: min(304px, calc(100vw - 52px));
  }

  .agent-sidebar-toggle,
  .agent-layout--collapsed .agent-sidebar-toggle {
    left: 62px;
  }

  .agent-sidebar-backdrop {
    inset: 0 0 0 52px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .agent-sidebar__conversation:hover .agent-sidebar__conversation-title--overflowing,
  .agent-sidebar__conversation:focus-visible .agent-sidebar__conversation-title--overflowing {
    animation: none;
  }
}
</style>
