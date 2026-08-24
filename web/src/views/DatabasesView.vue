<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  Check,
  Database as DatabaseIcon,
  LoaderCircle,
  Pencil,
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
import { usePermissions } from "@/composables/permissions";
import DatabaseLayout from "@/layouts/DatabaseLayout.vue";
import type { Database, DatabaseDialect } from "@/types/api";

const databases = ref<Database[]>([]);
const selectedDatabaseId = ref("");
const loading = ref(true);
const saving = ref(false);
const testingId = ref("");
const activatingId = ref("");
const batchUpdating = ref(false);
const batchMessage = ref("");
const tableFilter = ref<"all" | "enabled" | "disabled">("all");
const errorMessage = ref("");
const modalOpen = ref(false);
const editingDatabase = ref<Database | null>(null);
const { canManageDatabases: isAdmin, isReadOnly } = usePermissions();
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
const filteredTables = computed(() => {
  const tables = selectedDatabase.value?.tables ?? [];
  if (tableFilter.value === "enabled") return tables.filter((table) => table.agent_access);
  if (tableFilter.value === "disabled") return tables.filter((table) => !table.agent_access);
  return tables;
});
const tableFilterOptions = [
  { value: "all", label: "全部" },
  { value: "enabled", label: "已授权" },
  { value: "disabled", label: "未授权" },
] as const;

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
  batchMessage.value = "";
  tableFilter.value = "all";
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
  if (!isAdmin.value) return;
  editingDatabase.value = null;
  resetForm();
  errorMessage.value = "";
  modalOpen.value = true;
}

