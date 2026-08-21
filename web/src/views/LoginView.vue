<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Check,
  Database,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Table2,
  UserRound,
} from "lucide-vue-next";
import { isAuthenticated, login } from "@/auth/auth";

const router = useRouter();
const route = useRoute();
const username = ref("admin");
const password = ref("123456");
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
      <div class="startup-sequence" aria-hidden="true">
        <div class="startup-plane" />
        <div class="startup-radar"><i /><i /><i /></div>
        <div class="startup-caption"><span>INITIALIZING WORKSPACE</span><b>READY</b></div>
      </div>
      <div class="story-grid" aria-hidden="true" />
      <div class="story-orbit story-orbit--one" aria-hidden="true" />
      <div class="story-orbit story-orbit--two" aria-hidden="true" />
      <div class="story-inner">
        <header class="brand-lockup login-reveal login-reveal--brand">
          <span class="brand-mark"><Database :size="19" :stroke-width="2.1" /></span
          ><span class="brand-name">Chain-NL2SQL</span><span class="brand-badge">WORKSPACE</span>
        </header>
        <div class="story-main">
          <div class="story-copy login-reveal login-reveal--copy">
            <p class="story-kicker"><Sparkles :size="14" /> DATA, IN PLAIN LANGUAGE</p>
            <h1>让数据<br /><em>回答问题。</em></h1>
            <p class="story-description">从自然语言到可解释的 SQL，让每一次探索都更快、更清晰。</p>
          </div>
          <div class="signal-row login-reveal login-reveal--signals" aria-label="工作台能力">
            <span><MessageSquareText :size="15" />自然语言</span><i /><span
              ><BarChart3 :size="15" />可解释结果</span
            ><i /><span><ShieldCheck :size="15" />安全可控</span>
          </div>
          <div class="query-preview login-reveal login-reveal--query" aria-label="数据查询预览">
            <div class="preview-header">
              <span class="preview-label">LIVE QUERY</span
              ><span class="preview-status"><i /> READY</span>
            </div>
            <div class="preview-prompt">
              <span class="prompt-symbol">›</span><span>本月各业务线的收入趋势</span
              ><ArrowUpRight :size="16" />
            </div>
            <div class="preview-schema">
              <div class="schema-item">
                <Table2 :size="14" /><span>revenue</span><small>table</small>
              </div>
              <div class="schema-item">
                <Table2 :size="14" /><span>business_line</span><small>field</small>
              </div>
              <div class="schema-item">
                <Table2 :size="14" /><span>growth_rate</span><small>metric</small>
              </div>
            </div>
          </div>
        </div>
        <footer class="story-footer login-reveal login-reveal--footer">
          <span><span class="footer-dot" />系统在线</span><span>只读查询 · 本地演示环境</span>
        </footer>
      </div>
    </section>
    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-panel__inner">
        <div class="login-heading">
          <p class="login-eyebrow">SECURE WORKSPACE <span>01</span></p>
          <h2 id="login-title">欢迎回来</h2>
          <p>登录后继续使用数据问答与知识库。</p>
        </div>
        <form class="login-form" :aria-busy="submitting" @submit.prevent="submit">
          <div class="form-field">
            <label class="field-label" for="username">用户名</label>
            <div class="field-control">
              <UserRound :size="17" aria-hidden="true" /><input
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
              <LockKeyhole :size="17" aria-hidden="true" /><input
                id="password"
                v-model="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                :type="showPassword ? 'text' : 'password'"
                :disabled="submitting"
              /><button
                class="password-toggle"
                type="button"
                :disabled="submitting"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :title="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" :size="17" /><Eye v-else :size="17" />
              </button>
            </div>
          </div>
          <p v-if="errorMessage" class="login-error" role="alert" aria-live="polite">
            {{ errorMessage }}
          </p>
          <button class="login-submit" type="submit" :disabled="submitting">
            <span>{{ submitting ? "正在登录" : "登录工作区" }}</span
            ><LoaderCircle
              v-if="submitting"
              class="loading-icon"
              :size="17"
              aria-hidden="true"
            /><ArrowRight v-else :size="17" aria-hidden="true" />
          </button>
        </form>
        <div class="login-note">
          <ShieldCheck :size="16" /><span>本地演示环境 · 会话状态仅保存在当前浏览器</span
          ><Check :size="15" class="note-check" />
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  position: relative;
  display: grid;
  min-height: 100vh;
  min-height: 100dvh;
  grid-template-columns: minmax(0, 1.06fr) minmax(440px, 0.94fr);
  background: #f7f8f6;
  color: #18251f;
}
.startup-sequence {
  position: absolute;
  z-index: 1;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}
