<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Check,
  Database as DatabaseIcon,
  LoaderCircle,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
} from "lucide-vue-next";
import type { Database } from "@/types/api";

const props = defineProps<{
  databases: Database[];
  selectedDatabaseId: string;
  loading: boolean;
  isAdmin: boolean;
}>();
const emit = defineEmits<{
  (event: "select", databaseId: string): void;
  (event: "refresh"): void;
  (event: "add"): void;
}>();
const searchQuery = ref("");
const statusFilter = ref<"all" | "enabled" | "disabled">("all");
const filteredDatabases = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return props.databases.filter((database) => {
    const matchesQuery =
      !query || `${database.name} ${database.dialect} ${database.id}`.toLowerCase().includes(query);
    const matchesStatus =
      statusFilter.value === "all" ||
      (statusFilter.value === "enabled" ? database.enabled : !database.enabled);
    return matchesQuery && matchesStatus;
  });
});
const enabledCount = computed(() => props.databases.filter((database) => database.enabled).length);
const filterOptions = [
  { value: "all", label: "全部" },
  { value: "enabled", label: "启用" },
  { value: "disabled", label: "停用" },
] as const;
</script>

<template>
  <div class="database-layout">
    <aside class="database-sidebar" aria-label="数据库列表">
      <header class="database-sidebar__header">
        <div class="sidebar-title-row">
          <div>
            <p class="sidebar-kicker">RESOURCE HUB</p>
            <h2>数据库</h2>
          </div>
          <span class="sidebar-count">{{ databases.length }}</span>
        </div>
        <p class="sidebar-subtitle">
          <span class="status-dot" aria-hidden="true" />{{ enabledCount }} 个已启用 ·
          {{ databases.length }} 个数据源
        </p>
      </header>
      <div class="database-sidebar__body">
        <div class="sidebar-tools">
          <label class="sidebar-search"
            ><Search :size="15" aria-hidden="true" /><input
              v-model="searchQuery"
              type="search"
              placeholder="搜索数据库"
              aria-label="搜索数据库"
            /><kbd v-if="searchQuery">Esc</kbd></label
          >
          <div class="status-filter" role="group" aria-label="数据库状态筛选">
            <SlidersHorizontal :size="13" aria-hidden="true" /><button
              v-for="option in filterOptions"
              :key="option.value"
              type="button"
              :class="{ active: statusFilter === option.value }"
              @click="statusFilter = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
        <div v-if="loading" class="sidebar-state" aria-live="polite">
          <LoaderCircle class="spin" :size="19" />正在加载数据源
        </div>
        <div v-else-if="databases.length === 0" class="sidebar-state">
          <DatabaseIcon :size="19" />暂无数据库
        </div>
        <div v-else-if="filteredDatabases.length === 0" class="sidebar-state sidebar-state--empty">
          <Search :size="19" /><span>没有匹配的数据源</span
          ><button
            type="button"
            @click="
              searchQuery = '';
              statusFilter = 'all';
            "
          >
            清除筛选
          </button>
        </div>
        <nav v-else class="database-nav" aria-label="选择数据库">
          <button
            v-for="database in filteredDatabases"
            :key="database.id"
            class="database-nav-item"
            :class="{
              'database-nav-item--active': database.id === selectedDatabaseId,
              'database-nav-item--inactive': !database.enabled,
            }"
            type="button"
            @click="emit('select', database.id)"
          >
            <span
              class="database-nav-item__indicator"
              :class="{ 'database-nav-item__indicator--ready': database.enabled }"
              aria-hidden="true"
            />
            <span
              class="database-nav-item__icon"
              :class="
                database.dialect === 'mysql'
                  ? 'database-nav-item__icon--mysql'
                  : 'database-nav-item__icon--sqlite'
              "
              ><DatabaseIcon :size="17"
            /></span>
            <span class="database-nav-item__copy"
              ><strong>{{ database.name }}</strong
              ><small
                >{{ database.dialect.toUpperCase() }} <span aria-hidden="true">·</span>
                {{ database.enabled ? "在线" : "未连接" }}</small
              ></span
            >
            <span
              class="database-nav-item__status"
              :class="{ 'database-nav-item__status--ready': database.enabled }"
              ><Check v-if="database.enabled" :size="12" /><span
                v-else
                class="status-dot status-dot--muted"
                aria-hidden="true"
              />{{ database.enabled ? "已启用" : "停用" }}</span
            >
          </button>
        </nav>
        <footer class="sidebar-footer">
          <button
            class="sidebar-refresh-button"
            type="button"
            title="刷新列表"
            aria-label="刷新列表"
            :disabled="loading"
            @click="emit('refresh')"
          >
            <RefreshCw :class="{ spin: loading }" :size="15" />刷新列表</button
          ><button v-if="isAdmin" class="sidebar-add-button" type="button" @click="emit('add')">
            <Plus :size="16" />添加数据库
          </button>
        </footer>
      </div>
    </aside>
    <section class="database-layout__content"><slot /></section>
  </div>
