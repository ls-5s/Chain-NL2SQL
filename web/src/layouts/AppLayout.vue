<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  CircleHelp,
  Database,
  LibraryBig,
  Menu,
  Search,
  SquarePen,
  UserRound,
  X,
} from "lucide-vue-next";
import { getDemoUsername } from "@/auth/auth";

const router = useRouter();
const currentUser = getDemoUsername();
const mobileNavigation = ref<HTMLDialogElement | null>(null);

function openKnowledge() {
  void router.push("/knowledge");
}

function closeMobileNavigation() {
  mobileNavigation.value?.close();
}

function openMobileNavigation() {
  mobileNavigation.value?.showModal();
}

function handleAgentShortcut(event: KeyboardEvent) {
  const target = event.target;
  const isEditing =
    target instanceof HTMLElement &&
    (target.matches("input, textarea, select") || target.isContentEditable);

  if (isEditing || event.altKey || !event.ctrlKey || !event.shiftKey || event.code !== "KeyO")
    return;

  event.preventDefault();
  void router.push("/agent");
}

onMounted(() => window.addEventListener("keydown", handleAgentShortcut));
onBeforeUnmount(() => window.removeEventListener("keydown", handleAgentShortcut));
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand-lockup">
        <span class="brand-mark"><Database :size="18" :stroke-width="2" aria-hidden="true" /></span>
        <div>
          <strong>Chain-NL2SQL</strong>
          <span>数据语义工作台</span>
        </div>
      </div>

      <div class="header-actions">
        <label class="global-search">
          <Search :size="16" aria-hidden="true" />
          <input
            type="search"
            placeholder="搜索资料、字段或规则"
            aria-label="搜索资料、字段或规则"
          />
          <kbd>Ctrl K</kbd>
        </label>
        <button class="header-icon" type="button" aria-label="帮助" title="帮助">
          <CircleHelp :size="19" :stroke-width="1.8" aria-hidden="true" />
        </button>
        <span class="header-divider" aria-hidden="true" />
        <span class="service-status"><i aria-hidden="true" />服务正常</span>
        <button class="profile-button" type="button" :aria-label="currentUser" :title="currentUser">
          <UserRound :size="17" :stroke-width="1.8" aria-hidden="true" />
        </button>
      </div>

      <button class="mobile-menu" type="button" aria-label="打开导航" @click="openMobileNavigation">
        <Menu :size="20" aria-hidden="true" />
      </button>
    </header>

    <aside class="rail" aria-label="主导航">
      <RouterLink class="rail-logo" to="/query" aria-label="Chain-NL2SQL 首页" title="Chain-NL2SQL">
        <Database :size="27" :stroke-width="1.8" aria-hidden="true" />
      </RouterLink>

      <nav class="rail-nav">
        <RouterLink
          class="rail-link rail-link--agent"
          to="/agent"
          active-class="rail-link--active"
          aria-label="

          Agent 对话，打开 Agent"
          aria-describedby="agent-tooltip"
        >
          <SquarePen :size="24" :stroke-width="1.8" aria-hidden="true" />
          <span id="agent-tooltip" class="rail-tooltip" role="tooltip">
            <span>Agent 对话</span>
          </span>
        </RouterLink>
        <RouterLink
          class="rail-link rail-link--tooltip"
          to="/rag"
          active-class="rail-link--active"
          aria-label="RAG 资料库"
          aria-describedby="rag-tooltip"
        >
          <LibraryBig :size="25" :stroke-width="1.8" aria-hidden="true" />
          <span id="rag-tooltip" class="rail-tooltip rail-tooltip--label" role="tooltip">
            RAG 资料库
          </span>
        </RouterLink>
      </nav>

      <div class="rail-bottom">
        <button
          class="user-button"
          type="button"
          :aria-label="`${currentUser}，本地演示用户`"
          aria-describedby="user-tooltip"
        >
          <img src="/user-avatar.jpg" :alt="`${currentUser} 的头像`" />
          <span id="user-tooltip" class="user-tooltip" role="tooltip">{{ currentUser }}</span>
        </button>
      </div>
    </aside>

    <main class="app-main"><slot /></main>

    <dialog ref="mobileNavigation" class="mobile-navigation" @click.self="closeMobileNavigation">
      <div class="mobile-navigation__header">
        <span class="brand-mark"><Database :size="18" aria-hidden="true" /></span>
        <button
          class="header-icon"
          type="button"
          aria-label="关闭导航"
          @click="closeMobileNavigation"
        >
          <X :size="20" aria-hidden="true" />
        </button>
      </div>
      <nav class="mobile-navigation__links" aria-label="主导航">
        <RouterLink to="/agent" @click="closeMobileNavigation"
          ><SquarePen :size="19" />Agent</RouterLink
        >
        <RouterLink to="/rag" @click="closeMobileNavigation"
          ><LibraryBig :size="19" />RAG 资料库</RouterLink
        >
        <button
          type="button"
          @click="
            openKnowledge();
            closeMobileNavigation();
          "
        >
          新建资料
        </button>
      </nav>
    </dialog>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: #fafafa;
  color: #222222;
}

