<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  KeyRound,
  LockKeyhole,
  LoaderCircle,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
  UsersRound,
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
      <div class="summary-item summary-item--members">
        <span class="summary-icon"><UsersRound :size="17" /></span>
        <div>
          <strong>{{ members.length }}</strong>
          <span>成员总数</span>
        </div>
      </div>
      <div class="summary-item summary-item--admin">
        <span class="summary-icon"><ShieldCheck :size="17" /></span>
        <div>
          <strong>{{ members.filter((member) => member.role === "super_admin").length }}</strong>
          <span>超级管理员</span>
        </div>
      </div>
      <div class="summary-item summary-item--secure">
        <span class="summary-icon"><LockKeyhole :size="17" /></span>
        <div>
          <strong>HttpOnly</strong>
          <span>安全会话</span>
        </div>
      </div>
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
              @click="removeMember(member)"
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
  </main>
</template>

<style scoped>
.members-page {
  min-height: 100dvh;
  padding: 24px clamp(20px, 4vw, 64px) 48px;
  color: #203027;
  background: #f4f7f5;
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
  max-width: 1440px;
  margin: 0 auto 14px;
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
  min-height: 38px;
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
  box-shadow: 0 5px 12px rgba(61, 142, 88, 0.12);
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
  display: grid;
  max-width: 1440px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 0 auto 18px;
}
.summary-item {
  display: flex;
  min-height: 78px;
  align-items: center;
  gap: 12px;
  border: 1px solid #dfe8e1;
  border-radius: 9px;
  padding: 15px 18px;
  background: #fff;
  box-shadow: 0 5px 14px rgba(33, 67, 47, 0.045);
}
.summary-icon {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
  color: #39805a;
  background: #e8f4eb;
}
.summary-item--admin .summary-icon {
  color: #8b7040;
  background: #f7f0df;
}
.summary-item--secure .summary-icon {
  color: #526f99;
  background: #eaf0f8;
}
.summary-item > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.summary-item strong {
  color: #24362b;
  font-size: 20px;
  line-height: 1.1;
}
.summary-item > div > span {
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
  max-width: 1440px;
  margin: 0 auto;
  border: 1px solid #e0e7e2;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(32, 64, 45, 0.045);
}
.surface-heading {
  align-items: center;
  min-height: 92px;
  padding: 18px 22px;
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
.member-cards {
  display: grid;
  gap: 10px;
  padding: 14px 16px 16px;
}
.member-card {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 1fr) auto;
  align-items: center;
  gap: 20px;
  min-height: 96px;
  border: 1px solid #e0e7e2;
  border-radius: 8px;
  padding: 15px 18px;
  background: #fbfdfb;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}
.member-card:hover {
  border-color: #c8dbcd;
  box-shadow: 0 6px 16px rgba(38, 74, 51, 0.07);
  transform: translateY(-1px);
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
  color: #26382c;
  font-size: 15px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.avatar {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  color: #397453;
  background: #e8f4eb;
}
.role-badge {
  border-radius: 999px;
  padding: 5px 8px;
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
.member-card__details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.member-detail {
  display: grid;
  align-items: start;
  gap: 7px;
}
.detail-label {
  color: #8a968e;
  font-size: 11px;
}
.date-value {
  color: #78847d;
  font-size: 13px;
}
.member-card__actions {
  justify-content: flex-end;
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
  color: #9aa49e;
  font-size: 11px;
  white-space: nowrap;
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
  background: rgba(22, 37, 29, 0.28);
  backdrop-filter: blur(2px);
}
.modal {
  width: min(100%, 440px);
  border: 1px solid #dfe7e1;
  border-radius: 12px;
  padding: 22px;
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
    padding: 16px 12px 32px;
  }
  .summary-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .summary-item:last-child {
    grid-column: 1 / -1;
  }
  .surface-heading {
    display: grid;
    gap: 14px;
    min-height: 0;
    padding: 16px;
  }
  .member-cards {
    padding: 10px;
  }
  .member-card {
    grid-template-columns: 1fr auto;
    gap: 18px;
    padding: 15px;
  }
  .member-card__details {
    grid-column: 1 / -1;
    gap: 14px;
  }
  .member-card__actions {
    grid-column: 2;
    grid-row: 1;
  }
}

@media (min-width: 641px) and (max-width: 980px) {
  .member-card {
    grid-template-columns: minmax(0, 1fr) minmax(220px, 0.9fr) auto;
    gap: 14px;
  }
}
</style>
