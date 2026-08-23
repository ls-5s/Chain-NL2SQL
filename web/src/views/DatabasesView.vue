<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  Check,
  Database as DatabaseIcon,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-vue-next";

import {
  ApiRequestError,
  createDatabase,
  deleteDatabase,
  fetchDatabaseConfigs,
  testDatabase,
  updateDatabase,
  updateDatabaseTableAccess,
} from "@/api/client";
import { getDemoRole } from "@/auth/auth";
import type { Database, DatabaseDialect } from "@/types/api";

const databases = ref<Database[]>([]);
const selectedDatabaseId = ref("");
const loading = ref(true);
const saving = ref(false);
const testingId = ref("");
const activatingId = ref("");
const errorMessage = ref("");
const modalOpen = ref(false);
const editingDatabase = ref<Database | null>(null);
const isAdmin = computed(() => getDemoRole() === "super_admin");
const form = reactive({
  name: "",
  dialect: "sqlite" as DatabaseDialect,
  path: "data/demo.sqlite",
  host: "",
  port: "3306",
  database: "",
  username: "",
  credentialRef: "",
  tls: true,
});

const activeDatabase = computed(() => databases.value.find((database) => database.enabled));
const selectedDatabase = computed(
  () =>
    databases.value.find((database) => database.id === selectedDatabaseId.value) ??
    activeDatabase.value ??
    databases.value[0],
);
const enabledTableCount = computed(
  () => selectedDatabase.value?.tables.filter((table) => table.agent_access).length ?? 0,
);

function setError(error: unknown, fallback: string) {
  errorMessage.value = error instanceof ApiRequestError ? error.message : fallback;
}

function reconcileSelection(preferredId = "") {
  const preferred = databases.value.find((database) => database.id === preferredId);
  selectedDatabaseId.value = (preferred ?? activeDatabase.value ?? databases.value[0])?.id ?? "";
}

async function loadDatabases(preferredId = selectedDatabaseId.value) {
  loading.value = true;
  errorMessage.value = "";
  try {
    databases.value = await fetchDatabaseConfigs();
    reconcileSelection(preferredId);
  } catch (error) {
    setError(error, "数据库列表加载失败。");
  } finally {
    loading.value = false;
  }
}

function selectDatabase(databaseId: string) {
  selectedDatabaseId.value = databaseId;
  errorMessage.value = "";
}

function resetForm() {
  Object.assign(form, {
    name: "",
    dialect: "sqlite",
    path: "data/demo.sqlite",
    host: "",
    port: "3306",
    database: "",
    username: "",
    credentialRef: "",
    tls: true,
  });
}

function openCreate() {
  editingDatabase.value = null;
  resetForm();
  errorMessage.value = "";
  modalOpen.value = true;
}

function openEdit(database: Database) {
  editingDatabase.value = database;
  Object.assign(form, {
    name: database.name,
    dialect: database.dialect,
    path: String(database.config.path || ""),
    host: String(database.config.host || ""),
    port: String(database.config.port || "3306"),
    database: String(database.config.database || ""),
    username: String(database.config.username || ""),
    credentialRef: String(database.config.credential_ref || ""),
    tls: database.config.tls !== false,
  });
  errorMessage.value = "";
  modalOpen.value = true;
}

function closeModal() {
  if (!saving.value) modalOpen.value = false;
}

function configPayload() {
  if (form.dialect === "sqlite") return { path: form.path.trim() };
  return {
    host: form.host.trim(),
    port: Number(form.port),
    database: form.database.trim(),
    username: form.username.trim(),
    credential_ref: form.credentialRef.trim(),
    tls: form.tls,
  };
}

