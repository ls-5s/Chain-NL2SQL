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
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import type { Member } from "@/types/api";

const members = ref<Member[]>([]);
const loading = ref(true);
const saving = ref(false);
const errorMessage = ref("");
const modalOpen = ref(false);
const deleteTarget = ref<Member | null>(null);
const deleting = ref(false);
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

function openDelete(member: Member) {
  deleteTarget.value = member;
  errorMessage.value = "";
}

function closeDeleteModal() {
  if (!deleting.value) deleteTarget.value = null;
}

async function removeMember() {
  const member = deleteTarget.value;
  if (!member || deleting.value) return;
  deleting.value = true;
  errorMessage.value = "";
  try {
    await deleteMember(member.id);
    members.value = members.value.filter((item) => item.id !== member.id);
    deleteTarget.value = null;
  } catch (error) {
    errorMessage.value = error instanceof ApiRequestError ? error.message : "删除成员失败。";
  } finally {
    deleting.value = false;
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(new Date(value));
}

onMounted(() => void loadMembers());
</script>

<template>
  <main class="members-page">
    <p v-if="errorMessage && !modalOpen && !deleteTarget" class="alert" role="alert">
      {{ errorMessage }}
    </p>

    <section class="members-surface" aria-labelledby="members-title">
      <div class="surface-heading">
        <div>
          <h2 id="members-title">账号列表</h2>
          <p>密码仅保存为安全哈希，页面不会显示明文密码。</p>
        </div>
        <div class="surface-actions">
          <button v-if="isAdmin" class="primary-button" type="button" @click="openCreate">
            <Plus :size="17" /> 添加成员
          </button>
          <span class="permission-note"
            ><ShieldCheck :size="15" /> {{ isAdmin ? "管理员权限" : "只读权限" }}</span
          >
        </div>
      </div>

      <div v-if="loading" class="empty-state">
        <LoaderCircle class="spin" :size="22" />正在加载成员
      </div>
      <div v-else-if="members.length === 0" class="empty-state">
        <UserRound :size="22" />暂无成员
      </div>
      <div v-else class="member-cards">
        <article v-for="member in members" :key="member.id" class="member-card">
          <div class="member-card__header">
            <div class="member-identity">
              <span class="avatar"><UserRound :size="17" /></span>
              <div>
                <h3>{{ member.username }}</h3>
                <span
                  :class="['role-badge', member.role === 'super_admin' ? 'role-badge--admin' : '']"
                  ><ShieldCheck v-if="member.role === 'super_admin'" :size="13" />{{
                    member.role === "super_admin" ? "超级管理员" : "普通成员"
                  }}</span
                >
              </div>
            </div>
            <span v-if="isAdmin && member.role === 'super_admin'" class="protected-label"
              >受保护</span
            >
          </div>

          <div class="member-card__details">
            <div class="member-detail">
              <span class="detail-label">密码</span>
              <span class="password-mask"><KeyRound :size="14" />••••••••</span>
            </div>
            <div class="member-detail">
              <span class="detail-label">创建时间</span>
              <span class="date-value">{{ formatDate(member.created_at) }}</span>
            </div>
          </div>

          <div v-if="isAdmin && member.role !== 'super_admin'" class="member-card__actions">
            <button
              class="icon-button"
              type="button"
              aria-label="编辑成员"
              title="编辑成员"
              @click="openEdit(member)"
            >
              <Pencil :size="16" />
            </button>
            <button
              class="icon-button icon-button--danger"
              type="button"
              aria-label="删除成员"
              title="删除成员"
              @click="openDelete(member)"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </article>
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

    <ConfirmDialog
      :open="Boolean(deleteTarget)"
      title="删除成员"
      confirm-text="删除成员"
      busy-text="删除中"
      :busy="deleting"
      :error="errorMessage"
      @update:open="closeDeleteModal"
      @confirm="removeMember"
    >
      <template #icon><Trash2 :size="18" /></template>
      <template #description>
        确定要删除成员“{{ deleteTarget?.username }}”吗？此操作无法撤销。
      </template>
    </ConfirmDialog>
  </main>
</template>

<style scoped>
.members-page {
  min-height: 100dvh;
  padding: 28px clamp(20px, 4vw, 68px) 56px;
  color: #202123;
  background: #f7f7f5;
}
.surface-heading,
.modal-header,
.modal-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.modal-eyebrow {
  margin: 0 0 8px;
  color: #8b8b88;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}
h2 {
  margin: 0;
  color: #202123;
  font-size: 20px;
  font-weight: 650;
  letter-spacing: 0;
}
.surface-heading p {
  margin: 8px 0 0;
  color: #777875;
  font-size: 13px;
}
.primary-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  border-radius: 8px;
  padding: 0 15px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background-color 150ms ease,
    border-color 150ms ease,
    color 150ms ease,
    box-shadow 150ms ease;
}
.primary-button {
  border: 1px solid #202123;
  color: #ffffff;
  background: #202123;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}
.primary-button:hover:not(:disabled) {
  border-color: #343536;
  background: #343536;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
}
.secondary-button {
  border: 1px solid #d6d6d3;
  color: #4f504e;
  background: #ffffff;
}
.secondary-button:hover:not(:disabled) {
  border-color: #bdbdb9;
  background: #f6f6f4;
}
.primary-button:disabled,
.secondary-button:disabled,
.icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.alert,
.form-error {
  margin: 16px auto;
  max-width: 1320px;
  border: 1px solid #ebcaca;
  border-radius: 8px;
  padding: 11px 13px;
  color: #9c4141;
  background: #fff8f8;
  font-size: 13px;
}
.members-surface {
  max-width: 1320px;
  margin: 0 auto;
  overflow: hidden;
  border: 1px solid #e4e4e1;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.035);
}
.surface-heading {
  align-items: center;
  min-height: 92px;
  padding: 20px 24px;
  border-bottom: 1px solid #ecece9;
}
.surface-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 18px;
}
.permission-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #557661;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}
.member-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 360px));
  justify-content: start;
  gap: 16px;
  padding: 18px;
}
.member-card {
  display: grid;
  width: 100%;
  aspect-ratio: 1 / 1;
  grid-template-rows: auto 1fr auto;
  align-items: stretch;
  gap: 18px;
  border: 1px solid #e3e3e0;
  border-radius: 10px;
  padding: 18px;
  background: #ffffff;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease,
    transform 150ms ease;
}
.member-card:hover {
  border-color: #c9c9c5;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}
.member-card:focus-within {
  border-color: #8b8c88;
  box-shadow: 0 0 0 3px rgba(32, 33, 35, 0.08);
}
.member-card__header,
.member-identity,
.member-card__details,
.member-detail,
.member-card__actions,
.password-mask,
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.member-card__header {
  display: flex;
  min-width: 0;
  justify-content: space-between;
  gap: 14px;
}
.member-identity {
  min-width: 0;
}
.member-identity > div {
  min-width: 0;
}
.member-identity h3 {
  overflow: hidden;
  margin: 0 0 8px;
  color: #202123;
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.avatar {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  color: #565754;
  background: #f0f0ee;
}
.role-badge {
  border-radius: 999px;
  padding: 5px 8px;
  color: #6d6e6b;
  background: #f1f1ef;
  font-size: 11px;
}
.role-badge--admin {
  color: #4d765b;
  background: #edf6ef;
}
.password-mask {
  color: #8a8b87;
  letter-spacing: 0.16em;
}
.password-mask svg {
  color: #979894;
  letter-spacing: 0;
}
.member-card__details {
  display: grid;
  align-content: center;
  grid-template-columns: 1fr;
  gap: 18px;
}
.member-detail {
  display: grid;
  align-items: start;
  gap: 7px;
}
.detail-label {
  color: #969793;
  font-size: 11px;
}
.date-value {
  color: #666764;
  font-size: 13px;
}
.member-card__actions {
  justify-content: flex-end;
  min-height: 32px;
}
.icon-button,
.close-button {
  display: inline-grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #777875;
  background: transparent;
  cursor: pointer;
  transition:
    background-color 150ms ease,
    border-color 150ms ease,
    color 150ms ease;
}
.icon-button:hover:not(:disabled),
.close-button:hover {
  border-color: #e0e0dd;
  color: #202123;
  background: #f4f4f2;
}
.icon-button:focus-visible,
.close-button:focus-visible {
  outline: 2px solid #6f8b77;
  outline-offset: 2px;
}
.icon-button--danger:hover:not(:disabled) {
  border-color: #efd5d5;
  color: #a44747;
  background: #fff5f5;
}
.protected-label {
  color: #969793;
  font-size: 11px;
  white-space: nowrap;
}
.empty-state {
  display: flex;
  min-height: 190px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: #777875;
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
  background: rgba(32, 33, 35, 0.24);
  backdrop-filter: blur(2px);
}
.modal {
  width: min(100%, 440px);
  border: 1px solid #e0e0dd;
  border-radius: 12px;
  padding: 24px;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.16);
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
  color: #4f504e;
  font-size: 12px;
  font-weight: 650;
}
.member-form small {
  margin-left: 6px;
  color: #969793;
  font-size: 11px;
  font-weight: 400;
}
.member-form input {
  width: 100%;
  height: 42px;
  border: 1px solid #d8d8d5;
  border-radius: 7px;
  padding: 0 11px;
  color: #202123;
  outline: 0;
  background: #ffffff;
  font-size: 13px;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease;
}
.member-form input:hover:not(:disabled) {
  border-color: #bdbdb9;
}
.member-form input:focus {
  border-color: #777875;
  box-shadow: 0 0 0 3px rgba(32, 33, 35, 0.1);
}
.modal-actions {
  align-items: center;
  justify-content: flex-end;
  margin-top: 5px;
}
@media (max-width: 640px) {
  .members-page {
    padding: 16px 12px 32px;
  }
  .surface-heading {
    display: grid;
    gap: 14px;
    min-height: 0;
    padding: 18px 16px;
  }
  .surface-actions {
    width: 100%;
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }
  .surface-actions .primary-button {
    width: 100%;
  }
  .member-cards {
    grid-template-columns: minmax(0, 1fr);
    padding: 12px;
  }
  .member-card {
    max-width: none;
    gap: 14px;
    padding: 16px;
  }
  .member-card__details {
    gap: 14px;
  }
  .member-card__actions {
    justify-content: flex-start;
  }
  .modal-backdrop {
    padding: 12px;
  }
  .modal {
    padding: 20px;
  }
}
</style>