</template>

<style scoped>
.database-layout {
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
.database-sidebar {
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
.database-sidebar__header {
  padding: 25px 22px 18px;
  border-bottom: 1px solid rgba(228, 241, 231, 0.1);
}
.sidebar-title-row,
.sidebar-subtitle,
.sidebar-refresh-button,
.sidebar-add-button,
.status-filter,
.sidebar-search {
  display: flex;
  align-items: center;
}
.sidebar-title-row {
  justify-content: space-between;
  gap: 18px;
}
.sidebar-kicker {
  margin: 0 0 7px;
  color: #8ab99a;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
}
.database-sidebar__header h2 {
  margin: 0;
  color: #f7fbf8;
  font-size: 24px;
  font-weight: 720;
}
.sidebar-count {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid rgba(161, 213, 177, 0.3);
  border-radius: 8px;
  color: #b9e2c3;
  background: rgba(113, 170, 129, 0.16);
  font-size: 13px;
  font-weight: 700;
}
.sidebar-subtitle {
  gap: 7px;
  margin: 12px 0 0;
  color: #9db0a3;
  font-size: 12px;
}
.status-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #77d497;
  box-shadow: 0 0 0 3px rgba(119, 212, 151, 0.12);
}
.status-dot--muted {
  width: 5px;
  height: 5px;
  box-shadow: none;
  background: #88968b;
}
.database-sidebar__body {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  overflow-y: auto;
  padding: 17px 13px 15px;
  scrollbar-color: #476150 transparent;
  scrollbar-width: thin;
}
.database-sidebar__body::-webkit-scrollbar {
  width: 7px;
}
.database-sidebar__body::-webkit-scrollbar-thumb {
  border-radius: 8px;
  background: #476150;
}
.sidebar-tools {
  display: grid;
  gap: 10px;
  margin: 0 3px 14px;
}
.sidebar-search {
  min-height: 38px;
  gap: 8px;
  border: 1px solid rgba(205, 226, 211, 0.18);
  border-radius: 7px;
  padding: 0 10px;
  color: #98b4a0;
  background: rgba(5, 15, 10, 0.24);
}
.sidebar-search:focus-within {
  border-color: #80bf91;
  box-shadow: 0 0 0 3px rgba(128, 191, 145, 0.12);
}
.sidebar-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: #edf5ef;
  background: transparent;
  font-size: 12px;
}
.sidebar-search input::placeholder {
  color: #789080;
}
.sidebar-search kbd {
  border: 1px solid rgba(214, 233, 218, 0.18);
  border-radius: 4px;
  padding: 3px 5px;
  color: #9fb5a5;
  background: rgba(255, 255, 255, 0.05);
  font-size: 10px;
}
.status-filter {
  gap: 5px;
  min-height: 29px;
  color: #779181;
}
.status-filter button {
  min-height: 27px;
  border: 1px solid transparent;
  border-radius: 5px;
  padding: 0 8px;
  color: #91a79a;
  background: transparent;
  font-size: 11px;
  cursor: pointer;
}
.status-filter button:hover,
.status-filter button.active {
  border-color: rgba(157, 211, 171, 0.2);
  color: #eaf5ed;
  background: rgba(136, 194, 149, 0.14);
}
.database-nav {
  display: grid;
  flex: 1;
  align-content: start;
  gap: 6px;
  min-height: 0;
}
.database-nav-item {
  position: relative;
  display: grid;
  height: 70px;
  min-width: 0;
  min-height: 70px;
  grid-template-columns: 3px 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 10px 10px 10px 7px;
  color: #c4d3c8;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.database-nav-item:hover {
  border-color: rgba(175, 214, 185, 0.16);
  background: rgba(210, 237, 216, 0.07);
}
.database-nav-item--active {
  border-color: rgba(158, 214, 171, 0.32);
  color: #f4fbf5;
  background: #2a4133;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
.database-nav-item--inactive {
  color: #9aaca0;
}
.database-nav-item__indicator {
  width: 3px;
  height: 28px;
  border-radius: 99px;
  background: #526258;
}
.database-nav-item__indicator--ready {
  background: #78d596;
  box-shadow: 0 0 10px rgba(120, 213, 150, 0.34);
}
.database-nav-item__icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 8px;
}
.database-nav-item__icon--sqlite {
  color: #9cdbad;
  background: rgba(110, 191, 131, 0.16);
}
.database-nav-item__icon--mysql {
  color: #b7caeb;
  background: rgba(116, 148, 205, 0.16);
}
.database-nav-item--inactive .database-nav-item__icon {
  color: #94a199;
  background: rgba(198, 214, 202, 0.1);
}
.database-nav-item__copy {
  display: grid;
  min-width: 0;
  gap: 4px;
}
.database-nav-item__copy strong {
  overflow: hidden;
  color: inherit;
  font-size: 14px;
  font-weight: 670;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.database-nav-item__copy small {
  overflow: hidden;
  color: #8fa598;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.database-nav-item--active .database-nav-item__copy small {
  color: #aec5b4;
}
.database-nav-item__status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #8fa197;
  font-size: 10px;
  white-space: nowrap;
}
.database-nav-item__status--ready {
  color: #9fe0ae;
}
.sidebar-footer {
  display: grid;
  gap: 8px;
  margin-top: auto;
  padding-top: 18px;
}
.sidebar-refresh-button,
.sidebar-add-button {
  width: 100%;
  min-height: 40px;
  justify-content: center;
  gap: 8px;
  border-radius: 7px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}