async function saveDatabase() {
  if (!form.name.trim()) {
    errorMessage.value = "请输入数据库名称。";
    return;
  }
  if (form.dialect === "sqlite" && !form.path.trim()) {
    errorMessage.value = "请输入 SQLite 文件路径。";
    return;
  }
  if (
    form.dialect === "mysql" &&
    (!form.host.trim() ||
      !form.database.trim() ||
      !form.username.trim() ||
      !form.credentialRef.trim())
  ) {
    errorMessage.value = "请完整填写 MySQL 连接信息和凭据引用。";
    return;
  }

  saving.value = true;
  errorMessage.value = "";
  const preferredId = editingDatabase.value?.id;
  try {
    if (editingDatabase.value) {
      await updateDatabase(editingDatabase.value.id, {
        name: form.name.trim(),
        config: configPayload(),
      });
    } else {
      await createDatabase({
        name: form.name.trim(),
        dialect: form.dialect,
        config: configPayload(),
      });
    }
    await loadDatabases(preferredId);
    modalOpen.value = false;
  } catch (error) {
    setError(error, "数据库保存失败。");
  } finally {
    saving.value = false;
  }
}

async function handleTest(database: Database) {
  testingId.value = database.id;
  errorMessage.value = "";
  try {
    const refreshed = await testDatabase(database.id);
    const index = databases.value.findIndex((item) => item.id === database.id);
    if (index !== -1) databases.value[index] = refreshed;
  } catch (error) {
    setError(error, "连接测试失败。");
  } finally {
    testingId.value = "";
  }
}

async function activateDatabase(database: Database) {
  if (!isAdmin.value || database.enabled || activatingId.value) return;
  activatingId.value = database.id;
  errorMessage.value = "";
  try {
    await updateDatabase(database.id, { enabled: true });
    await loadDatabases(database.id);
  } catch (error) {
    setError(error, "数据库启用失败。");
  } finally {
    activatingId.value = "";
  }
}

async function toggleTable(database: Database, tableName: string, value: boolean) {
  const table = database.tables.find((item) => item.table_name === tableName);
  if (!table || !isAdmin.value) return;

  const previous = table.agent_access;
  table.agent_access = value;
  try {
    const saved = await updateDatabaseTableAccess(database.id, tableName, value);
    table.agent_access = saved.agent_access;
  } catch (error) {
    table.agent_access = previous;
    setError(error, "表权限更新失败。");
  }
}

async function removeDatabase(database: Database) {
  if (database.id === "demo" || !window.confirm(`确定删除“${database.name}”吗？`)) return;

  try {
    await deleteDatabase(database.id);
    databases.value = databases.value.filter((item) => item.id !== database.id);
    reconcileSelection();
  } catch (error) {
    setError(error, "数据库删除失败。");
  }
}

onMounted(() => void loadDatabases());
</script>

