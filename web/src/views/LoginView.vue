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
    : "/agent";
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
      <div class="story-grid" aria-hidden="true" />
      <div class="story-orbit story-orbit--outer" aria-hidden="true" />
      <div class="story-orbit story-orbit--inner" aria-hidden="true" />
      <div class="story-signal" aria-hidden="true">
        <span class="story-signal__dot" />
        <span>WORKSPACE READY</span>
      </div>

      <div class="story-inner">
        <header class="brand-lockup login-reveal login-reveal--brand">
          <span class="brand-mark"><Database :size="19" :stroke-width="2.1" /></span>
          <span class="brand-name">Chain-NL2SQL</span>
          <span class="brand-badge">WORKSPACE</span>
        </header>

        <div class="story-main">
          <div class="story-copy login-reveal login-reveal--copy">
            <p class="story-kicker"><Sparkles :size="14" /> DATA, IN PLAIN LANGUAGE</p>
            <h1 class="story-title">让数据<br /><em>回答问题。</em></h1>
            <p class="story-description">从自然语言到可解释的 SQL，让每一次探索都更快、更清晰。</p>
          </div>

          <div class="signal-row login-reveal login-reveal--signals" aria-label="工作台能力">
            <span><MessageSquareText :size="15" />自然语言</span>
            <i aria-hidden="true" />
            <span><BarChart3 :size="15" />可解释结果</span>
            <i aria-hidden="true" />
            <span><ShieldCheck :size="15" />安全可控</span>
          </div>

          <div class="query-preview login-reveal login-reveal--query" aria-label="数据查询预览">
            <div class="preview-header">
              <span class="preview-label">LIVE QUERY</span>
              <span class="preview-status"><i aria-hidden="true" /> READY</span>
            </div>
            <div class="preview-prompt">
              <span class="prompt-symbol" aria-hidden="true">›</span>
              <span>本月各业务线的收入趋势</span>
              <ArrowUpRight :size="16" aria-hidden="true" />
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
          <span><i class="footer-dot" aria-hidden="true" />系统在线</span>
          <span>只读查询 · 本地演示环境</span>
        </footer>
      </div>
    </section>

    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-panel__inner login-reveal login-reveal--form">
        <div class="login-heading">
          <p class="login-eyebrow">SECURE WORKSPACE <span>01</span></p>
          <h2 id="login-title">欢迎回来</h2>
          <p>登录后继续使用数据问答与知识库。</p>
        </div>

        <p class="status-track"><i aria-hidden="true" />安全会话已就绪</p>

        <form class="login-form" :aria-busy="submitting" @submit.prevent="submit">
          <div class="form-field">
            <label class="field-label" for="username">用户名</label>
            <div class="field-control">
              <UserRound :size="17" aria-hidden="true" />
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
              <LockKeyhole :size="17" aria-hidden="true" />
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
            <span>{{ submitting ? "正在登录" : "登录工作区" }}</span>
            <LoaderCircle v-if="submitting" class="loading-icon" :size="17" aria-hidden="true" />
            <ArrowRight v-else :size="17" aria-hidden="true" />
          </button>
        </form>

        <div class="login-note">
          <ShieldCheck :size="16" aria-hidden="true" />
          <span>本地演示环境 · 会话状态仅保存在当前浏览器</span>
          <Check :size="15" class="note-check" aria-hidden="true" />
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
  grid-template-columns: minmax(0, 1.06fr) minmax(440px, 0.94fr);
  color: #16251d;
  background: #f7f8f5;
}

.login-story {
  position: relative;
  overflow: hidden;
  color: #f4f8f4;
  background: #10251c;
}