.sidebar-refresh-button {
  border: 1px solid transparent;
  color: #9db3a3;
  background: transparent;
}
.sidebar-refresh-button:hover:not(:disabled) {
  border-color: rgba(179, 214, 186, 0.16);
  color: #eff8f1;
  background: rgba(212, 238, 217, 0.08);
}
.sidebar-refresh-button:disabled {
  cursor: default;
  opacity: 0.5;
}
.sidebar-add-button {
  border: 1px solid #9fd2aa;
  color: #173120;
  background: #b9e6c2;
}
.sidebar-add-button:hover {
  border-color: #c8efd0;
  background: #c8efd0;
}
.sidebar-state {
  display: flex;
  min-height: 190px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #9aafa0;
  font-size: 12px;
}
.sidebar-state--empty {
  flex-direction: column;
  gap: 9px;
  text-align: center;
}
.sidebar-state--empty button {
  border: 0;
  color: #b5e5bf;
  background: transparent;
  font-size: 11px;
  cursor: pointer;
}
.sidebar-state--empty button:hover {
  color: #e1f6e5;
  text-decoration: underline;
}
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.database-layout__content {
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
  background: #f9fbf9;
}
@media (max-width: 1100px) {
  .database-layout {
    display: block;
    height: auto;
    min-height: 0;
  }
  .database-sidebar {
    width: auto;
    height: auto;
    min-width: 0;
    flex: none;
    border-right: 0;
    border-bottom: 1px solid #263d31;
  }
  .database-sidebar__header {
    padding: 19px 18px 15px;
  }
  .database-sidebar__body {
    overflow: visible;
    padding: 13px 12px 12px;
  }
  .sidebar-tools {
    grid-template-columns: minmax(180px, 1fr) auto;
    align-items: center;
    margin-bottom: 12px;
  }
  .database-nav {
    display: flex;
    overflow-x: auto;
    gap: 7px;
    padding-bottom: 3px;
  }
  .database-nav-item {
    width: 245px;
    flex: 0 0 245px;
  }
  .sidebar-footer {
    grid-template-columns: 1fr 1fr;
    margin-top: 10px;
    padding-top: 0;
  }
  .database-layout__content {
    overflow: visible;
  }
}
@media (max-width: 520px) {
  .sidebar-tools {
    grid-template-columns: 1fr;
  }
  .status-filter {
    justify-content: flex-start;
  }
  .database-nav-item {
    width: min(82vw, 245px);
    flex-basis: min(82vw, 245px);
  }
  .sidebar-footer {
    grid-template-columns: 1fr;
  }
}
</style>