<template>
  <main class="databases-page">
    <p v-if="errorMessage && !modalOpen" class="alert" role="alert">{{ errorMessage }}</p>

    <section class="database-workspace" aria-labelledby="database-list-title">
      <aside class="database-sidebar" aria-label="数据库列表">
        <div class="database-sidebar__header">
          <div>
            <h2 id="database-list-title">数据库</h2>
            <p>{{ databases.length }} 个数据源</p>
          </div>
        </div>

        <div v-if="loading" class="sidebar-state">
          <LoaderCircle class="spin" :size="19" />
          正在加载
        </div>
        <div v-else-if="databases.length === 0" class="sidebar-state">
          <DatabaseIcon :size="19" />
          暂无数据库
        </div>
        <nav v-else class="database-nav" aria-label="选择数据库">
          <button
            v-for="database in databases"
            :key="database.id"
            class="database-nav-item"
            :class="{
              'database-nav-item--active': database.id === selectedDatabase?.id,
              'database-nav-item--inactive': !database.enabled,
            }"
            type="button"
            @click="selectDatabase(database.id)"
          >
            <span class="database-nav-item__icon"><DatabaseIcon :size="17" /></span>
            <span class="database-nav-item__copy">
              <strong>{{ database.name }}</strong>
              <small>{{ database.dialect.toUpperCase() }}</small>
            </span>
            <span
              class="database-nav-item__status"
              :class="{ 'database-nav-item__status--ready': database.enabled }"
            >
              <Check v-if="database.enabled" :size="12" />
              {{ database.enabled ? "已启用" : "停用" }}
            </span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <button
            class="sidebar-refresh-button"
            type="button"
            title="刷新列表"
            aria-label="刷新列表"
            :disabled="loading"
            @click="loadDatabases()"
          >
            <RefreshCw :class="{ spin: loading }" :size="16" />
            刷新
          </button>
          <button v-if="isAdmin" class="sidebar-add-button" type="button" @click="openCreate">
            <Plus :size="16" /> 添加数据库
          </button>
        </div>
      </aside>

      <section v-if="selectedDatabase" class="database-detail" aria-labelledby="database-detail-title">
        <header class="detail-header">
          <div class="database-identity">
            <span class="database-icon"><DatabaseIcon :size="20" /></span>
            <div>
              <p class="eyebrow">{{ selectedDatabase.dialect.toUpperCase() }} SOURCE</p>
              <h2 id="database-detail-title">{{ selectedDatabase.name }}</h2>
              <span class="database-meta">{{ selectedDatabase.id }}</span>
            </div>
          </div>
          <button
            class="status-badge"
            :class="[
              selectedDatabase.enabled
                ? 'status-badge--ready'
                : 'status-badge--interactive',
            ]"
            type="button"
            :disabled="!isAdmin || selectedDatabase.enabled || activatingId !== ''"
            :title="
              selectedDatabase.enabled
                ? '当前 Agent 正在使用此数据库'
                : '启用此数据库并停用其他数据库'
            "
            @click="activateDatabase(selectedDatabase)"
          >
            <LoaderCircle
              v-if="activatingId === selectedDatabase.id"
              class="spin"
              :size="13"
            />
            <Check v-else-if="selectedDatabase.enabled" :size="13" />
            {{
              activatingId === selectedDatabase.id
                ? "启用中"
                : selectedDatabase.enabled
                  ? "已启用"
                  : "已停用 · 点击启用"
            }}
          </button>
        </header>

        <div class="detail-summary" aria-label="数据库概览">
          <div class="summary-item">
            <strong>{{ selectedDatabase.tables.length }}</strong>
            <span>数据表</span>
          </div>
          <div class="summary-item">
            <strong>{{ enabledTableCount }}</strong>
            <span>Agent 已授权表</span>
          </div>
          <div class="summary-item">
            <strong><ShieldCheck :size="18" /> 只读</strong>
            <span>查询策略</span>
          </div>
        </div>

        <div class="detail-section">
          <div class="table-heading">
            <div>
              <h3>Agent 表权限</h3>
              <p>只有开启的表会进入 Agent 的 Schema 和查询权限。</p>
            </div>
            <span>{{ enabledTableCount }} / {{ selectedDatabase.tables.length }} 已授权</span>
          </div>

          <div v-if="selectedDatabase.tables.length" class="table-list">
            <label
              v-for="table in selectedDatabase.tables"
              :key="table.table_name"
              class="table-row"
            >
              <span>
                <span class="table-name">{{ table.table_name }}</span>
                <small>{{ table.agent_access ? "允许查询" : "已禁止" }}</small>
              </span>
              <input
                type="checkbox"
                :checked="table.agent_access"
                :disabled="!isAdmin || !selectedDatabase.enabled"
                @change="
                  toggleTable(
                    selectedDatabase,
                    table.table_name,
                    ($event.target as HTMLInputElement).checked,
                  )
                "
              />
            </label>
          </div>
          <div v-else class="table-empty">请先测试连接以读取数据表</div>
        </div>

        <footer class="detail-actions">
          <button
            class="secondary-button"
            type="button"
            :disabled="!isAdmin || testingId === selectedDatabase.id"
            @click="handleTest(selectedDatabase)"
          >
            <LoaderCircle
              v-if="testingId === selectedDatabase.id"
              class="spin"
              :size="15"
            />
            <RefreshCw v-else :size="15" />
            {{ testingId === selectedDatabase.id ? "测试中" : "测试连接" }}
          </button>
          <div v-if="isAdmin" class="action-group">
            <button
              class="icon-button"
              type="button"
              title="编辑数据库"
              aria-label="编辑数据库"
              @click="openEdit(selectedDatabase)"
            >
              <Pencil :size="16" />
            </button>
            <button
              v-if="selectedDatabase.id !== 'demo'"
              class="icon-button icon-button--danger"
              type="button"
              title="删除数据库"
              aria-label="删除数据库"
              @click="removeDatabase(selectedDatabase)"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </footer>
      </section>

      <section v-else class="database-detail database-detail--empty" aria-live="polite">
        <DatabaseIcon :size="28" />
        <p>选择一个数据库开始管理</p>
      </section>
    </section>

    <div v-if="modalOpen" class="modal-backdrop" role="presentation" @click.self="closeModal">
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="database-modal-title"
      >
        <header class="modal-header">
          <div>
            <p class="eyebrow">{{ editingDatabase ? "EDIT SOURCE" : "NEW SOURCE" }}</p>
            <h2 id="database-modal-title">
              {{ editingDatabase ? "编辑数据库" : "添加数据库" }}
            </h2>
          </div>
          <button
            class="icon-button"
            type="button"
            title="关闭"
            aria-label="关闭"
            @click="closeModal"
          >
            <X :size="19" />
          </button>
        </header>

        <form class="database-form" @submit.prevent="saveDatabase">
          <label>
            名称
            <input v-model="form.name" type="text" maxlength="100" :disabled="saving" />
          </label>
          <fieldset>
            <legend>类型</legend>
            <div class="dialect-switch">
              <button
                type="button"
                :class="{ active: form.dialect === 'sqlite' }"
                @click="form.dialect = 'sqlite'"
              >
                SQLite
              </button>
              <button
                type="button"
                :class="{ active: form.dialect === 'mysql' }"
                @click="form.dialect = 'mysql'"
              >
                MySQL
              </button>
            </div>
          </fieldset>
          <label v-if="form.dialect === 'sqlite'">
            文件路径
            <input v-model="form.path" type="text" placeholder="data/demo.sqlite" :disabled="saving" />
          </label>
          <template v-else>
            <label>
              主机
              <input v-model="form.host" type="text" placeholder="127.0.0.1" :disabled="saving" />
            </label>
            <div class="form-grid">
              <label>
                端口
                <input v-model="form.port" type="number" min="1" max="65535" :disabled="saving" />
              </label>
              <label>
                数据库名
                <input v-model="form.database" type="text" :disabled="saving" />
              </label>
            </div>
            <label>
              用户名
              <input v-model="form.username" type="text" :disabled="saving" />
            </label>
            <label>
              凭据引用
              <input v-model="form.credentialRef" type="text" placeholder="secret/my-db-readonly" :disabled="saving" />
            </label>
            <label class="checkbox-line">
              <input v-model="form.tls" type="checkbox" :disabled="saving" />启用 TLS
            </label>
          </template>
          <p v-if="errorMessage && modalOpen" class="form-error" role="alert">{{ errorMessage }}</p>
          <footer class="modal-actions">
            <button class="secondary-button" type="button" :disabled="saving" @click="closeModal">取消</button>
            <button class="primary-button" type="submit" :disabled="saving">
              <LoaderCircle v-if="saving" class="spin" :size="16" />
              {{ saving ? "保存中" : "保存数据库" }}
            </button>
          </footer>
        </form>
      </section>
    </div>
  </main>
