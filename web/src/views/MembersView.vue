<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  KeyRound,
  LoaderCircle,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
  X,
} from "lucide-vue-next";
import {
  ApiRequestError,
  createMember,
  deleteMember,
  fetchMembers,
  updateMember,
} from "@/api/client";
import { getDemoRole } from "@/auth/auth";
import type { Member } from "@/types/api";

const members = ref<Member[]>([]);
const loading = ref(true);
const saving = ref(false);
const errorMessage = ref("");
const modalOpen = ref(false);
const editingMember = ref<Member | null>(null);
const role = getDemoRole();
const isAdmin = computed(() => role === "super_admin");
const form = reactive({ username: "", password: "", confirmPassword: "" });

async function loadMembers() {
  loading.value = true;
  errorMessage.value = "";
  try {
    members.value = await fetchMembers();
  } catch (error) {
    errorMessage.value = error instanceof ApiRequestError ? error.message : "成员列表加载失败。";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingMember.value = null;
  form.username = "";
  form.password = "";
  form.confirmPassword = "";
  errorMessage.value = "";
  modalOpen.value = true;
}

function openEdit(member: Member) {
  editingMember.value = member;
  form.username = member.username;
  form.password = "";
  form.confirmPassword = "";
  errorMessage.value = "";
  modalOpen.value = true;
}

function closeModal() {
  if (!saving.value) modalOpen.value = false;
}

async function saveMember() {
  if (!form.username.trim()) {
    errorMessage.value = "请输入用户名。";
    return;
  }
  if (!editingMember.value && form.password.length < 6) {
    errorMessage.value = "密码至少需要 6 个字符。";
    return;
  }
  if (form.password && form.password !== form.confirmPassword) {
    errorMessage.value = "两次输入的密码不一致。";
    return;
  }
  saving.value = true;
  errorMessage.value = "";
  try {
    const payload = {
      username: form.username.trim(),
      ...(form.password ? { password: form.password } : {}),
    };
    const saved = editingMember.value
      ? await updateMember(editingMember.value.id, payload)
      : await createMember({ username: payload.username, password: form.password });
    const index = members.value.findIndex((member) => member.id === saved.id);
    if (index === -1) members.value.push(saved);
    else members.value[index] = saved;
    modalOpen.value = false;
  } catch (error) {
    errorMessage.value = error instanceof ApiRequestError ? error.message : "保存成员失败。";
  } finally {
    saving.value = false;
  }
}

async function removeMember(member: Member) {
  if (!window.confirm(`确定删除成员“${member.username}”吗？`)) return;
  errorMessage.value = "";
  try {
    await deleteMember(member.id);
    members.value = members.value.filter((item) => item.id !== member.id);
  } catch (error) {
    errorMessage.value = error instanceof ApiRequestError ? error.message : "删除成员失败。";
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(new Date(value));
}

onMounted(() => void loadMembers());
</script>

<template>
  <main class="members-page">
    <div class="members-toolbar">
      <button v-if="isAdmin" class="primary-button" type="button" @click="openCreate">
        <Plus :size="17" /> 添加成员
      </button>
    </div>

    <section class="summary-row" aria-label="成员概览">
      <div class="summary-item">
        <strong>{{ members.length }}</strong
        ><span>成员总数</span>
      </div>
      <div class="summary-item">
        <strong>{{ members.filter((member) => member.role === "super_admin").length }}</strong
        ><span>超级管理员</span>
      </div>
      <div class="summary-item"><strong>HttpOnly</strong><span>安全会话</span></div>
    </section>

    <p v-if="errorMessage && !modalOpen" class="alert" role="alert">{{ errorMessage }}</p>

    <section class="members-surface" aria-labelledby="members-title">
      <div class="surface-heading">
        <div>
          <h2 id="members-title">账号列表</h2>
          <p>密码仅保存为安全哈希，页面不会显示明文密码。</p>
        </div>
        <span class="permission-note"
          ><ShieldCheck :size="15" /> {{ isAdmin ? "管理员权限" : "只读权限" }}</span
        >
      </div>

      <div v-if="loading" class="empty-state">
        <LoaderCircle class="spin" :size="22" />正在加载成员
      </div>
      <div v-else-if="members.length === 0" class="empty-state">
        <UserRound :size="22" />暂无成员
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>用户名</th>
              <th>角色</th>
              <th>密码</th>
              <th>创建时间</th>
              <th v-if="isAdmin" class="actions-heading">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="member in members" :key="member.id">
              <td>
                <span class="member-name"
                  ><span class="avatar"><UserRound :size="15" /></span>{{ member.username }}</span
                >
              </td>
              <td>
                <span
                  :class="['role-badge', member.role === 'super_admin' ? 'role-badge--admin' : '']"
                  ><ShieldCheck v-if="member.role === 'super_admin'" :size="13" />{{
                    member.role === "super_admin" ? "超级管理员" : "普通成员"
                  }}</span
                >
              </td>
              <td>
                <span class="password-mask"><KeyRound :size="14" />••••••••</span>
              </td>
              <td class="date-cell">{{ formatDate(member.created_at) }}</td>
              <td v-if="isAdmin" class="actions-cell">
                <button
                  v-if="member.role !== 'super_admin'"
                  class="icon-button"
                  type="button"
                  aria-label="编辑成员"
                  title="编辑成员"
                  @click="openEdit(member)"
                >
                  <Pencil :size="16" />
                </button>
                <span v-else class="protected-label">受保护</span>
                <button
                  v-if="member.role !== 'super_admin'"
                  class="icon-button icon-button--danger"
                  type="button"
                  aria-label="删除成员"
                  title="删除成员"
                  @click="removeMember(member)"
                >
                  <Trash2 :size="16" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="modalOpen" class="modal-backdrop" role="presentation" @click.self="closeModal">
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="editingMember ? 'edit-member-title' : 'create-member-title'"
      >
        <header class="modal-header">
          <div>
            <p class="modal-eyebrow">{{ editingMember ? "EDIT MEMBER" : "NEW MEMBER" }}</p>
            <h2 :id="editingMember ? 'edit-member-title' : 'create-member-title'">
              {{ editingMember ? "编辑成员" : "添加成员" }}
            </h2>
          </div>
          <button
            class="close-button"
            type="button"
            aria-label="关闭"
            title="关闭"
            @click="closeModal"
          >
            <X :size="19" />
          </button>
        </header>
        <form class="member-form" @submit.prevent="saveMember">
          <label
            >用户名<input
              v-model="form.username"
              type="text"
              autocomplete="username"
              :disabled="saving"
          /></label>
          <label
            >密码<small v-if="editingMember">留空表示保持原密码</small
            ><input
              v-model="form.password"
              type="password"
              :autocomplete="editingMember ? 'new-password' : 'new-password'"
              :disabled="saving"
          /></label>
          <label
            >确认密码<input
              v-model="form.confirmPassword"
              type="password"
              autocomplete="new-password"
              :disabled="saving"
          /></label>
          <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
          <footer class="modal-actions">
            <button class="secondary-button" type="button" :disabled="saving" @click="closeModal">
              取消</button
            ><button class="primary-button" type="submit" :disabled="saving">
              <LoaderCircle v-if="saving" class="spin" :size="16" />{{
                saving ? "保存中" : "保存成员"
              }}
            </button>
          </footer>
        </form>
      </section>
    </div>
  </main>
</template>

<style scoped>
.members-page {
  min-height: 100vh;
  padding: 28px clamp(24px, 5vw, 72px);
  color: #203027;
  background: #f7f9f7;
}
.members-toolbar,
.surface-heading,
.modal-header,
.modal-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.members-toolbar {
  justify-content: flex-end;
  margin-bottom: 18px;
}
.modal-eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 12px;
  color: #4c9065;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
}
h2 {
  margin: 0;
  font-size: 18px;
}
.surface-heading p {
  margin: 10px 0 0;
  color: #718077;
  font-size: 13px;
}
.primary-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  border: 0;
  border-radius: 7px;
  padding: 0 15px;
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
}
.primary-button {
  color: #143322;
  background: #b7e7cb;
}
.primary-button:hover {
  background: #a6dbb9;
}
.secondary-button {
  border: 1px solid #d9e0db;
  color: #55645b;
  background: #fff;
}
.summary-row {
  display: flex;
  gap: 1px;
  margin: 38px 0 20px;
  border: 1px solid #e0e7e2;
  background: #e0e7e2;
}
.summary-item {
  display: grid;
  flex: 1;
  gap: 5px;
  padding: 18px 22px;
  background: #fff;
}
.summary-item strong {
  font-size: 22px;
}
.summary-item span {
  color: #7d8a82;
  font-size: 11px;
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
.members-surface {
  border: 1px solid #e0e7e2;
  background: #fff;
}
.surface-heading {
  align-items: center;
  padding: 22px 24px;
  border-bottom: 1px solid #edf0ed;
}
.permission-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #5c8069;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
th {
  color: #87928b;
  background: #fbfcfb;
  font-size: 11px;
  font-weight: 750;
}
th,
td {
  padding: 16px 24px;
  border-bottom: 1px solid #edf0ed;
}
td {
  color: #39483f;
  font-size: 13px;
}
tbody tr:last-child td {
  border-bottom: 0;
}
.member-name,
.password-mask,
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.avatar {
  display: grid;
  width: 29px;
  height: 29px;
  place-items: center;
  border-radius: 50%;
  color: #397453;
  background: #e8f4eb;
}
.role-badge {
  border-radius: 999px;
  padding: 6px 9px;
  color: #657269;
  background: #f2f4f2;
  font-size: 11px;
}
.role-badge--admin {
  color: #397453;
  background: #e8f4eb;
}
.password-mask {
  color: #8a988f;
  letter-spacing: 0.18em;
}
.password-mask svg {
  letter-spacing: 0;
}
.date-cell {
  color: #78847d;
}
.actions-heading,
.actions-cell {
  text-align: right;
}
.actions-cell {
  white-space: nowrap;
}
.icon-button,
.close-button {
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
.icon-button:hover,
.close-button:hover {
  background: #eef5ef;
  color: #326d4c;
}
.icon-button--danger:hover {
  color: #b65353;
  background: #fff0f0;
}
.protected-label {
  margin-right: 8px;
  color: #9aa49e;
  font-size: 11px;
}
.empty-state {
  display: flex;
  min-height: 190px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: #7b887f;
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
  width: min(100%, 440px);
  border: 1px solid #dfe7e1;
  border-radius: 9px;
  padding: 24px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(22, 37, 29, 0.22);
}
.modal-header {
  align-items: flex-start;
  margin-bottom: 24px;
}
.close-button {
  flex: 0 0 auto;
}
.member-form {
  display: grid;
  gap: 16px;
}
.member-form label {
  display: grid;
  gap: 7px;
  color: #4a5b50;
  font-size: 12px;
  font-weight: 700;
}
.member-form small {
  margin-left: 6px;
  color: #8d9991;
  font-size: 11px;
  font-weight: 400;
}
.member-form input {
  width: 100%;
  height: 42px;
  border: 1px solid #d9e2db;
  border-radius: 6px;
  padding: 0 11px;
  color: #26382c;
  outline: 0;
  background: #fbfdfb;
  font-size: 13px;
}
.member-form input:focus {
  border-color: #78b58b;
  box-shadow: 0 0 0 3px rgba(104, 181, 130, 0.12);
}
.modal-actions {
  align-items: center;
  justify-content: flex-end;
  margin-top: 5px;
}
@media (max-width: 640px) {
  .members-page {
    padding: 20px 16px;
  }
  .summary-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .summary-item:last-child {
    grid-column: 1 / -1;
  }
  .surface-heading {
    display: grid;
    gap: 14px;
    padding: 18px;
  }
  th,
  td {
    padding: 13px 14px;
  }
}
</style>