.startup-plane {
  position: absolute;
  width: 480px;
  height: 480px;
  right: -210px;
  top: 7%;
  border: 1px solid rgba(188, 239, 205, 0.2);
  border-radius: 50%;
  background: conic-gradient(from 90deg, transparent 0 61%, rgba(178, 237, 197, 0.18) 69%, transparent 78%);
  box-shadow: 0 0 70px rgba(99, 191, 130, 0.08);
  opacity: 0;
  transform: scale(0.76);
  animation: startup-plane 1800ms cubic-bezier(0.16, 0.8, 0.2, 1) both;
}
.startup-radar {
  position: absolute;
  width: 300px;
  height: 300px;
  right: -120px;
  top: 16%;
  border: 1px solid rgba(187, 235, 202, 0.13);
  border-radius: 50%;
  opacity: 0;
  transform: scale(0.76);
  animation: startup-radar-in 900ms cubic-bezier(0.16, 1, 0.3, 1) 190ms both;
}
.startup-radar::before,
.startup-radar::after,
.startup-radar i {
  position: absolute;
  border: 1px solid rgba(187, 235, 202, 0.11);
  border-radius: 50%;
  content: "";
}
.startup-radar::before { inset: 22%; }
.startup-radar::after { inset: 42%; }
.startup-radar i:first-child { inset: -1px; border-color: rgba(171, 234, 191, 0.24); animation: radar-spin 5s linear infinite 1200ms; }
.startup-radar i:nth-child(2) { width: 6px; height: 6px; left: 26%; top: 35%; border: 0; background: #9be1b0; box-shadow: 0 0 0 5px rgba(155, 225, 176, 0.12), 0 0 14px rgba(155, 225, 176, 0.7); animation: radar-node 1.8s ease-out 730ms both; }
.startup-radar i:last-child { width: 2px; height: 48%; left: 50%; top: 2%; border: 0; border-radius: 0; transform-origin: bottom; background: linear-gradient(transparent, rgba(175, 242, 197, 0.75)); animation: radar-sweep 1.8s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
.startup-caption {
  position: absolute;
  display: flex;
  width: 220px;
  right: 48px;
  top: calc(16% + 315px);
  justify-content: space-between;
  border-top: 1px solid rgba(183, 236, 199, 0.2);
  padding-top: 9px;
  color: #93b8a0;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.12em;
  opacity: 0;
  animation: startup-caption-in 360ms ease-out 860ms both;
}
.startup-caption b { color: #a9e5ba; font-weight: 800; }
}
.login-story {
  position: relative;
  overflow: hidden;
  background: #10221b;
  color: #f3f7f3;
}
.story-inner {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: clamp(32px, 5vw, 72px) clamp(30px, 7vw, 104px);
}
.story-grid {
  position: absolute;
  inset: 0;
  opacity: 0.28;
  background-image:
    linear-gradient(rgba(182, 229, 198, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(182, 229, 198, 0.08) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(125deg, #000 0%, transparent 68%);
  animation: story-grid-drift 15s linear infinite alternate;
}
.story-orbit {
  position: absolute;
  border: 1px solid rgba(172, 229, 193, 0.14);
  border-radius: 50%;
  transform: rotate(-23deg);
  animation: story-orbit-pulse 8s ease-in-out infinite alternate;
}
.story-orbit--one {
  width: 640px;
  height: 310px;
  right: -250px;
  top: 15%;
}
.story-orbit--two {
  width: 540px;
  height: 250px;
  right: -170px;
  top: 23%;
  border-color: rgba(172, 229, 193, 0.08);
  animation-delay: -3s;
}
.brand-lockup {
  display: flex;
  align-items: center;
  gap: 11px;
}
.brand-mark {
  display: grid;
  width: 39px;
  height: 39px;
  place-items: center;
  border: 1px solid rgba(207, 241, 218, 0.28);
  border-radius: 10px;
  color: #12251c;
  background: #bce8cd;
  box-shadow: 0 5px 20px rgba(130, 215, 160, 0.16);
}
.brand-name {
  font-size: 15px;
  font-weight: 760;
}
.brand-badge {
  margin-left: 3px;
  border: 1px solid rgba(203, 231, 215, 0.25);
  border-radius: 4px;
  padding: 4px 7px;
  color: #a7c4b1;
  font-size: 9px;
  font-weight: 760;
  letter-spacing: 0.08em;
}
.story-main {
  display: flex;
  margin: auto 0;
  flex-direction: column;
  padding: 58px 0 60px;
}
.story-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 19px;
  color: #a9d5b8;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.13em;
}
.story-copy h1 {
  margin: 0;
  color: #f5faf6;
  font-size: clamp(44px, 5.2vw, 74px);
  font-weight: 700;
  line-height: 1.03;
}
.story-copy h1 em {
  color: #bde9ce;
  font-style: normal;
}
.story-description {
  max-width: 360px;
  margin: 24px 0 0;
  color: #a1b7a9;
  font-size: 15px;
  line-height: 1.75;
}
.signal-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 35px;
  color: #9eb9a7;
  font-size: 11px;
}
.signal-row span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.signal-row svg {
  color: #8ac49b;
}
.signal-row i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #527461;
}
.query-preview {
  position: relative;
  overflow: hidden;
  width: min(100%, 560px);
  margin-top: 38px;
  border: 1px solid rgba(196, 229, 208, 0.18);
  border-radius: 9px;
  background: rgba(31, 53, 42, 0.88);
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.13);
}
.query-preview::after {
  position: absolute;
  z-index: 2;
  width: 42%;
  height: 1px;
  left: -45%;
  top: 45%;
  content: "";
  background: linear-gradient(90deg, transparent, #b7efca, transparent);
  box-shadow: 0 0 11px rgba(183, 239, 202, 0.85);
  opacity: 0;
  animation: query-scan 760ms ease-out 1270ms both;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(196, 229, 208, 0.12);
  padding: 13px 16px;
}
.preview-label {
  color: #87b899;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.14em;
}
.preview-status {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #a5d9b2;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.preview-status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #87dda0;
  box-shadow: 0 0 0 3px rgba(135, 221, 160, 0.1);
  animation: status-pulse 2.8s ease-in-out infinite 1850ms;
}
.preview-prompt {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 20px 16px 17px;
  color: #eff8f1;
  font-size: 14px;
}
.prompt-symbol {
  color: #9de2b0;
  font-size: 20px;
  line-height: 0;
}
.preview-prompt svg {
  margin-left: auto;
  color: #84b495;
}
.preview-schema {
  display: flex;
  gap: 9px;
  border-top: 1px solid rgba(196, 229, 208, 0.1);
  padding: 13px 16px 15px;
}
.schema-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 6px;
  color: #c9e2d0;
  font-size: 10px;
}
.schema-item svg {
  flex: 0 0 auto;
  color: #7eba8e;
}
.schema-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.schema-item small {
  color: #789381;
  font-size: 9px;
}
.story-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-top: 1px solid rgba(196, 229, 208, 0.13);
  padding-top: 16px;
  color: #789184;
  font-size: 10px;
}
.story-footer span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.story-footer span:first-child {
  color: #b6d7bf;
}
.login-reveal {
  will-change: opacity, transform;
  animation: login-reveal 680ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
.login-reveal--brand {
  animation-delay: 180ms;
}
.login-reveal--copy {
  animation-delay: 430ms;
}
.login-reveal--signals {
  animation-delay: 720ms;
}
.login-reveal--query {
  animation-delay: 980ms;
}
.login-reveal--footer {
  animation-delay: 1190ms;
}
.footer-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #8bdda0;
  box-shadow: 0 0 0 3px rgba(139, 221, 160, 0.12);
}
.login-panel {
  position: relative;
  display: grid;
  place-items: center;
  padding: 48px clamp(32px, 7vw, 108px);
  background: #f7f8f6;
}
.login-panel::after {
  position: absolute;
  z-index: 0;
  width: 1px;
  height: 0;
  left: 8%;
  top: 13%;
  content: "";
  background: #92dca8;
  box-shadow: 0 0 16px rgba(109, 198, 137, 0.72);
  opacity: 0;
  animation: panel-scan 1180ms cubic-bezier(0.2, 0.76, 0.25, 1) 270ms both;
}
.login-panel__inner {
  position: relative;
  z-index: 1;
  width: min(100%, 416px);
}
.login-heading {
  margin-bottom: 37px;
}
.login-eyebrow {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 14px;
  color: #4b9268;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.15em;
}
.login-eyebrow span {
  color: #acb8ae;
  font-size: 9px;
  letter-spacing: 0.04em;
}
.login-heading h2 {
  margin: 0;
  color: #17241d;
  font-size: clamp(31px, 3vw, 41px);
  font-weight: 720;
  line-height: 1.12;
}
.login-heading > p:last-child {
  margin: 12px 0 0;
  color: #75827a;
  font-size: 14px;
  line-height: 1.65;
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 21px;
}
.form-field {
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.field-label {
  color: #3d4d43;
  font-size: 12px;
  font-weight: 700;
}
.field-control {
  display: flex;
  height: 53px;
  align-items: center;
  gap: 11px;
  border: 1px solid #d8e0d9;
  border-radius: 8px;
  padding: 0 14px;
  color: #809087;
  background: #fff;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}
.field-control:focus-within {
  border-color: #5b9b75;
  box-shadow: 0 0 0 4px rgba(91, 155, 117, 0.12);
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
  color: #a5b0a8;
}
.password-toggle {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  border-radius: 6px;
  color: #89978e;
  background: transparent;
  cursor: pointer;
}
.password-toggle:hover {
  color: #182720;
  background: #edf3ee;
}
.password-toggle:disabled {
  cursor: wait;
  opacity: 0.5;
}
.login-error {
  margin: -4px 0 -2px;
  color: #b64c43;
  font-size: 12px;
  line-height: 1.5;
}
.login-submit {
  display: flex;
  width: 100%;
  height: 53px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  margin-top: 2px;
  border: 0;
  border-radius: 8px;
  color: #13221a;
  background: #b9e4cb;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(96, 155, 117, 0.12);
  transition:
    background-color 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease;
}
.login-submit:hover:not(:disabled) {
  background: #a8dbbd;
  box-shadow: 0 10px 23px rgba(96, 155, 117, 0.18);
  transform: translateY(-1px);
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
  align-items: center;
  gap: 9px;
  margin-top: 29px;
  border-top: 1px solid #e1e7e2;
  padding-top: 16px;
  color: #87938b;
  font-size: 10px;
  line-height: 1.5;
}
.login-note > svg:first-child {
  flex: 0 0 auto;
  color: #5c9b74;
}
.note-check {
  margin-left: auto;
  flex: 0 0 auto;
  color: #87b296;
}
@keyframes login-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes login-reveal {
  from {
    opacity: 0;
    transform: translate3d(0, 28px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}
@keyframes startup-plane {
  0% {
    opacity: 0;
    transform: scale(0.76) rotate(-18deg);
  }
  12% {
    opacity: 0.82;
  }
  72% {
    opacity: 0.6;
  }
  100% {
    opacity: 0.16;
    transform: scale(1) rotate(18deg);
  }
}
@keyframes startup-radar-in {
  from { opacity: 0; transform: scale(0.76); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes startup-caption-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes radar-spin {
  to { transform: rotate(360deg); }
}
@keyframes radar-node {
  0%, 38% { opacity: 0; transform: scale(0.3); }
  58% { opacity: 1; transform: scale(1); }
  100% { opacity: 1; transform: scale(1); }
}
@keyframes radar-sweep {
  0% { opacity: 0; transform: rotate(-138deg); }
  16% { opacity: 0.9; }
  78% { opacity: 0.72; }
  100% { opacity: 0; transform: rotate(138deg); }
}
@keyframes panel-scan {
  0% {
    height: 0;
    opacity: 0;
    transform: translateY(0);
  }
  14% {
    opacity: 0.95;
  }
  76% {
    opacity: 0.48;
  }
  100% {
    height: 72%;
    opacity: 0;
    transform: translateY(18%);
  }
}
@keyframes query-scan {
  0% {
    opacity: 0;
    transform: translateX(0);
  }
  14% {
    opacity: 1;
  }
  82% {
    opacity: 0.85;
  }
  100% {
    opacity: 0;
    transform: translateX(350%);
  }
}
@keyframes status-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 3px rgba(135, 221, 160, 0.1);
  }
  50% {
    box-shadow:
      0 0 0 6px rgba(135, 221, 160, 0.04),
      0 0 9px rgba(135, 221, 160, 0.65);
  }
}
@keyframes story-grid-drift {
  from {
    background-position:
      0 0,
      0 0;
  }
  to {
    background-position:
      72px 36px,
      72px 36px;
  }
}
@keyframes story-orbit-pulse {
  from {
    opacity: 0.5;
    transform: rotate(-23deg) scale(0.98);
  }
  to {
    opacity: 1;
    transform: rotate(-23deg) scale(1.04);
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
    padding: 38px 0 42px;
  }
  .story-copy h1 {
    font-size: clamp(36px, 5vw, 52px);
  }
  .story-description {
    font-size: 13px;
  }
  .signal-row {
    flex-wrap: wrap;
    gap: 8px;
  }
  .query-preview {
    margin-top: 30px;
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
  .startup-radar {
    width: 230px;
    height: 230px;
    right: -105px;
  }
  .startup-caption {
    width: 176px;
    right: 26px;
    top: calc(16% + 242px);
  }
}
@media (max-width: 600px) {
  .login-page {
    display: block;
  }
  .login-story {
    min-height: 300px;
  }
  .story-inner {
    min-height: 300px;
    padding: 25px 24px 21px;
  }
  .brand-mark {
    width: 36px;
    height: 36px;
  }
  .brand-name {
    font-size: 14px;
  }
  .brand-badge {
    display: none;
  }
  .story-main {
    padding: 32px 0 21px;
  }
  .story-kicker {
    margin-bottom: 14px;
    font-size: 9px;
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
  .signal-row,
  .query-preview {
    display: none;
  }
  .story-footer {
    padding-top: 12px;
    font-size: 9px;
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
  .startup-plane {
    width: 260px;
    height: 260px;
    right: -130px;
    top: 2px;
  }
  .startup-radar {
    width: 170px;
    height: 170px;
    right: -84px;
    top: 18px;
  }
  .startup-caption {
    width: 146px;
    right: 12px;
    top: 190px;
    font-size: 7px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .field-control,
  .login-submit {
    transition: none;
  }
  .loading-icon,
  .startup-plane,
  .startup-radar,
  .startup-radar i,
  .startup-caption,
  .login-reveal,
  .story-grid,
  .story-orbit,
  .preview-status i,
  .query-preview::after,
  .login-panel::after {
    animation: none;
  }
  .login-reveal {
    opacity: 1;
    transform: none;
  }
  .startup-sequence {
    display: none;
  }
}
</style>