</template>

<style scoped>
.databases-page {
  min-height: 100vh;
  padding: 40px 32px 48px;
  color: #202123;
  background: #ffffff;
}

.detail-header,
.database-sidebar__header,
.table-heading,
.detail-actions,
.modal-header,
.modal-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #6b7f73;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

h1,
h2,
h3,
p {
  margin-top: 0;
}

h2 {
  margin-bottom: 0;
  font-size: 20px;
  letter-spacing: -0.01em;
}

h3 {
  margin-bottom: 5px;
  font-size: 14px;
}

.table-heading p,
.database-sidebar__header p {
  margin-bottom: 0;
  color: #6f7772;
  font-size: 13px;
}

.primary-button,
.secondary-button,
.sidebar-add-button {
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

.primary-button {
  border: 0;
  color: #143322;
  background: #b7e7cb;
}

.primary-button:hover {
  background: #a6dbb9;
}

.primary-button:disabled,
.secondary-button:disabled,
.sidebar-add-button:disabled {
  cursor: default;
  opacity: 0.55;
}

.secondary-button {
  border: 1px solid #d9dfdb;
  color: #4f5953;
  background: #ffffff;
}

.secondary-button:hover:not(:disabled) {
  border-color: #b6cebd;
  color: #326d4c;
}

.alert,
.form-error {
  margin: 16px 0;
  border: 1px solid #f0c8c8;
  border-radius: 6px;
  padding: 11px 13px;
  color: #a24a4a;
  background: #fff7f7;
  font-size: 13px;
}

.form-error {
  margin: 0;
}

.database-workspace {
  display: grid;
  width: 100%;
  min-width: 0;
  min-height: 636px;
  grid-template-columns: minmax(250px, 280px) minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid #e7e7e7;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.045);
}

.database-sidebar {
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: 20px 13px 13px;
  background: #f7f7f8;
}

.database-sidebar__header {
  padding: 4px 8px 18px;
}

.database-sidebar__header h2 {
  font-size: 16px;
}

.database-sidebar__header p {
  margin-top: 4px;
  color: #8a8f8b;
  font-size: 11px;
}

.database-nav {
  display: grid;
  flex: 1;
  gap: 3px;
  min-height: 0;
  overflow-y: auto;
}

.database-nav-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 8px;
  padding: 12px 9px;
  color: #444746;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.database-nav-item:hover {
  background: #ececee;
}

