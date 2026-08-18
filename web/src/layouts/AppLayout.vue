<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  BookOpenText,
  ChevronRight,
  CircleHelp,
  Database,
  FileStack,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-vue-next";

const router = useRouter();
const collapsed = ref(false);
const mobileOpen = ref(false);
function openKnowledge() {
  mobileOpen.value = false;
  router.push("/knowledge");
}
function toggleCollapsed() {
  collapsed.value = !collapsed.value;
  localStorage.setItem("chain-sidebar-collapsed", String(collapsed.value));
}
onMounted(() => {
  collapsed.value = localStorage.getItem("chain-sidebar-collapsed") === "true";
});
watch(
  () => router.currentRoute.value.fullPath,
  () => {
    mobileOpen.value = false;
  },
);
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="app-header__inner">
        <button class="icon-button mobile-menu" aria-label="打开导航" @click="mobileOpen = true">
          <Menu :size="20" />
        </button>
        <div class="brand-lockup">
          <div class="brand-mark"><Database :size="19" :stroke-width="2.25" /></div>
          <div>
            <p class="brand-name">Chain-NL2SQL</p>
            <p class="brand-context">数据语义工作台</p>
          </div>
        </div>
        <div class="app-header__actions">
          <label class="global-search"
            ><Search :size="16" aria-hidden="true" /><input
              type="search"
              placeholder="搜索资料、字段或规则"
              aria-label="搜索资料、字段或规则"
            /><kbd>⌘ K</kbd></label
          ><button class="icon-button header-help" aria-label="帮助">
            <CircleHelp :size="18" />
          </button>
          <div class="header-divider" />
          <div class="status-indicator"><span />服务正常</div>
          <button class="profile-button" aria-label="本地工作区账户">
            <UserRound :size="17" />
          </button>
        </div>
      </div>
    </header>
    <div class="app-body">
      <aside class="sidebar" :class="{ 'sidebar--collapsed': collapsed }">
        <div class="sidebar__top">
          <button
            class="sidebar-collapse icon-button"
            :title="collapsed ? '展开侧栏' : '收起侧栏'"
            @click="toggleCollapsed"
          >
            <PanelLeftOpen v-if="collapsed" :size="18" /><PanelLeftClose
              v-else
              :size="18"
            /></button
          ><button
            class="create-button"
            :class="{ 'create-button--icon': collapsed }"
            :title="collapsed ? '新建资料' : undefined"
            @click="openKnowledge"
          >
            <Plus :size="18" /><span v-if="!collapsed">新建资料</span>
          </button>
        </div>
        <nav class="sidebar-nav" aria-label="主导航">
          <p v-if="!collapsed" class="sidebar-label">工作空间</p>
          <RouterLink
            to="/knowledge"
            class="nav-item"
            active-class="nav-item--active"
            :title="collapsed ? '知识库' : undefined"
            ><FileStack :size="18" /><span v-if="!collapsed">知识库</span
            ><ChevronRight v-if="!collapsed" class="nav-item__arrow" :size="16"
          /></RouterLink>
        </nav>
        <div class="sidebar__bottom">
          <div v-if="!collapsed" class="security-note">
            <span class="security-note__icon"><ShieldCheck :size="16" /></span>
            <div>
              <strong>受控访问</strong>
              <p>当前工作区为本地只读模式</p>
            </div>
          </div>
          <button
            class="nav-item nav-item--muted"
            :class="{ 'nav-item--centered': collapsed }"
            :title="collapsed ? '设置' : undefined"
          >
            <Settings2 :size="18" /><span v-if="!collapsed">设置</span>
          </button>
          <div class="workspace-user" :class="{ 'workspace-user--centered': collapsed }">
            <span class="workspace-user__avatar">A</span
            ><span v-if="!collapsed"><strong>本地工作区</strong><small>Administrator</small></span>
          </div>
        </div>
      </aside>
      <main class="app-main"><slot /></main>
    </div>
    <div v-if="mobileOpen" class="mobile-overlay">
      <button class="mobile-overlay__backdrop" aria-label="关闭导航" @click="mobileOpen = false" />
      <aside class="mobile-drawer">
        <div class="mobile-drawer__top">
          <div class="brand-mark"><BookOpenText :size="18" /></div>
          <button class="icon-button" aria-label="关闭导航" @click="mobileOpen = false">
            <X :size="19" />
          </button>
        </div>
        <button class="create-button" @click="openKnowledge"><Plus :size="18" />新建资料</button>
        <nav class="mobile-drawer__nav" aria-label="主导航">
          <RouterLink
            to="/knowledge"
            class="nav-item"
            active-class="nav-item--active"
            @click="mobileOpen = false"
            ><FileStack :size="18" />知识库</RouterLink
          >
        </nav>
        <div class="security-note">
          <span class="security-note__icon"><ShieldCheck :size="16" /></span>
          <div>
            <strong>受控访问</strong>
            <p>本地只读模式</p>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--canvas);
  color: var(--ink);
}
.app-header {
  position: sticky;
  top: 0;
  z-index: 30;
  height: 68px;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 253, 0.94);
  backdrop-filter: blur(16px);
}
.app-header__inner {
  display: flex;
  height: 100%;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
}
.brand-lockup {
  display: flex;
  align-items: center;
  gap: 11px;
}
.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 9px;
  background: var(--ink);
  color: #e9f5ee;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}
