<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import {
  ChevronRight,
  CircleHelp,
  CircleUserRound,
  LogOut,
  Palette,
  Settings,
  Sparkles,
} from "lucide-vue-next";

const props = defineProps<{
  open: boolean;
  username: string;
}>();

const emit = defineEmits<{
  "update:open": [open: boolean];
  logout: [];
}>();

function close() {
  emit("update:open", false);
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === "Escape" && props.open) close();
}

function requestLogout() {
  close();
  emit("logout");
}

onMounted(() => window.addEventListener("keydown", handleEscape));
onBeforeUnmount(() => window.removeEventListener("keydown", handleEscape));
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="account-menu-layer" @mousedown.self="close">
      <section class="account-menu" aria-label="账户菜单" @mousedown.stop>
        <button class="account-menu__profile" type="button">
          <img class="account-menu__avatar" src="/user-avatar.jpg" alt="" />
          <span><strong>{{ username }}</strong><small>Plus</small></span>
          <ChevronRight :size="22" :stroke-width="1.8" aria-hidden="true" />
        </button>

        <div class="account-menu__divider" aria-hidden="true" />

        <div class="account-menu__actions">
          <button type="button"><Sparkles :size="21" aria-hidden="true" /><span class="account-menu__label">升级套餐</span></button>
          <button type="button"><Palette :size="21" aria-hidden="true" /><span class="account-menu__label">个性化</span></button>
          <button type="button"><CircleUserRound :size="22" aria-hidden="true" /><span class="account-menu__label">个人资料</span></button>
          <button type="button"><Settings :size="22" aria-hidden="true" /><span class="account-menu__label">设置</span></button>
        </div>

        <div class="account-menu__divider" aria-hidden="true" />

        <div class="account-menu__actions">
          <button type="button"><CircleHelp :size="22" aria-hidden="true" /><span class="account-menu__label">帮助</span><ChevronRight :size="21" /></button>
          <button type="button" @click="requestLogout"><LogOut :size="22" aria-hidden="true" /><span class="account-menu__label">退出登录</span></button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.account-menu-layer {
  position: fixed;
  z-index: 80;
  inset: 0;
}

.account-menu {
  position: absolute;
  width: min(374px, calc(100vw - 16px));
  left: 8px;
  bottom: 32px;
  border: 1px solid #e4e4e4;
  border-radius: 26px;
  padding: 18px 25px 20px;
  color: #1f1f1f;
  background: #ffffff;
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.11);
}

.account-menu button {
  display: flex;
  width: 100%;
  min-height: 54px;
  align-items: center;
  gap: 13px;
  border: 0;
  border-radius: 8px;
  padding: 0 8px;
  color: inherit;
  background: transparent;
  font: inherit;
  font-size: 21px;
  font-weight: 400;
  line-height: 1.2;
  text-align: left;
  cursor: pointer;
}

.account-menu button:hover,
.account-menu button:focus-visible {
  outline: 0;
  background: #f5f5f5;
}

.account-menu__profile {
  min-height: 70px !important;
  padding: 0 2px !important;
}

.account-menu__avatar {
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  border-radius: 50%;
  object-fit: cover;
}

.account-menu__profile > span:not(.account-menu__avatar) {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.account-menu__profile strong {
  font-size: 20px;
  font-weight: 500;
}

.account-menu__profile small {
  color: #929292;
  font-size: 17px;
}

.account-menu__divider {
  height: 1px;
  margin: 10px 0;
  background: #e2e2e2;
}

.account-menu__actions {
  display: grid;
  gap: 1px;
}

.account-menu__actions svg {
  flex: 0 0 auto;
}

.account-menu__label {
  flex: 1;
  text-align: left;
}

.account-menu__actions button svg:last-child {
  margin-left: auto;
}

@media (max-width: 520px) {
  .account-menu {
    bottom: 32px;
    left: 8px;
    padding: 16px 24px 18px;
  }

  .account-menu button {
    min-height: 50px;
    font-size: 19px;
  }

  .account-menu__profile strong {
    font-size: 18px;
  }

  .account-menu__profile small {
    font-size: 15px;
  }
}
</style>