.database-nav-item--active {
  color: #202123;
  background: #e4e4e4;
}

.database-nav-item--inactive {
  color: #747875;
}

.database-nav-item__icon {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 6px;
  color: #397453;
  background: #e6f2e9;
}

.database-nav-item--inactive .database-nav-item__icon {
  color: #7f8781;
  background: #e8e9e8;
}

.database-nav-item__copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 3px;
}

.database-nav-item__copy strong {
  overflow: hidden;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.database-nav-item__copy small {
  color: #8b918d;
  font-size: 10px;
}

.database-nav-item__status {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: #969b97;
  font-size: 10px;
  white-space: nowrap;
}

.database-nav-item__status--ready {
  color: #397453;
}

.sidebar-footer {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.sidebar-refresh-button,
.sidebar-add-button {
  display: inline-flex;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 8px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.sidebar-refresh-button {
  border: 0;
  color: #656c67;
  background: transparent;
}

.sidebar-refresh-button:hover:not(:disabled) {
  color: #326d4c;
  background: #ececee;
}

.sidebar-refresh-button:disabled {
  cursor: default;
  opacity: 0.55;
}

.sidebar-add-button {
  border: 1px solid #dfe1df;
  color: #4f5953;
  background: #ffffff;
}

.sidebar-add-button:hover {
  border-color: #c5d7c9;
  color: #326d4c;
  background: #fbfffc;
}

.sidebar-state {
  display: flex;
  min-height: 170px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #7d847f;
  font-size: 12px;
}

.database-detail {
  min-width: 0;
  background: #ffffff;
}

.detail-header {
  min-height: 108px;
  padding: 25px 30px 21px;
  border-bottom: 1px solid #ededed;
}

.database-identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
}

.database-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
  color: #397453;
  background: #e6f2e9;
}

.database-meta {
  color: #8a918c;
  font-size: 11px;
}

.status-badge {
  display: inline-flex;
  min-height: 29px;
  align-items: center;
  gap: 5px;
  border: 0;
  border-radius: 999px;
  padding: 0 10px;
  color: #9a6e34;
  background: #fff4df;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.status-badge--ready {
  color: #397453;
  background: #e8f4eb;
  cursor: default;
}

.status-badge--interactive {
  cursor: pointer;
}

.status-badge--interactive:hover:not(:disabled) {
  background: #ffebc8;
}

.status-badge:disabled {
  opacity: 1;
}

.detail-summary {
  display: flex;
  gap: 1px;
  margin: 22px 30px 0;
  border: 1px solid #e5e5e5;
  background: #e5e5e5;
}

.summary-item {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 5px;
  padding: 15px 18px;
  background: #ffffff;
}

.summary-item strong {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 19px;
}

.summary-item span {
  color: #858b87;
  font-size: 11px;
}

.detail-section {
  margin: 26px 30px 0;
}

.table-heading {
  align-items: flex-end;
  margin-bottom: 12px;
}

.table-heading p {
  font-size: 12px;
}

.table-heading > span {
  color: #8a918c;
  font-size: 11px;
  white-space: nowrap;
}

.table-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.table-row {
  display: flex;
  min-height: 50px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #ededed;
  border-radius: 7px;
  padding: 8px 12px;
  cursor: pointer;
}

.table-row:hover {
  border-color: #c8dbcd;
  background: #fbfefb;
}

.table-row > span {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.table-name {
  overflow: hidden;
  color: #303634;
  font: 12px ui-monospace, SFMono-Regular, Consolas, monospace;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-row small {
  color: #9aa19c;
  font-size: 10px;
}

.table-row input,
.checkbox-line input {
  width: 16px;
  height: 16px;
  accent-color: #4b9a67;
}

.table-empty {
  padding: 20px 0;
  color: #9aa19c;
  font-size: 12px;
}

.detail-actions {
  min-height: 74px;
  margin-top: 26px;
  border-top: 1px solid #ededed;
  padding: 15px 30px;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-button {
  display: inline-grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 0;
  border-radius: 6px;
  color: #64736a;
  background: transparent;
  cursor: pointer;
}

.icon-button:hover:not(:disabled) {
  color: #326d4c;
  background: #eef5ef;
}

.icon-button--danger:hover {
  color: #b65353;
  background: #fff0f0;
}

.icon-button:disabled {
  cursor: default;
  opacity: 0.5;
}

.database-detail--empty {
  display: grid;
  min-height: 590px;
  place-items: center;
  align-content: center;
  gap: 8px;
  color: #8b918d;
}

.database-detail--empty p {
  margin: 0;
  font-size: 13px;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.modal-backdrop {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(22, 37, 29, 0.35);
}

.modal {
  width: min(100%, 470px);
  max-height: min(90vh, 700px);
  overflow: auto;
  border: 1px solid #dfe7e1;
  border-radius: 9px;
  padding: 24px;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(22, 37, 29, 0.22);
}

.modal-header {
  align-items: flex-start;
  margin-bottom: 23px;
}

.database-form {
  display: grid;
  gap: 15px;
}

.database-form label,
fieldset {
  display: grid;
  gap: 7px;
  border: 0;
  padding: 0;
  color: #4a5b50;
  font-size: 12px;
  font-weight: 700;
}

.database-form input[type="text"],
.database-form input[type="number"] {
  width: 100%;
  height: 41px;
  border: 1px solid #d9e2db;
  border-radius: 6px;
  padding: 0 10px;
  color: #26382c;
  outline: 0;
  background: #fbfdfb;
  font-size: 13px;
}

.database-form input:focus {
  border-color: #78b58b;
  box-shadow: 0 0 0 3px rgba(104, 181, 130, 0.12);
}

.database-form legend {
  margin-bottom: 7px;
  color: #4a5b50;
  font-size: 12px;
  font-weight: 700;
}

.dialect-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  border: 1px solid #d9e2db;
  border-radius: 6px;
  padding: 2px;
  background: #eef2ef;
}

.dialect-switch button {
  min-height: 35px;
  border: 0;
  border-radius: 4px;
  color: #718077;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.dialect-switch button.active {
  color: #245e3c;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(35, 76, 49, 0.1);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 12px;
}

.checkbox-line {
  display: flex !important;
  align-items: center;
  gap: 8px !important;
  font-weight: 500 !important;
}

.modal-actions {
  justify-content: flex-end;
  margin-top: 4px;
}

@media (max-width: 1100px) {
  .databases-page {
    padding: 22px 16px 32px;
  }

  .database-workspace {
    display: block;
    min-height: 0;
  }

  .database-sidebar {
    padding: 14px 12px 12px;
  }

  .database-sidebar__header {
    padding-bottom: 10px;
  }

  .database-nav {
    display: flex;
    overflow-x: auto;
    gap: 5px;
    padding-bottom: 3px;
  }

  .database-nav-item {
    width: 190px;
    flex: 0 0 190px;
  }

  .sidebar-add-button {
    margin-top: 0;
  }

  .detail-header,
  .detail-actions {
    padding-inline: 16px;
  }

  .detail-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
    padding-top: 20px;
  }

  .detail-summary,
  .detail-section {
    margin-inline: 16px;
  }

  .table-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .detail-summary {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .summary-item:last-child {
    grid-column: 1 / -1;
  }

  .table-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