.brand-name {
  margin: 0;
  font-size: 14px;
  font-weight: 760;
  line-height: 1.2;
}
.brand-context {
  margin: 3px 0 0;
  font-size: 11px;
  color: var(--muted);
}
.app-header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}
.global-search {
  display: flex;
  width: min(31vw, 360px);
  height: 36px;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 0 8px 0 10px;
  color: var(--subtle);
  background: var(--panel);
}
.global-search:focus-within {
  border-color: #94cdb6;
  box-shadow: 0 0 0 3px rgba(67, 138, 109, 0.11);
}
.global-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--ink);
  font-size: 12px;
}
.global-search input::placeholder {
  color: #9aa39e;
}
kbd {
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 2px 4px;
  color: #8d9691;
  background: #fafbf9;
  font: 10px/1 var(--font-sans);
  white-space: nowrap;
}
.icon-button {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 0;
  border-radius: 7px;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
}
.icon-button:hover {
  color: var(--ink);
  background: #f0f3ef;
}
.header-divider {
  width: 1px;
  height: 22px;
  background: var(--line);
}
.status-indicator {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-size: 12px;
}
.status-indicator span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3b9d72;
  box-shadow: 0 0 0 3px #e5f4eb;
}
.profile-button {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid #e4ded2;
  border-radius: 50%;
  color: #4f4535;
  background: #f4ead6;
  cursor: pointer;
}
.mobile-menu {
  display: none;
}
.app-body {
  display: flex;
  min-height: calc(100vh - 68px);
}
.sidebar {
  display: flex;
  width: 238px;
  flex: 0 0 238px;
  flex-direction: column;
  border-right: 1px solid #25352e;
  padding: 16px 12px 14px;
  background: var(--ink);
  color: #ecf1ec;
  transition:
    width 0.2s,
    flex-basis 0.2s;
}
.sidebar--collapsed {
  width: 68px;
  flex-basis: 68px;
  padding-inline: 10px;
}
.sidebar__top {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sidebar-collapse {
  align-self: flex-end;
  color: #9caaa3;
}
.sidebar-collapse:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}
.sidebar--collapsed .sidebar-collapse {
  align-self: center;
}
.create-button {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 7px;
  padding: 0 12px;
  color: #14221b;
  background: #bfe6d1;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.create-button:hover {
  background: #d2f0df;
}
.create-button--icon {
  width: 38px;
  padding: 0;
}
.sidebar-nav {
  margin-top: 26px;
}
.sidebar-label {
  margin: 0 10px 9px;
  color: #7d8d84;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.nav-item {
  display: flex;
  min-height: 40px;
  align-items: center;
  gap: 11px;
  border-radius: 7px;
  padding: 0 10px;
  color: #b5c0ba;
  font-size: 13px;
  font-weight: 560;
  text-decoration: none;
}
.nav-item:hover {
  color: #f7faf7;
  background: rgba(255, 255, 255, 0.06);
}
.nav-item--active {
  color: #ecfff3;
  background: rgba(190, 230, 209, 0.13);
  box-shadow: inset 2px 0 #bfe6d1;
}
.nav-item__arrow {
  margin-left: auto;
  opacity: 0.6;
}
.nav-item--muted {
  width: 100%;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.nav-item--centered {
  justify-content: center;
  padding-inline: 0;
}
.sidebar__bottom {
  margin-top: auto;
}
.security-note {
  display: flex;
  gap: 9px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 7px;
  padding: 10px;
  color: #b4c2ba;
  background: rgba(255, 255, 255, 0.035);
}
.security-note__icon {
  color: #a7ddbe;
}
.security-note strong {
  display: block;
  color: #e8eee9;
  font-size: 11px;
  font-weight: 650;
}
.security-note p {
  margin: 3px 0 0;
  font-size: 10px;
  line-height: 1.45;
  color: #90a097;
}
.sidebar__bottom .nav-item {
  margin-top: 10px;
}
.workspace-user {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 8px;
  padding: 8px 10px;
}
.workspace-user--centered {
  justify-content: center;
  padding-inline: 0;
}
.workspace-user__avatar {
  display: grid;
  width: 27px;
  height: 27px;
  place-items: center;
  border-radius: 50%;
  color: #423827;
  background: #efc980;
  font-size: 11px;
  font-weight: 800;
}
.workspace-user strong {
  display: block;
  color: #e2e9e4;
  font-size: 11px;
  font-weight: 600;
}
.workspace-user small {
  display: block;
  margin-top: 1px;
  color: #819087;
  font-size: 10px;
}
.app-main {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  background: var(--canvas);
}
.mobile-overlay {
  display: none;
}
@media (max-width: 900px) {
  .sidebar {
    display: none;
  }
  .mobile-menu {
    display: grid;
  }
  .app-header__inner {
    padding-inline: 16px;
  }
  .global-search,
  .header-help,
  .header-divider,
  .status-indicator {
    display: none;
  }
  .mobile-overlay {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: block;
  }
  .mobile-overlay__backdrop {
    position: absolute;
    inset: 0;
    border: 0;
    background: rgba(14, 26, 20, 0.52);
  }
  .mobile-drawer {
    position: relative;
    display: flex;
    width: min(84vw, 320px);
    height: 100%;
    flex-direction: column;
    padding: 16px 14px;
    color: #ecf1ec;
    background: var(--ink);
    box-shadow: 16px 0 40px rgba(0, 0, 0, 0.2);
  }
  .mobile-drawer__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 26px;
  }
  .mobile-drawer__top .icon-button {
    color: #c6d0ca;
  }
  .mobile-drawer__nav {
    margin-top: 24px;
  }
  .mobile-drawer .security-note {
    margin-top: auto;
  }
}
@media (max-width: 520px) {
  .brand-context {
    display: none;
  }
  .app-header__actions {
    gap: 8px;
  }
  .app-header__inner {
    gap: 10px;
  }
}
</style>