.app-header {
  position: fixed;
  inset: 0 0 auto 0;
  z-index: 30;
  display: flex;
  height: 64px;
  align-items: center;
  border-bottom: 1px solid #e9e9e9;
  padding: 0 28px;
  background: rgba(255, 255, 255, 0.96);
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
  background: #202b26;
}

.brand-lockup strong,
.brand-lockup span:not(.brand-mark) {
  display: block;
}

.brand-lockup strong {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
}

.brand-lockup span:not(.brand-mark) {
  margin-top: 2px;
  color: #818181;
  font-size: 11px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-left: auto;
}

.global-search {
  display: flex;
  width: min(31vw, 350px);
  height: 34px;
  align-items: center;
  gap: 8px;
  border: 1px solid #e2e2e2;
  border-radius: 7px;
  padding: 0 8px 0 10px;
  color: #8a8a8a;
  background: #ffffff;
}

.global-search:focus-within {
  border-color: #9db9aa;
  box-shadow: 0 0 0 3px rgba(65, 126, 96, 0.1);
}

.global-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: #333333;
  background: transparent;
  font-size: 12px;
}

.global-search input::placeholder {
  color: #a0a0a0;
}

kbd {
  border: 1px solid #e7e7e7;
  border-radius: 4px;
  padding: 2px 4px;
  color: #a0a0a0;
  background: #fafafa;
  font: 10px/1 var(--font-sans);
  white-space: nowrap;
}

.header-icon,
.mobile-menu {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 0;
  border-radius: 7px;
  color: #66716b;
  background: transparent;
  cursor: pointer;
}

.header-icon:hover,
.mobile-menu:hover {
  color: #202b26;
  background: #f3f5f3;
}

.header-divider {
  width: 1px;
  height: 20px;
  background: #e8e8e8;
}

.service-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #647069;
  font-size: 12px;
}

.service-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #32a26f;
  box-shadow: 0 0 0 3px #e7f6ee;
}

.profile-button {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid #e4dfd5;
  border-radius: 50%;
  color: #504739;
  background: #f6eddc;
  cursor: pointer;
}

.mobile-menu {
  display: none;
  margin-left: auto;
}

.rail {
  position: fixed;
  inset: 64px auto 0 0;
  z-index: 20;
  display: flex;
  width: 56px;
  flex-direction: column;
  align-items: center;
  border-right: 1px solid #ededed;
  background: #ffffff;
}

.rail-logo,
.rail-link,
.rail-button,
.user-button {
  display: grid;
  place-items: center;
  border: 0;
  color: #171717;
  background: transparent;
  cursor: pointer;
  text-decoration: none;
}

.rail-logo {
  width: 100%;
  height: 56px;
  border-bottom: 1px solid #f1f1f1;
}

.rail-logo:hover,
.rail-link:hover,
.rail-button:hover {
  color: #000000;
  background: #f6f6f6;
}

.rail-nav {
  display: flex;
  width: 100%;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding-top: 11px;
}

.rail-link,
.rail-button {
  width: 36px;
  height: 36px;
  border-radius: 7px;
}

.rail-link--active {
  color: #111111;
  background: #f0f0f0;
}

.rail-link--agent,
.rail-link--tooltip {
  position: relative;
}

.rail-tooltip {
  position: absolute;
  top: 50%;
  left: calc(100% + 16px);
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 9px 8px 15px;
  border-radius: 999px;
  color: #ffffff;
  background: #1f1f1f;
  box-shadow: 0 15px 28px rgba(0, 0, 0, 0.23);
  font-size: 16px;
  font-weight: 750;
  line-height: 1;
  pointer-events: none;
  transform: translate(-6px, -50%);
  opacity: 0;
  visibility: hidden;
  white-space: nowrap;
  transition:
    opacity 0.16s ease,
    transform 0.16s ease,
    visibility 0.16s;
}

