<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowRight,
  ArrowUpRight,
  Database,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  Table2,
  UserRound,
} from "lucide-vue-next";

import { isAuthenticated, login } from "@/auth/auth";

const router = useRouter();
const route = useRoute();
const username = ref("");
const password = ref("");
const showPassword = ref(false);
const submitting = ref(false);
const errorMessage = ref("");

function safeRedirect(): string {
  const redirect = route.query.redirect;
  return typeof redirect === "string" &&
    redirect.startsWith("/") &&
    !redirect.startsWith("//") &&
    redirect !== "/login"
    ? redirect
    : "/query";
}

function redirectAfterLogin(): void {
  void router.replace(safeRedirect());
}

function submit(): void {
  if (submitting.value) return;
  errorMessage.value = "";
  if (!username.value.trim() || !password.value) {
    errorMessage.value = "请输入用户名和密码。";
    return;
  }
  submitting.value = true;
  if (!login({ username: username.value, password: password.value })) {
    errorMessage.value = "用户名或密码不正确。";
    submitting.value = false;
    return;
  }
  redirectAfterLogin();
}

if (isAuthenticated()) redirectAfterLogin();
</script>

<template>
  <main class="login-page">
    <section class="login-story" aria-label="Chain-NL2SQL 数据语义工作台">
      <div class="story-inner">
        <div class="brand-lockup">
          <span class="brand-mark"><Database :size="20" :stroke-width="2.2" /></span>
          <span class="brand-name">Chain-NL2SQL</span>
          <span class="brand-badge">WORKSPACE</span>
        </div>

        <div class="story-main">
          <div class="story-copy">
            <p class="story-kicker"><Sparkles :size="15" /> 数据语义工作台</p>
            <h1>让数据<br /><em>回答问题。</em></h1>
            <p class="story-description">把自然语言带进你的数据世界，清晰地理解每一次查询。</p>
          </div>

          <div class="query-preview" aria-label="数据查询预览">
            <div class="preview-header">
              <span class="preview-label">LIVE QUERY</span>
              <span class="preview-status"><i /> READY</span>
            </div>
            <div class="preview-prompt">
              <span class="prompt-symbol">&gt;</span>
              <span>本月各业务线的收入趋势</span>
              <ArrowUpRight :size="17" />
            </div>
            <div class="preview-schema">
              <div class="schema-item">
                <Table2 :size="15" /><span>revenue</span><small>table</small>
              </div>
              <div class="schema-item">
                <Table2 :size="15" /><span>business_line</span><small>field</small>
              </div>
              <div class="schema-item">
                <Table2 :size="15" /><span>growth_rate</span><small>metric</small>
              </div>
            </div>
          </div>
        </div>

        <div class="story-footer">
          <span><ShieldCheck :size="15" /> 受控访问</span>
          <span>只读查询 · 本地演示环境</span>
        </div>
      </div>
    </section>

    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-panel__inner">
        <div class="login-heading">
          <p class="login-eyebrow">SECURE WORKSPACE</p>
          <h2 id="login-title">欢迎回来</h2>
          <p>登录后继续使用数据问答与知识库。</p>
        </div>

        <form class="login-form" :aria-busy="submitting" @submit.prevent="submit">
          <div class="form-field">
            <label class="field-label" for="username">用户名</label>
            <div class="field-control">
              <UserRound :size="18" aria-hidden="true" />
              <input
                id="username"
                v-model="username"
                autocomplete="username"
                placeholder="请输入用户名"
                type="text"
                :disabled="submitting"
              />
            </div>
          </div>

          <div class="form-field">
            <label class="field-label" for="password">密码</label>
            <div class="field-control">
              <LockKeyhole :size="18" aria-hidden="true" />
              <input
                id="password"
                v-model="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                :type="showPassword ? 'text' : 'password'"
                :disabled="submitting"
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :title="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" :size="18" />
                <Eye v-else :size="18" />
              </button>
            </div>
          </div>

          <p v-if="errorMessage" class="login-error" role="alert" aria-live="polite">
            {{ errorMessage }}
          </p>
          <button class="login-submit" type="submit" :disabled="submitting">
            <span>{{ submitting ? "正在登录" : "登录工作区" }}</span>
            <LoaderCircle v-if="submitting" class="loading-icon" :size="18" aria-hidden="true" />
            <ArrowRight v-else :size="18" aria-hidden="true" />
          </button>
        </form>

        <div class="login-note">
          <ShieldCheck :size="17" /><span>本地演示环境 · 会话状态仅保存在当前浏览器</span>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  min-height: 100dvh;
  grid-template-columns: minmax(0, 1.04fr) minmax(460px, 0.96fr);
  background: #f4f6f2;
  color: #182720;
}
.login-story {
  position: relative;
  overflow: hidden;
  background: #182720;
  color: #f4f8f4;
}
.story-inner {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: clamp(34px, 5vw, 78px) clamp(32px, 7vw, 112px);
}
.brand-lockup {
  display: flex;
  align-items: center;
  gap: 11px;
}
.brand-mark {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid rgba(213, 242, 224, 0.24);
  border-radius: 10px;
  color: #182720;
  background: #c1e8d2;
}
.brand-name {
  font-size: 15px;
  font-weight: 760;
  letter-spacing: 0;
}
.brand-badge {
  margin-left: 4px;
  border: 1px solid rgba(203, 231, 215, 0.24);
  border-radius: 4px;
  padding: 4px 7px;
  color: #a9c5b3;
  font-size: 9px;
  font-weight: 760;
  letter-spacing: 0.08em;
}
.story-main {
  display: flex;
  margin: auto 0;
  flex-direction: column;
  padding: 56px 0 62px;
}
.story-copy {
  max-width: 560px;
}
.story-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 20px;
  color: #afd7bc;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.story-copy h1 {
  margin: 0;
  color: #f5faf6;
  font-size: clamp(42px, 5vw, 72px);
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.04;
}
.story-copy h1 em {
  color: #c1e8d2;
  font-style: normal;
}
.story-description {
  max-width: 360px;
  margin: 24px 0 0;
  color: #a5b8ab;
  font-size: 15px;
  line-height: 1.75;
}
.query-preview {
  width: min(100%, 560px);
  margin-top: 48px;
  border: 1px solid rgba(196, 229, 208, 0.2);
  border-radius: 10px;
  background: #20352b;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(196, 229, 208, 0.14);
  padding: 14px 17px;
}
.preview-label {
  color: #89b79a;
  font-size: 10px;
  font-weight: 760;
  letter-spacing: 0.12em;
}
.preview-status {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #abdcb8;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
}
.preview-status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #8de1a3;
}
.preview-prompt {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 21px 17px 18px;
  color: #eef8f0;
  font-size: 14px;
}
.prompt-symbol {
  color: #9bdfb0;
  font-weight: 800;
}
.preview-prompt svg {
  margin-left: auto;
  color: #88b99b;
}
.preview-schema {
  display: flex;
  gap: 9px;
  border-top: 1px solid rgba(196, 229, 208, 0.12);
  padding: 14px 17px 16px;
}
.schema-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 6px;
  color: #cce4d2;
  font-size: 11px;
}
.schema-item svg {
  flex: 0 0 auto;
  color: #81bd93;
}
.schema-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.schema-item small {
  color: #7e9a86;
  font-size: 9px;
}
.story-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-top: 1px solid rgba(196, 229, 208, 0.15);
  padding-top: 17px;
  color: #829b89;
  font-size: 11px;
}
.story-footer span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.story-footer span:first-child {
  color: #b9d9c1;
}
.login-panel {
  display: grid;
  place-items: center;
  padding: 48px clamp(32px, 7vw, 110px);
  background: #f4f6f2;
}
.login-panel__inner {
  width: min(100%, 420px);
}
.login-heading {
  margin-bottom: 38px;
}
.login-eyebrow {
  margin: 0 0 13px;
  color: #4d936b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.13em;
}
.login-heading h2 {
  margin: 0;
  color: #182720;
  font-size: clamp(30px, 3vw, 40px);
  font-weight: 720;
  letter-spacing: 0;
  line-height: 1.12;
}
.login-heading > p:last-child {
  margin: 12px 0 0;
  color: #718078;
  font-size: 14px;
  line-height: 1.65;
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.form-field {
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.field-label {
  color: #3d4e43;
  font-size: 13px;
  font-weight: 700;
}
.field-control {
  display: flex;
  height: 52px;
  align-items: center;
  gap: 11px;
  border: 1px solid #d3ddd5;
  border-radius: 8px;
  padding: 0 14px;
  color: #7b8b80;
  background: #fff;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease;
}
.field-control:focus-within {
  border-color: #5b9b75;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(91, 155, 117, 0.13);
}
.field-control input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: #182720;
  background: transparent;
  font-size: 14px;
}
.field-control input::placeholder {
  color: #a0aca3;
}
.field-control input:disabled {
  cursor: wait;
}
.password-toggle {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  border-radius: 6px;
  color: #839187;
  background: transparent;
  cursor: pointer;
}
.password-toggle:hover {
  color: #182720;
  background: #edf3ee;
}
.login-error {
  margin: -5px 0 -2px;
  color: #b64c43;
  font-size: 13px;
  line-height: 1.5;
}
.login-submit {
  display: flex;
  width: 100%;
  height: 52px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  margin-top: 2px;
  border: 0;
  border-radius: 8px;
  color: #14221b;
  background: #bfe6d1;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    transform 0.18s ease,
    opacity 0.18s ease;
}
.login-submit:hover:not(:disabled) {
  background: #aee0c4;
  transform: translateY(-1px);
}
.login-submit:active:not(:disabled) {
  transform: translateY(0);
}
.login-submit:disabled {
  cursor: wait;
  opacity: 0.7;
}
.loading-icon {
  animation: login-spin 0.8s linear infinite;
}
.login-note {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: 30px;
  border-top: 1px solid #dfe6df;
  padding-top: 17px;
  color: #829087;
  font-size: 11px;
  line-height: 1.5;
}
.login-note svg {
  flex: 0 0 auto;
  color: #5c9b74;
}
@keyframes login-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 899px) and (min-width: 601px) {
  .login-page {
    grid-template-columns: minmax(0, 0.82fr) minmax(340px, 1.18fr);
  }
  .story-inner {
    padding: 30px 28px;
  }
  .brand-badge {
    display: none;
  }
  .story-main {
    padding: 36px 0 42px;
  }
  .story-copy h1 {
    font-size: clamp(36px, 5vw, 52px);
  }
  .story-description {
    font-size: 13px;
  }
  .query-preview {
    margin-top: 32px;
  }
  .preview-schema {
    flex-direction: column;
    gap: 8px;
  }
  .story-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .login-panel {
    padding-inline: 40px;
  }
}
@media (max-width: 600px) {
  .login-page {
    display: block;
  }
  .login-story {
    min-height: 280px;
  }
  .story-inner {
    min-height: 280px;
    padding: 27px 24px 23px;
  }
  .brand-mark {
    width: 36px;
    height: 36px;
  }
  .brand-name {
    font-size: 14px;
  }
  .story-main {
    padding: 31px 0 22px;
  }
  .story-kicker {
    margin-bottom: 14px;
    font-size: 10px;
  }
  .story-copy h1 {
    font-size: 38px;
  }
  .story-description {
    max-width: 290px;
    margin-top: 15px;
    font-size: 12px;
    line-height: 1.55;
  }
  .query-preview {
    display: none;
  }
  .story-footer {
    padding-top: 13px;
    font-size: 10px;
  }
  .story-footer span:last-child {
    display: none;
  }
  .login-panel {
    display: block;
    padding: 47px 24px 54px;
  }
  .login-heading {
    margin-bottom: 30px;
  }
  .login-heading h2 {
    font-size: 30px;
  }
  .login-form {
    gap: 19px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .field-control,
  .login-submit {
    transition: none;
  }
  .loading-icon {
    animation: none;
  }
}
</style>
