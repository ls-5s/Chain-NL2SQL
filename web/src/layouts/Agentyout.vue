<script setup lang="ts">
import { computed, ref } from "vue";
import { Menu, MessageSquarePlus, Search, Sparkles, Trash2, X } from "lucide-vue-next";

import { getDemoUsername } from "@/auth/auth";
import { provideAgentConversationStore } from "@/composables/agentConversations";

const store = provideAgentConversationStore();
const currentUser = getDemoUsername();
const searchQuery = ref("");
const searchOpen = ref(false);
const drawerOpen = ref(false);

const filteredConversations = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase();
  if (!query) return store.recentConversations.value;
  return store.recentConversations.value.filter((conversation) =>
    conversation.title.toLocaleLowerCase().includes(query),
  );
});

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
  <div class="agent-layout">
    <button
      class="agent-sidebar-toggle"
      type="button"
      aria-label="打开会话列表"
      title="打开会话列表"
      @click="drawerOpen = true"
    >
      <Menu :size="20" aria-hidden="true" />
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
        <div class="agent-sidebar__brand">
          <span class="agent-sidebar__brand-mark" aria-hidden="true"><Sparkles :size="17" /></span>
          <span><strong>Chain</strong><small>数据助理</small></span>
        </div>
        <button
          class="agent-sidebar__close"
          type="button"
          aria-label="关闭会话列表"
          title="关闭会话列表"
          @click="drawerOpen = false"
        >
          <X :size="19" aria-hidden="true" />
        </button>
      </header>

      <div class="agent-sidebar__tools">
        <label v-if="searchOpen" class="agent-search">
          <Search :size="17" aria-hidden="true" />
          <input v-model="searchQuery" type="search" placeholder="搜索会话" aria-label="搜索会话" />
          <button type="button" aria-label="关闭搜索" title="关闭搜索" @click="closeSearch">
            <X :size="15" aria-hidden="true" />
          </button>
        </label>
        <button
          v-else
          class="agent-sidebar__icon-button"
          type="button"
          aria-label="搜索会话"
          title="搜索会话"
          @click="searchOpen = true"
        >
          <Search :size="18" aria-hidden="true" />
        </button>
        <button
          class="agent-sidebar__new-button"
          type="button"
          :disabled="store.isBusy.value"
          @click="createConversation"
        >
          <MessageSquarePlus :size="19" aria-hidden="true" />
          <span>新聊天</span>
        </button>
      </div>

      <section class="agent-sidebar__history" aria-label="最近会话">
        <h2>最近会话</h2>
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

      <footer class="agent-sidebar__account">
        <img src="/user-avatar.jpg" alt="" />
        <span>{{ currentUser }}</span>
      </footer>
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
  border-right: 1px solid #e8e8e8;
  background: #fbfbfb;
}

.agent-sidebar__header,
.agent-sidebar__tools,
.agent-sidebar__account {
  flex: 0 0 auto;
  padding-inline: 14px;
}

.agent-sidebar__header {
  display: flex;
  height: 64px;
  align-items: center;
  justify-content: space-between;
}

.agent-sidebar__brand {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 9px;
}

.agent-sidebar__brand-mark {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
  background: #202b26;
}

.agent-sidebar__brand strong,
.agent-sidebar__brand small {
  display: block;
}

.agent-sidebar__brand strong {
  color: #202123;
  font-size: 15px;
  font-weight: 700;
}

.agent-sidebar__brand small {
  margin-top: 1px;
  color: #888888;
  font-size: 11px;
}

.agent-sidebar__close {
  display: none;
}

.agent-sidebar__tools {
  display: flex;
  gap: 8px;
  padding-bottom: 13px;
}

.agent-sidebar__icon-button,
.agent-sidebar__new-button,
.agent-search,
.agent-search button,
.agent-sidebar__delete {
  border: 0;
  background: transparent;
  font: inherit;
}

.agent-sidebar__icon-button {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  place-items: center;
  border-radius: 8px;
  color: #5f6963;
  cursor: pointer;
}

.agent-sidebar__icon-button:hover,
.agent-sidebar__icon-button:focus-visible {
  outline: 0;
  color: #202b26;
  background: #eeeeee;
}

.agent-sidebar__new-button {
  display: flex;
  min-width: 0;
  height: 40px;
  flex: 1;
  align-items: center;
  gap: 9px;
  border-radius: 8px;
  padding: 0 12px;
  color: #202123;
  background: #eeeeee;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.agent-sidebar__new-button:hover:not(:disabled),
.agent-sidebar__new-button:focus-visible:not(:disabled) {
  outline: 0;
  background: #e4e4e4;
}

.agent-sidebar__new-button:disabled,
.agent-sidebar__conversation:disabled,
.agent-sidebar__delete:disabled {
  cursor: default;
  opacity: 0.55;
}

.agent-search {
  display: flex;
  width: 100%;
  height: 40px;
  align-items: center;
  gap: 7px;
  border: 1px solid #d8d8d8;
  border-radius: 8px;
  padding: 0 8px 0 11px;
  color: #727272;
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
  font: 13px var(--font-sans);
}

.agent-search button {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 5px;
  color: inherit;
  cursor: pointer;
}

.agent-search button:hover {
  background: #f0f0f0;
}

.agent-sidebar__history {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 9px 8px 18px;
}

.agent-sidebar__history h2 {
  margin: 0;
  padding: 0 7px 8px;
  color: #8a8a8a;
  font-size: 12px;
  font-weight: 600;
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
  padding: 0 34px 0 9px;
  color: #3f3f3f;
  background: transparent;
  font: 13px var(--font-sans);
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
  margin: 16px 7px;
  color: #929292;
  font-size: 13px;
}

.agent-sidebar__account {
  display: flex;
  height: 62px;
  align-items: center;
  gap: 9px;
  border-top: 1px solid #e8e8e8;
  color: #4b4b4b;
  font-size: 13px;
  font-weight: 600;
}

.agent-sidebar__account img {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
}

.agent-layout__content {
  min-width: 0;
  flex: 1;
}

.agent-sidebar-toggle,
.agent-sidebar-backdrop {
  display: none;
}

@media (max-width: 760px) {
  .agent-sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 52px;
    z-index: 91;
    width: min(304px, calc(100vw - 52px));
    flex-basis: min(304px, calc(100vw - 52px));
    box-shadow: 12px 0 28px rgba(0, 0, 0, 0.16);
    transform: translateX(calc(-100% - 8px));
    transition: transform 0.2s ease;
  }

  .agent-sidebar--open {
    transform: translateX(0);
  }

  .agent-sidebar__close {
    display: grid;
    width: 34px;
    height: 34px;
    place-items: center;
    border: 0;
    border-radius: 7px;
    color: #5e5e5e;
    background: transparent;
    cursor: pointer;
  }

  .agent-sidebar__close:hover,
  .agent-sidebar__close:focus-visible {
    outline: 0;
    background: #eeeeee;
  }

  .agent-sidebar-toggle {
    position: fixed;
    top: 10px;
    left: 62px;
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

  .agent-sidebar-backdrop {
    position: fixed;
    inset: 0 0 0 52px;
    z-index: 90;
    display: block;
    border: 0;
    background: rgba(0, 0, 0, 0.26);
    cursor: pointer;
  }
}
</style>
