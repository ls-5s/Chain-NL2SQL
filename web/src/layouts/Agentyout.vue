<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Clock3,
  Ellipsis,
  Folder,
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
const drawerOpen = ref(false);
const desktopCollapsed = ref(readCollapsedPreference());

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
}

function closeSearch() {
  searchQuery.value = "";
  searchOpen.value = false;
}
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

    <aside class="agent-sidebar" :class="{ 'agent-sidebar--open': drawerOpen }" aria-label="会话列表">
      <header class="agent-sidebar__header">
        <template v-if="searchOpen">
          <label class="agent-search">
            <Search :size="17" aria-hidden="true" />
            <input v-model="searchQuery" type="search" placeholder="搜索会话" aria-label="搜索会话" />
            <button type="button" aria-label="关闭搜索" title="关闭搜索" @click="closeSearch">
              <X :size="16" aria-hidden="true" />
            </button>
          </label>
        </template>
        <template v-else>
          <div class="agent-sidebar__brand" aria-label="Chain 数据助理">
            <strong>Chain</strong><span>数据助理</span>
          </div>
          <div class="agent-sidebar__header-actions">
            <button
              class="agent-sidebar__icon-button"
              type="button"
              aria-label="搜索会话"
              title="搜索会话"
              @click="searchOpen = true"
            >
              <Search :size="19" aria-hidden="true" />
            </button>
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

        <nav class="agent-sidebar__shortcuts" aria-label="Agent 功能">
          <span aria-disabled="true"><Folder :size="21" :stroke-width="1.8" aria-hidden="true" />项目</span>
          <span aria-disabled="true"><Clock3 :size="21" :stroke-width="1.8" aria-hidden="true" />已安排</span>
          <span aria-disabled="true"><Puzzle :size="21" :stroke-width="1.8" aria-hidden="true" />插件</span>
          <span aria-disabled="true"><Ellipsis :size="22" :stroke-width="2.2" aria-hidden="true" />更多</span>
        </nav>

        <section class="agent-sidebar__history" aria-label="最近会话">
          <h2>最近</h2>
          <p v-if="!filteredConversations.length" class="agent-sidebar__empty">没有匹配的会话</p>
          <ul v-else>
            <li v-for="conversation in filteredConversations" :key="conversation.id">
              <div
                class="agent-sidebar__conversation-row"
                :class="{ 'agent-sidebar__conversation-row--active': conversation.id === store.activeConversationId.value }"
              >
                <button
                  class="agent-sidebar__conversation"
                  type="button"
                  :disabled="store.isBusy.value"
                  :title="conversation.title"
                  @click="selectConversation(conversation.id)"
                >
                  <span>{{ conversation.title }}</span>
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
  font-size: 20px;
  font-weight: 700;
}

.agent-sidebar__brand span {
  color: #8b8b8b;
  font-size: 18px;
  font-weight: 400;
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
  font: 14px var(--font-sans);
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
  font-size: 15px;
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
.agent-sidebar__shortcuts span {
  display: flex;
  height: 38px;
  align-items: center;
  gap: 10px;
  border-radius: 7px;
  padding: 0 11px;
  color: #303030;
  font-size: 15px;
  line-height: 1;
  text-decoration: none;
}

.agent-sidebar__shortcuts a:hover,
.agent-sidebar__shortcuts a:focus-visible {
  outline: 0;
  background: #eeeeee;
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
  font-size: 14px;
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
  width: 100%;
  height: 38px;
  align-items: center;
  border: 0;
  border-radius: 7px;
  padding: 0 35px 0 11px;
  color: #343434;
  background: transparent;
  font: 14px var(--font-sans);
  text-align: left;
  cursor: pointer;
}

.agent-sidebar__conversation > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

@media (max-width: 760px) {
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
</style>
