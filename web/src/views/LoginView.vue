<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowRight, Database, Eye, EyeOff, LockKeyhole, UserRound } from "lucide-vue-next";

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
  return typeof redirect === "string" && redirect.startsWith("/") && !redirect.startsWith("//") && redirect !== "/login"
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
    <section class="login-shell" aria-labelledby="login-title">
      <div class="login-brand"><span class="login-brand__mark"><Database :size="21" /></span><span>Chain-NL2SQL</span></div>
      <div class="login-card">
        <div class="login-card__intro"><span class="login-card__eyebrow">数据语义工作台</span><h1 id="login-title">欢迎回来</h1><p>登录后继续使用数据问答与知识库。</p></div>
        <form class="login-form" @submit.prevent="submit">
          <label class="field-label" for="username">用户名</label>
          <div class="field-control"><UserRound :size="17" aria-hidden="true" /><input id="username" v-model="username" autocomplete="username" placeholder="请输入用户名" type="text" :disabled="submitting" /></div>
          <label class="field-label" for="password">密码</label>
          <div class="field-control"><LockKeyhole :size="17" aria-hidden="true" /><input id="password" v-model="password" autocomplete="current-password" placeholder="请输入密码" :type="showPassword ? 'text' : 'password'" :disabled="submitting" /><button class="password-toggle" type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" :title="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword"><EyeOff v-if="showPassword" :size="17" /><Eye v-else :size="17" /></button></div>
          <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>
          <button class="login-submit" type="submit" :disabled="submitting"><span>{{ submitting ? "正在登录" : "登录工作区" }}</span><ArrowRight :size="17" /></button>
        </form>
      </div>
      <p class="login-footer">本地演示环境 · 受控访问</p>
    </section>
  </main>
</template>

<style scoped>
.login-page { display: grid; min-height: 100vh; place-items: center; padding: 28px 18px; color: #1c2922; background: #f5f8f5; }
.login-shell { width: min(100%, 420px); }
.login-brand { display: flex; align-items: center; justify-content: center; gap: 10px; color: #1c2922; font-size: 16px; font-weight: 760; }
.login-brand__mark { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 10px; color: #e9f5ee; background: #1c2922; }
.login-card { margin-top: 24px; border: 1px solid #e1e8e2; border-radius: 10px; padding: 30px; background: #fff; box-shadow: 0 16px 40px rgba(28, 41, 34, .08); }
.login-card__intro { text-align: center; }.login-card__eyebrow { color: #3b8c66; font-size: 11px; font-weight: 700; }.login-card h1 { margin: 9px 0 7px; font-size: 28px; letter-spacing: 0; }.login-card p { margin: 0; color: #718078; font-size: 13px; line-height: 1.5; }
.login-form { margin-top: 27px; }.field-label { display: block; margin: 0 0 7px; color: #3b4740; font-size: 12px; font-weight: 650; }.field-label + .field-control { margin-bottom: 18px; }
.field-control { display: flex; height: 42px; align-items: center; gap: 9px; border: 1px solid #dbe4dd; border-radius: 7px; padding: 0 11px; color: #8b9790; background: #fbfdfb; }.field-control:focus-within { border-color: #6eb796; box-shadow: 0 0 0 3px rgba(67, 138, 109, .12); }.field-control input { min-width: 0; flex: 1; border: 0; outline: 0; color: #1c2922; background: transparent; font-size: 13px; }.field-control input::placeholder { color: #a4aea7; }
.password-toggle { display: grid; width: 26px; height: 26px; place-items: center; border: 0; border-radius: 5px; color: #849089; background: transparent; cursor: pointer; }.password-toggle:hover { color: #1c2922; background: #eef4ef; }
.login-error { margin: -3px 0 14px !important; color: #b4473d !important; font-size: 12px !important; }.login-submit { display: flex; width: 100%; height: 42px; align-items: center; justify-content: center; gap: 8px; border: 0; border-radius: 7px; color: #102118; background: #bfe6d1; font-size: 13px; font-weight: 700; cursor: pointer; }.login-submit:hover:not(:disabled) { background: #aee0c4; }.login-submit:disabled { cursor: wait; opacity: .65; }.login-footer { margin: 18px 0 0 !important; color: #87948c !important; font-size: 11px !important; text-align: center; }
@media (max-width: 480px) { .login-card { padding: 24px 20px; } }
</style>