.story-grid {
  position: absolute;
  inset: 0;
  opacity: 0.28;
  background-image:
    linear-gradient(rgba(194, 239, 210, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(194, 239, 210, 0.07) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(135deg, #000 0%, transparent 72%);
}

.story-orbit {
  position: absolute;
  right: -215px;
  border: 1px solid rgba(183, 236, 201, 0.16);
  border-radius: 50%;
  transform: rotate(-24deg);
  transform-origin: center;
  animation: orbit-drift 12s ease-in-out infinite alternate;
}

.story-orbit--outer {
  width: 680px;
  height: 340px;
  top: 15%;
}

.story-orbit--inner {
  width: 470px;
  height: 230px;
  right: -135px;
  top: 24%;
  border-color: rgba(183, 236, 201, 0.1);
  animation-delay: -6s;
}

.story-signal {
  position: absolute;
  right: 42px;
  top: calc(15% + 314px);
  display: flex;
  width: 224px;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(183, 236, 201, 0.19);
  padding-top: 9px;
  color: #94b6a1;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.story-signal__dot,
.preview-status i,
.footer-dot,
.status-track i {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #83d79c;
  box-shadow: 0 0 0 4px rgba(131, 215, 156, 0.11);
  animation: status-pulse 2.8s ease-in-out infinite;
}

.story-inner {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: clamp(32px, 5vw, 72px) clamp(30px, 7vw, 104px);
}

.brand-lockup,
.signal-row,
.story-footer,
.preview-header,
.preview-prompt,
.login-note,
.status-track,
.field-control,
.login-submit {
  display: flex;
  align-items: center;
}

.brand-lockup {
  gap: 11px;
}
.brand-mark {
  display: grid;
  width: 39px;
  height: 39px;
  place-items: center;
  border: 1px solid rgba(215, 245, 224, 0.27);
  border-radius: 8px;
  color: #14271e;
  background: #bce8cd;
}
.brand-name {
  font-size: 15px;
  font-weight: 760;
}
.brand-badge {
  border: 1px solid rgba(203, 231, 215, 0.24);
  border-radius: 4px;
  padding: 4px 7px;
  color: #a7c4b1;
  font-size: 9px;
  font-weight: 800;
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
.story-title {
  margin: 0;
  color: #f4faf5;
  font-size: clamp(44px, 5.2vw, 74px);
  font-weight: 720;
  line-height: 1.04;
}
.story-title em {
  color: #bde9ce;
  font-style: normal;
}
.story-description {
  max-width: 360px;
  margin: 24px 0 0;
  color: #9cb5a5;
  font-size: 15px;
  line-height: 1.75;
}

.signal-row {
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 35px;
  color: #a3bfae;
  font-size: 11px;
}
.signal-row span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.signal-row svg {
  color: #8dca9f;
}
.signal-row i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #567963;
}

.query-preview {
  position: relative;
  overflow: hidden;
  width: min(100%, 560px);
  margin-top: 38px;
  border: 1px solid rgba(196, 229, 208, 0.18);
  border-radius: 8px;
  background: rgba(31, 55, 43, 0.9);
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.13);
}
.query-preview::after {
  position: absolute;
  z-index: 2;
  top: 44%;
  left: -45%;
  width: 42%;
  height: 1px;
  content: "";
  background: linear-gradient(90deg, transparent, #b7efca, transparent);
  box-shadow: 0 0 10px rgba(183, 239, 202, 0.8);
  animation: query-scan 7s ease-in-out infinite 1.8s;
}
.preview-header {
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
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #a5d9b2;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
}
.preview-prompt {
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
  flex-wrap: wrap;
  gap: 12px;
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

.login-panel {
  position: relative;
  display: grid;
  overflow: hidden;
  place-items: center;
  padding: 48px clamp(32px, 7vw, 108px);
  background: #f7f8f5;
}
.login-panel::before {
  position: absolute;
  inset: 0;
  content: "";
  opacity: 0.48;
  background-image:
    linear-gradient(rgba(71, 124, 89, 0.042) 1px, transparent 1px),
    linear-gradient(90deg, rgba(71, 124, 89, 0.042) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(150deg, transparent 4%, #000 55%, transparent 100%);
}
.login-panel__inner {
  position: relative;
  z-index: 1;
  width: min(100%, 416px);
}
.login-heading {
  margin-bottom: 30px;
}
.login-eyebrow {
  display: flex;
  gap: 10px;
  margin: 0 0 14px;
  color: #4b9268;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.15em;
}
.login-eyebrow span {
  color: #abb8ae;
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
.status-track {
  gap: 8px;
  margin: 0 0 28px;
  color: #537260;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
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
  color: #3d4d44;
  font-size: 12px;
  font-weight: 750;
}
.field-control {
  height: 70px;
  gap: 13px;
  border: 1px solid #d8ded9;
  border-radius: 9px;
  padding: 0 17px;
  color: #82958a;
  background: rgba(255, 255, 255, 0.84);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}
.field-control:focus-within {
  border-color: #7cbd91;
  box-shadow: 0 0 0 4px rgba(104, 181, 130, 0.12);
}
.field-control input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: #1f3027;
  background: transparent;
  font: inherit;
  font-size: 15px;
}
.field-control input::placeholder {
  color: #a7b1aa;
}
.field-control:has(input:disabled) {
  opacity: 0.66;
}
.password-toggle {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  border-radius: 6px;
  padding: 0;
  color: #87978e;
  background: transparent;
  cursor: pointer;
}
.password-toggle:hover:not(:disabled),
.password-toggle:focus-visible {
  color: #3c7651;
  background: #edf5ef;
  outline: 0;
}
.password-toggle:disabled {
  cursor: not-allowed;
}
.login-error {
  margin: -8px 0 -4px;
  color: #bc4f4f;
  font-size: 12px;
  line-height: 1.5;
}
.login-submit {
  height: 70px;
  justify-content: center;
  gap: 10px;
  border: 0;
  border-radius: 9px;
  color: #143322;
  background: #b7e7cb;
  box-shadow: 0 14px 30px rgba(77, 147, 102, 0.16);
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background 160ms ease,
    box-shadow 160ms ease;
}
.login-submit:hover:not(:disabled) {
  background: #a9dfbf;
  box-shadow: 0 18px 32px rgba(77, 147, 102, 0.22);
  transform: translateY(-1px);
}
.login-submit:focus-visible {
  outline: 3px solid rgba(52, 143, 82, 0.3);
  outline-offset: 3px;
}
.login-submit:disabled {
  cursor: wait;
  opacity: 0.72;
}
.loading-icon {
  animation: loading-spin 0.8s linear infinite;
}
.login-note {
  gap: 10px;
  margin-top: 38px;
  border-top: 1px solid #e0e6e1;
  padding-top: 21px;
  color: #8a968e;
  font-size: 11px;
  line-height: 1.45;
}
.login-note > svg:first-child {
  flex: 0 0 auto;
  color: #56a773;
}
.note-check {
  margin-left: auto;
  flex: 0 0 auto;
  color: #5ba979;
}

.login-reveal {
  animation: login-reveal 620ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
.login-reveal--brand {
  animation-delay: 100ms;
}
.login-reveal--copy {
  animation-delay: 240ms;
}
.login-reveal--signals {
  animation-delay: 390ms;
}
.login-reveal--query {
  animation-delay: 520ms;
}
.login-reveal--footer {
  animation-delay: 660ms;
}
.login-reveal--form {
  animation-delay: 280ms;
}

@keyframes login-reveal {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes orbit-drift {
  from {
    transform: rotate(-24deg) scale(0.98);
  }
  to {
    transform: rotate(-18deg) scale(1.04);
  }
}
@keyframes query-scan {
  0%,
  20% {
    left: -45%;
    opacity: 0;
  }
  32% {
    opacity: 0.9;
  }
  62%,
  100% {
    left: 110%;
    opacity: 0;
  }
}
@keyframes status-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 4px rgba(131, 215, 156, 0.1);
  }
  50% {
    box-shadow: 0 0 0 7px rgba(131, 215, 156, 0.02);
  }
}
@keyframes loading-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 899px) and (min-width: 701px) {
  .login-page {
    grid-template-columns: minmax(0, 1fr) minmax(360px, 0.9fr);
  }
  .story-inner {
    padding-inline: clamp(28px, 5vw, 52px);
  }
  .story-title {
    font-size: clamp(42px, 5vw, 58px);
  }
  .story-description {
    font-size: 13px;
  }
  .preview-schema {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .login-panel {
    padding-inline: 40px;
  }
  .story-signal {
    right: 25px;
    width: 180px;
  }
}

@media (max-width: 700px) {
  .login-page {
    display: block;
  }
  .login-story {
    min-height: 310px;
  }
  .story-inner {
    min-height: 310px;
    padding: 25px 24px 21px;
  }
  .brand-mark {
    width: 36px;
    height: 36px;
  }
  .brand-name {
    font-size: 14px;
  }
  .brand-badge,
  .signal-row,
  .query-preview,
  .story-signal {
    display: none;
  }
  .story-main {
    padding: 32px 0 21px;
  }
  .story-kicker {
    margin-bottom: 14px;
    font-size: 9px;
  }
  .story-title {
    font-size: 38px;
  }
  .story-description {
    max-width: 290px;
    margin-top: 15px;
    font-size: 12px;
    line-height: 1.55;
  }
  .story-footer {
    padding-top: 12px;
    font-size: 9px;
  }
  .story-footer span:last-child {
    display: none;
  }
  .story-orbit--outer {
    width: 360px;
    height: 190px;
    right: -160px;
    top: 10%;
  }
  .story-orbit--inner {
    width: 260px;
    height: 130px;
    right: -100px;
    top: 21%;
  }
  .login-panel {
    display: block;
    padding: 47px 24px 54px;
  }
  .login-heading {
    margin-bottom: 27px;
  }
  .login-heading h2 {
    font-size: 30px;
  }
  .field-control,
  .login-submit {
    height: 62px;
  }
  .login-note {
    margin-top: 30px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .login-reveal {
    opacity: 1;
    transform: none;
  }
}
</style>