.rail-tooltip kbd {
  border: 0;
  border-radius: 10px;
  padding: 5px 9px;
  color: #e0e0e0;
  background: #5e5e5e;
  font: inherit;
  font-weight: 700;
}

.rail-tooltip--label {
  padding: 10px 15px;
}

.rail-link--agent:hover .rail-tooltip,
.rail-link--agent:focus-visible .rail-tooltip,
.rail-link--tooltip:hover .rail-tooltip,
.rail-link--tooltip:focus-visible .rail-tooltip {
  visibility: visible;
  transform: translate(0, -50%);
  opacity: 1;
}

.rail-bottom {
  display: flex;
  width: 100%;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  margin-top: auto;
  padding-bottom: 14px;
}

.user-button {
  position: relative;
  overflow: visible;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #edf3f8;
}

.user-button img {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.user-tooltip {
  position: absolute;
  top: 50%;
  left: calc(100% + 12px);
  z-index: 40;
  padding: 7px 10px;
  border: 1px solid #303030;
  color: #272727;
  background: #ffffff;
  box-shadow: 0 2px 7px rgba(0, 0, 0, 0.08);
  font-size: 14px;
  font-weight: 500;
  line-height: 1;
  pointer-events: none;
  transform: translate(-4px, -50%);
  opacity: 0;
  visibility: hidden;
  white-space: nowrap;
  transition:
    opacity 0.16s ease,
    transform 0.16s ease,
    visibility 0.16s;
}

.user-button:hover .user-tooltip,
.user-button:focus-visible .user-tooltip {
  visibility: visible;
  transform: translate(0, -50%);
  opacity: 1;
}

.app-main {
  min-width: 0;
  min-height: calc(100vh - 64px);
  margin-top: 64px;
  margin-left: 56px;
  overflow: auto;
  background: #fafafa;
}

.mobile-navigation {
  display: none;
}

@media (max-width: 520px) {
  .app-header {
    height: 58px;
    padding-inline: 16px;
  }
  .header-actions {
    display: none;
  }
  .mobile-menu {
    display: grid;
  }
  .rail {
    display: none;
  }
  .app-main {
    min-height: calc(100vh - 58px);
    margin-top: 58px;
    margin-left: 0;
  }
  .mobile-navigation {
    position: fixed;
    inset: 0 auto 0 0;
    display: flex;
    width: min(82vw, 300px);
    height: 100dvh;
    flex-direction: column;
    border: 0;
    margin: 0;
    padding: 16px;
    color: #ffffff;
    background: #202b26;
    box-shadow: 12px 0 32px rgba(0, 0, 0, 0.2);
  }
  .mobile-navigation::backdrop {
    background: rgba(20, 26, 23, 0.42);
  }
  .mobile-navigation__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .mobile-navigation__header .header-icon {
    color: #dce5df;
  }
  .mobile-navigation__header .brand-mark {
    background: #f0f4f1;
    color: #202b26;
  }
  .mobile-navigation__links {
    display: grid;
    gap: 4px;
    margin-top: 34px;
  }
  .mobile-navigation__links a,
  .mobile-navigation__links button {
    display: flex;
    min-height: 42px;
    align-items: center;
    gap: 10px;
    border: 0;
    border-radius: 6px;
    padding: 0 10px;
    color: #dce5df;
    background: transparent;
    font-size: 14px;
    text-align: left;
    text-decoration: none;
    cursor: pointer;
  }
  .mobile-navigation__links a.router-link-active {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.12);
  }
}

/* Query pages use the full viewport; navigation remains in the left rail. */
.app-header {
  display: none;
}

.rail {
  inset: 0 auto 0 0;
}

.app-main {
  min-height: 100vh;
  margin-top: 0;
}

@media (max-width: 520px) {
  .rail {
    display: flex;
    width: 52px;
  }

  .rail-tooltip {
    display: none;
  }

  .app-main {
    min-height: 100vh;
    margin-top: 0;
    margin-left: 52px;
  }

  .mobile-navigation {
    display: none !important;
  }
}
</style>
