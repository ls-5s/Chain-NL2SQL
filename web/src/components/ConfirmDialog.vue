<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { LoaderCircle, TriangleAlert, X } from "lucide-vue-next";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    description?: string;
    confirmText?: string;
    cancelText?: string;
    busy?: boolean;
    busyText?: string;
    error?: string;
  }>(),
  {
    description: "确认执行此操作吗？",
    confirmText: "确认",
    cancelText: "取消",
    busy: false,
    busyText: "处理中",
    error: "",
  },
);

const emit = defineEmits<{
  "update:open": [open: boolean];
  confirm: [];
}>();

const cancelButton = ref<HTMLButtonElement | null>(null);
const instanceId = Math.random().toString(36).slice(2, 9);
const titleId = `confirm-dialog-title-${instanceId}`;
const descriptionId = `confirm-dialog-description-${instanceId}`;

function close() {
  if (!props.busy) emit("update:open", false);
}

function confirm() {
  if (!props.busy) emit("confirm");
}

function focusCancelButton() {
  if (props.open) void nextTick(() => cancelButton.value?.focus());
}

watch(() => props.open, focusCancelButton);
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="confirm-dialog-backdrop"
      role="presentation"
      @click.self="close"
      @keydown.esc="close"
    >
      <section
        class="confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="descriptionId"
      >
        <header class="confirm-dialog__header">
          <div class="confirm-dialog__title">
            <span class="confirm-dialog__icon">
              <slot name="icon"><TriangleAlert :size="18" /></slot>
            </span>
            <div>
              <h2 :id="titleId">{{ title }}</h2>
            </div>
          </div>
          <button
            class="confirm-dialog__close"
            type="button"
            aria-label="关闭"
            title="关闭"
            :disabled="busy"
            @click="close"
          >
            <X :size="19" />
          </button>
        </header>

        <p :id="descriptionId" class="confirm-dialog__description">
          <slot name="description">{{ description }}</slot>
        </p>
        <p v-if="error" class="confirm-dialog__error" role="alert">{{ error }}</p>

        <footer class="confirm-dialog__actions">
          <button
            ref="cancelButton"
            class="confirm-dialog__cancel"
            type="button"
            :disabled="busy"
            @click="close"
          >
            {{ cancelText }}
          </button>
          <button class="confirm-dialog__confirm" type="button" :disabled="busy" @click="confirm">
            <LoaderCircle v-if="busy" class="confirm-dialog__spinner" :size="16" />
            {{ busy ? busyText : confirmText }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.confirm-dialog-backdrop {
  position: fixed;
  z-index: 120;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(32, 33, 35, 0.2);
  backdrop-filter: blur(4px);
}
.confirm-dialog {
  width: min(594px, calc(100vw - 32px));
  border: 1px solid #e2e2df;
  border-radius: 16px;
  padding: 32px;
  background: #ffffff;
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.14);
}
.confirm-dialog__header,
.confirm-dialog__actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}
.confirm-dialog__header {
  margin-bottom: 28px;
}
.confirm-dialog__title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 15px;
}
.confirm-dialog__icon {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 12px;
  color: #a44747;
  background: #fff0f0;
}
.confirm-dialog h2 {
  margin: 0;
  color: #202123;
  font-size: 26px;
  font-weight: 750;
  line-height: 1.15;
}
.confirm-dialog__close {
  display: inline-grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #777875;
  background: transparent;
  cursor: pointer;
}
.confirm-dialog__close:hover:not(:disabled) {
  border-color: #e0e0dd;
  color: #202123;
  background: #f4f4f2;
}
.confirm-dialog__close:focus-visible,
.confirm-dialog__cancel:focus-visible,
.confirm-dialog__confirm:focus-visible {
  outline: 2px solid #6f8b77;
  outline-offset: 2px;
}
.confirm-dialog__description {
  margin: 0;
  color: #5f605d;
  font-size: 16px;
  line-height: 1.6;
}
.confirm-dialog__error {
  margin: 20px 0 0;
  border: 1px solid #ebcaca;
  border-radius: 9px;
  padding: 12px 14px;
  color: #9c4141;
  background: #fff8f8;
  font-size: 14px;
}
.confirm-dialog__actions {
  align-items: center;
  justify-content: flex-end;
  margin-top: 30px;
}
.confirm-dialog__cancel,
.confirm-dialog__confirm {
  display: inline-flex;
  min-height: 54px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border-radius: 10px;
  padding: 0 20px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}
.confirm-dialog__cancel {
  min-width: 78px;
  border: 1px solid #d6d6d3;
  color: #4f504e;
  background: #ffffff;
}
.confirm-dialog__cancel:hover:not(:disabled) {
  border-color: #bdbdb9;
  background: #f6f6f4;
}
.confirm-dialog__confirm {
  min-width: 113px;
  border: 1px solid #b84b4b;
  color: #ffffff;
  background: #b84b4b;
}
.confirm-dialog__confirm:hover:not(:disabled) {
  border-color: #963d3d;
  background: #963d3d;
  box-shadow: 0 4px 10px rgba(150, 61, 61, 0.16);
}
.confirm-dialog__cancel:disabled,
.confirm-dialog__confirm:disabled,
.confirm-dialog__close:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.confirm-dialog__spinner {
  animation: confirm-dialog-spin 0.8s linear infinite;
}
@keyframes confirm-dialog-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 640px) {
  .confirm-dialog-backdrop {
    padding: 12px;
  }
  .confirm-dialog {
    width: min(100%, 594px);
    padding: 24px;
  }
  .confirm-dialog__header {
    margin-bottom: 22px;
  }
  .confirm-dialog h2 {
    font-size: 22px;
  }
  .confirm-dialog__description {
    font-size: 15px;
  }
  .confirm-dialog__actions {
    align-items: stretch;
    flex-direction: column-reverse;
  }
  .confirm-dialog__cancel,
  .confirm-dialog__confirm {
    width: 100%;
  }
}
</style>