function openEdit(database: Database) {
  if (!isAdmin.value) return;
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
  if (!isAdmin.value) return;
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
  if (!isAdmin.value) return;
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
  if (!table || !isAdmin.value || !database.enabled || batchUpdating.value) return;

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

async function updateAllTableAccess(value: boolean) {
  const database = selectedDatabase.value;
  if (!database || !isAdmin.value || !database.enabled || batchUpdating.value) return;

  const pendingTables = database.tables.filter((table) => table.agent_access !== value);
  if (!pendingTables.length) {
    batchMessage.value = value ? "所有数据表已授权。" : "所有数据表已取消授权。";
    return;
  }

  batchUpdating.value = true;
  batchMessage.value = "正在逐项更新权限…";
  errorMessage.value = "";
  let succeeded = 0;
  let failed = 0;

  for (const table of pendingTables) {
    const previous = table.agent_access;
    table.agent_access = value;
    try {
      const saved = await updateDatabaseTableAccess(database.id, table.table_name, value);
      table.agent_access = saved.agent_access;
      succeeded += 1;
    } catch {
      table.agent_access = previous;
      failed += 1;
    }
  }

  batchUpdating.value = false;
  batchMessage.value = failed
    ? `已更新 ${succeeded} 张表，${failed} 张表失败。`
    : `已更新 ${succeeded} 张表。`;
  if (failed) errorMessage.value = `部分表权限更新失败：${failed} 张表未改变。`;
}

async function removeDatabase(database: Database) {
  if (!isAdmin.value) return;
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
    <p v-if="isReadOnly" class="permission-note" role="status">
      <ShieldCheck :size="15" />当前为只读权限，数据库管理操作仅超级管理员可执行。
    </p>

    <DatabaseLayout
      :databases="databases"
      :selected-database-id="selectedDatabase?.id ?? ''"
      :loading="loading"
      :is-admin="isAdmin"
      @select="selectDatabase"
      @refresh="loadDatabases()"
      @add="openCreate"
    >
      <section
        v-if="selectedDatabase"
        class="database-detail"
        aria-labelledby="database-detail-title"
      >
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
              selectedDatabase.enabled ? 'status-badge--ready' : 'status-badge--interactive',
            ]"
            type="button"
            :disabled="!isAdmin || selectedDatabase.enabled || activatingId !== '' || batchUpdating"
            :title="
              !isAdmin
                ? '仅超级管理员可操作'
                : selectedDatabase.enabled
                  ? '当前 Agent 正在使用此数据库'
                  : '启用此数据库并停用其他数据库'
            "
            :aria-label="!isAdmin ? '启用数据库，仅超级管理员可操作' : '启用数据库'"
            @click="activateDatabase(selectedDatabase)"
          >
            <LoaderCircle v-if="activatingId === selectedDatabase.id" class="spin" :size="13" />
            <Check v-else-if="selectedDatabase.enabled" :size="13" />
            {{
              activatingId === selectedDatabase.id
                ? "启用中"
                : selectedDatabase.enabled
                  ? "已启用"
                  : isAdmin
                    ? "已停用 · 点击启用"
                    : "已停用 · 仅管理员可启用"
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
            <span class="table-heading__count"
              >{{ enabledTableCount }} / {{ selectedDatabase.tables.length }} 已授权</span
            >
          </div>

          <div class="table-controls">
            <div class="table-filter" role="group" aria-label="表权限筛选">
              <button
                v-for="option in tableFilterOptions"
                :key="option.value"
                type="button"
                :class="{ active: tableFilter === option.value }"
                :disabled="batchUpdating"
                @click="tableFilter = option.value"
              >
                {{ option.label }}
              </button>
            </div>
            <div class="table-batch-actions">
              <button
                class="text-action"
                type="button"
                :disabled="!isAdmin || !selectedDatabase.enabled || batchUpdating"
                title="仅超级管理员可操作"
                @click="updateAllTableAccess(true)"
              >
                全部授权
              </button>
              <button
                class="text-action text-action--muted"
                type="button"
                :disabled="!isAdmin || !selectedDatabase.enabled || batchUpdating"
                title="仅超级管理员可操作"
                @click="updateAllTableAccess(false)"
              >
                全部取消
              </button>
            </div>
          </div>

          <p v-if="batchMessage" class="batch-message" role="status" aria-live="polite">
            <LoaderCircle v-if="batchUpdating" class="spin" :size="13" />
            <Check v-else :size="13" />
            {{ batchMessage }}
          </p>

          <div v-if="selectedDatabase.tables.length && filteredTables.length" class="table-list">
            <label
              v-for="table in filteredTables"
              :key="table.table_name"
              class="table-row"
              :class="{ 'table-row--enabled': table.agent_access }"
            >
              <span class="table-row__copy">
                <span class="table-name">{{ table.table_name }}</span>
                <small>{{ table.agent_access ? "允许查询" : "已禁止" }}</small>
              </span>
              <span class="table-row__control">
                <span class="table-row__state">{{ table.agent_access ? "已授权" : "未授权" }}</span>
                <input
                  type="checkbox"
                  :checked="table.agent_access"
                  :disabled="!isAdmin || !selectedDatabase.enabled || batchUpdating"
                  :title="!isAdmin ? '仅超级管理员可操作' : '启用或停用此数据表'"
                  :aria-label="`${table.table_name} ${table.agent_access ? '已授权' : '未授权'}`"
                  @change="
                    toggleTable(
                      selectedDatabase,
                      table.table_name,
                      ($event.target as HTMLInputElement).checked,
                    )
                  "
                />
              </span>
            </label>
          </div>
          <div v-else-if="selectedDatabase.tables.length" class="table-empty">
            当前筛选没有匹配的数据表
          </div>
          <div v-else class="table-empty">请先测试连接以读取数据表</div>
        </div>

        <footer class="detail-actions">
          <button
            class="secondary-button"
            type="button"
            :disabled="!isAdmin || testingId === selectedDatabase.id || batchUpdating"
            :title="!isAdmin ? '仅超级管理员可操作' : '测试连接'"
            :aria-label="!isAdmin ? '测试连接，仅超级管理员可操作' : '测试连接'"
            @click="handleTest(selectedDatabase)"
          >
            <LoaderCircle v-if="testingId === selectedDatabase.id" class="spin" :size="15" />
            <RefreshCw v-else :size="15" />
            {{ testingId === selectedDatabase.id ? "测试中" : "测试连接" }}
          </button>
          <div class="action-group">
            <button
              class="icon-button"
              type="button"
              :title="!isAdmin ? '仅超级管理员可操作' : '编辑数据库'"
              :aria-label="!isAdmin ? '编辑数据库，仅超级管理员可操作' : '编辑数据库'"
              :disabled="!isAdmin || batchUpdating"
              @click="openEdit(selectedDatabase)"
            >
              <Pencil :size="16" />
            </button>
            <button
              class="icon-button icon-button--danger"
              type="button"
              :title="
                !isAdmin
                  ? '仅超级管理员可操作'
                  : selectedDatabase.id === 'demo'
                    ? '演示数据库不能删除'
                    : '删除数据库'
              "
              :aria-label="
                !isAdmin
                  ? '删除数据库，仅超级管理员可操作'
                  : selectedDatabase.id === 'demo'
                    ? '删除数据库，演示数据库不能删除'
                    : '删除数据库'
              "
              :disabled="!isAdmin || selectedDatabase.id === 'demo' || batchUpdating"
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
    </DatabaseLayout>

    <div v-if="modalOpen" class="modal-backdrop" role="presentation" @click.self="closeModal">
      <section class="modal" role="dialog" aria-modal="true" aria-labelledby="database-modal-title">
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
            <input
              v-model="form.path"
              type="text"
              placeholder="data/demo.sqlite"
              :disabled="saving"
            />
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
              <input
                v-model="form.credentialRef"
                type="text"
                placeholder="secret/my-db-readonly"
                :disabled="saving"
              />
            </label>
            <label class="checkbox-line">
              <input v-model="form.tls" type="checkbox" :disabled="saving" />启用 TLS
            </label>
          </template>
          <p v-if="errorMessage && modalOpen" class="form-error" role="alert">{{ errorMessage }}</p>
          <footer class="modal-actions">
            <button class="secondary-button" type="button" :disabled="saving" @click="closeModal">
              取消
            </button>
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
.permission-note {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 12px;
  border: 1px solid #eadfc6;
  border-radius: 7px;
  padding: 8px 11px;
  color: #7d6538;
  background: #fffaf0;
  font-size: 12px;
}

.detail-header,
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

.table-heading p {
  margin-bottom: 0;
  color: #6f7772;
  font-size: 13px;
}

.primary-button,
.secondary-button {
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
.secondary-button:disabled {
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
  font:
    12px ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
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

/* Database workspace visual system. */
.databases-page {
  min-height: 100vh;
  padding: 24px;
  color: #24332a;
  background: #edf1ec;
}

.databases-page > .alert {
  width: min(100%, 1180px);
  margin: 0 auto 14px;
  border-color: #e9c7bd;
  color: #8d4036;
  background: #fff9f6;
}

.database-detail {
  min-height: 100%;
  background: #fbfcfa;
}

.detail-header {
  min-height: 132px;
  padding: 28px 32px 25px;
  border-bottom: 1px solid #e0e7e1;
  background: #fffefa;
}

.database-identity {
  gap: 15px;
}

.database-icon {
  width: 48px;
  height: 48px;
  border: 1px solid #cde1d2;
  border-radius: 9px;
  color: #31744d;
  background: #eaf5ec;
}

.eyebrow {
  margin-bottom: 6px;
  color: #5c8d6d;
  font-size: 10px;
  letter-spacing: 0.13em;
}

.detail-header h2 {
  color: #1f2e25;
  font-size: 23px;
  font-weight: 730;
  letter-spacing: 0;
}

.database-meta {
  display: inline-block;
  margin-top: 5px;
  color: #77857b;
  font:
    11px ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
}

.status-badge {
  min-height: 34px;
  gap: 6px;
  border: 1px solid #ebd5a8;
  border-radius: 7px;
  padding: 0 11px;
  color: #8b672e;
  background: #fff8e8;
  font-size: 12px;
  font-weight: 700;
}

.status-badge--ready {
  border-color: #c4e1cb;
  color: #267044;
  background: #eff9f0;
}

.status-badge--interactive:hover:not(:disabled) {
  border-color: #dfbb6d;
  background: #fff1d2;
}

.detail-summary {
  gap: 10px;
  margin: 24px 32px 0;
  border: 0;
  background: transparent;
}

.summary-item {
  position: relative;
  gap: 6px;
  border: 1px solid #dfe7e0;
  border-radius: 8px;
  padding: 16px 18px;
  background: #fffefa;
  box-shadow: 0 2px 5px rgba(30, 49, 36, 0.025);
}

.summary-item:first-child {
  border-top: 2px solid #81bc90;
}

.summary-item:nth-child(2) {
  border-top: 2px solid #79a8bd;
}

.summary-item:last-child {
  border-top: 2px solid #ccb376;
}

.summary-item strong {
  color: #26372c;
  font-size: 21px;
  font-weight: 730;
}

.summary-item span {
  color: #718075;
  font-size: 11px;
}

.detail-section {
  margin: 30px 32px 0;
}

.table-heading {
  align-items: flex-end;
  margin-bottom: 14px;
}

.table-heading h3 {
  margin-bottom: 6px;
  color: #26372c;
  font-size: 15px;
  font-weight: 720;
}

.table-heading p {
  color: #77857b;
  font-size: 12px;
}

.table-heading > span {
  border: 1px solid #d7e6d9;
  border-radius: 999px;
  padding: 5px 9px;
  color: #477655;
  background: #f1f8f1;
  font-size: 11px;
  font-weight: 650;
}

.table-list {
  gap: 9px 10px;
}

.table-row {
  min-height: 58px;
  border-color: #dfe7e0;
  border-radius: 7px;
  padding: 9px 13px;
  background: #fffefa;
}

.table-row:hover {
  border-color: #a6cdae;
  background: #f7fcf7;
}

.table-row:has(input:checked) {
  border-color: #c2ddc7;
  background: #f6fbf6;
}

.table-name {
  color: #304037;
  font-size: 12px;
}

.table-row small {
  color: #728075;
}

.table-row input,
.checkbox-line input {
  accent-color: #367a4e;
}

.table-empty {
  border: 1px dashed #ccd8ce;
  border-radius: 7px;
  padding: 28px 18px;
  color: #77857b;
  background: #fffefa;
  text-align: center;
}

.detail-actions {
  min-height: 76px;
  margin-top: 30px;
  border-top-color: #e0e7e1;
  padding: 15px 32px;
  background: #fffefa;
}

.secondary-button {
  min-height: 38px;
  border-color: #cfdcd1;
  border-radius: 7px;
  color: #365b42;
  background: #f8fbf8;
  font-weight: 700;
}

.secondary-button:hover:not(:disabled) {
  border-color: #88b797;
  color: #1d6138;
  background: #eff8f0;
}

.primary-button {
  min-height: 40px;
  border-radius: 7px;
  color: #123421;
  background: #bde7c5;
}

.primary-button:hover:not(:disabled) {
  background: #abdbb6;
}

.icon-button {
  border: 1px solid transparent;
  border-radius: 7px;
  color: #617167;
}

.icon-button:hover:not(:disabled) {
  border-color: #c8d9cc;
  color: #28633e;
  background: #f0f8f1;
}

.icon-button--danger:hover {
  border-color: #ebcdcd;
  color: #a94747;
  background: #fff5f5;
}

.database-detail--empty {
  min-height: 680px;
  border: 0;
  color: #77857b;
  background: #fbfcfa;
}

.database-detail--empty svg {
  color: #619274;
}

.modal-backdrop {
  background: rgba(15, 33, 23, 0.52);
}

.modal {
  width: min(100%, 500px);
  border-color: #d4e0d6;
  border-radius: 9px;
  padding: 26px;
  background: #fffefa;
  box-shadow: 0 28px 80px rgba(8, 24, 15, 0.34);
}

.modal-header {
  padding-bottom: 18px;
  border-bottom: 1px solid #e2e9e3;
}

.modal-header h2 {
  color: #233329;
}

.database-form label,
fieldset,
.database-form legend {
  color: #405447;
}

.database-form input[type="text"],
.database-form input[type="number"] {
  border-color: #d2dfd4;
  border-radius: 6px;
  color: #25372b;
  background: #fbfdfb;
}

.database-form input:focus {
  border-color: #6fad80;
  box-shadow: 0 0 0 3px rgba(92, 163, 112, 0.13);
}

.dialect-switch {
  border-color: #d2dfd4;
  border-radius: 7px;
  background: #edf3ee;
}

.dialect-switch button.active {
  color: #205e39;
  background: #fffefa;
}

.database-detail {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

@media (min-width: 1101px) {
  :deep(.database-layout) {
    height: calc(100dvh - 48px);
    min-height: 0;
  }

  :deep(.database-layout__content) {
    overflow-y: auto;
  }

  :deep(.database-sidebar) {
    height: 100%;
    min-height: 0;
  }

  .database-detail {
    min-height: 100%;
  }

  .detail-section {
    padding-bottom: 92px;
  }

  .detail-actions {
    position: sticky;
    z-index: 5;
    bottom: 0;
    margin-top: auto;
    background: #fffefa;
    box-shadow: 0 -8px 18px rgba(30, 49, 36, 0.035);
  }
}

.table-heading__count {
  flex: 0 0 auto;
}

.table-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin: 0 0 12px;
}

.table-filter {
  display: inline-flex;
  gap: 2px;
  border: 1px solid #d9e5db;
  border-radius: 7px;
  padding: 3px;
  background: #f1f6f1;
}

.table-filter button {
  min-height: 28px;
  border: 1px solid transparent;
  border-radius: 5px;
  padding: 0 10px;
  color: #738379;
  background: transparent;
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
}

.table-filter button:hover:not(:disabled),
.table-filter button.active {
  border-color: #c7dfcb;
  color: #28633d;
  background: #fffefa;
  box-shadow: 0 1px 3px rgba(32, 75, 44, 0.08);
}

.table-filter button:disabled,
.text-action:disabled {
  cursor: default;
  opacity: 0.5;
}

.table-batch-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.text-action {
  min-height: 30px;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0 8px;
  color: #39704b;
  background: transparent;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.text-action:hover:not(:disabled) {
  border-color: #cbe0cf;
  background: #f0f8f1;
}

.text-action--muted {
  color: #7d8980;
}

.batch-message {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 10px;
  color: #5c7c65;
  font-size: 11px;
}

.batch-message svg {
  color: #4f9564;
}

.table-row__copy,
.table-row__control {
  display: flex;
  min-width: 0;
  align-items: center;
}

.table-row__copy {
  display: grid;
  gap: 3px;
}

.table-row__control {
  gap: 12px;
  flex: 0 0 auto;
}

.table-row__state {
  min-width: 42px;
  color: #849087;
  font-size: 10px;
  text-align: right;
}

.table-row--enabled .table-row__state {
  color: #4c8a5d;
}

.table-row input {
  margin: 0;
}

@media (max-width: 700px) {
  .table-controls {
    align-items: flex-start;
    flex-direction: column;
  }

  .table-batch-actions {
    align-self: flex-end;
  }
}

@media (max-width: 1100px) {
  .databases-page {
    padding: 22px 16px 32px;
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

  .detail-header,
  .detail-actions {
    padding-inline: 22px;
  }

  .detail-summary,
  .detail-section {
    margin-inline: 22px;
  }

  .database-detail {
    display: block;
    min-height: 0;
  }

  .detail-section {
    padding-bottom: 0;
  }

  .detail-actions {
    position: static;
    margin-top: 30px;
    box-shadow: none;
  }
}

@media (max-width: 520px) {
  .databases-page {
    padding: 10px;
  }

  .detail-header {
    padding: 22px 18px;
  }

  .detail-actions {
    padding-inline: 18px;
  }

  .detail-summary,
  .detail-section {
    margin-inline: 18px;
  }

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
