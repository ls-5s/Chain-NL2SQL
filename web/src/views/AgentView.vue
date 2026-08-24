<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  AudioLines,
  CornerDownRight,
  ChevronDown,
  Database,
  FileText,
  LoaderCircle,
  Plus,
} from "lucide-vue-next";

import { createResultReference, fetchDatabases } from "@/api/client";
import { useAgentConversationStore } from "@/composables/agentConversations";
import { renderMarkdown } from "@/utils/markdown";
import type { QueryIntent, QueryResponse, QueryResult, QueryStatus } from "@/types/api";

const databases = ref<string[]>([]);
const conversation = ref<HTMLElement | null>(null);
const emptyQuestionInput = ref<HTMLTextAreaElement | null>(null);
const activeQuestionInput = ref<HTMLTextAreaElement | null>(null);
const agentStep = ref("正在准备查询");
const referenceIds = ref<string[]>([]);
const store = useAgentConversationStore();
const messages = computed(() => store.activeConversation.value.messages);
const question = computed({
  get: () => store.activeConversation.value.draft,
  set: (value: string) => store.setDraft(value),
});
const databaseId = computed({
  get: () => store.activeConversation.value.databaseId,
  set: (value: string) => { void store.setDatabaseId(value); },
});
const loading = computed(() => store.isBusy.value);
const clarificationRequired = computed(() => {
  const response = [...messages.value].reverse().find((message) => message.response)?.response;
  return response?.status === "needs_clarification";
});
const canSubmit = computed(
  () =>
    question.value.trim().length > 0 && !loading.value && Boolean(store.activeConversationId.value),
);

async function resizeQuestionInput(input: HTMLTextAreaElement | null) {
  if (!input) return;

  await nextTick();
  input.style.height = "auto";
  const styles = window.getComputedStyle(input);
  const minHeight = Number.parseFloat(styles.minHeight) || 0;
  const maxHeight = Number.parseFloat(styles.maxHeight) || 180;
  const contentHeight = input.scrollHeight;
  const nextHeight = Math.min(Math.max(contentHeight, minHeight), maxHeight);

  input.style.height = `${nextHeight}px`;
  input.style.overflowY = contentHeight > maxHeight ? "auto" : "hidden";
}

async function resizeQuestionInputs() {
  await Promise.all([
    resizeQuestionInput(emptyQuestionInput.value),
    resizeQuestionInput(activeQuestionInput.value),
  ]);
}

function handleQuestionInput() {
  void resizeQuestionInputs();
}

watch(
  question,
  () => {
    void resizeQuestionInputs();
  },
  { flush: "post" },
);

watch(
  [() => store.activeConversationId.value, () => messages.value.length],
  () => {
    void scrollToBottom();
  },
  { flush: "post", immediate: true },
);

onMounted(async () => {
  try {
    databases.value = await fetchDatabases();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "无法加载数据库列表");
  }
  await resizeQuestionInputs();
});

async function askQuestion(value = question.value) {
  const text = value.trim();
  if (!text || loading.value) return;

  const requestConversationId = store.activeConversationId.value;
  const requestReferenceIds = [...referenceIds.value];
  const isRequestActive = () => store.activeConversationId.value === requestConversationId;
  if (isRequestActive()) {
    agentStep.value = "正在连接查询 Agent";
    await scrollToBottom();
  }

  try {
    await store.sendQuestion(
      text,
      (event) => {
        if (isRequestActive() && event.message) {
          agentStep.value = event.message;
        }
      },
      requestReferenceIds,
    );
    if (isRequestActive()) referenceIds.value = [];
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "查询服务暂时不可用，请稍后重试。");
  } finally {
    if (isRequestActive()) {
      agentStep.value = "正在准备查询";
      await scrollToBottom();
    }
  }
}

function handleSubmit() {
  void askQuestion();
}

async function handleDatabaseChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  if (!value) return;
  try {
    await store.setDatabaseId(value);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "无法绑定数据库");
  }
}

function statusLabel(status: QueryStatus) {
  return ({
    succeeded: "查询完成",
    blocked: "已拦截",
    failed: "执行失败",
    running: "处理中",
    needs_clarification: "需要澄清",
    no_grounded_answer: "暂无可验证资料",
  } as Record<QueryStatus, string>)[status];
}

function statusClass(status: QueryStatus) {
  return `status-pill status-pill--${status}`;
}

function intentLabel(intent: QueryIntent) {
  const labels: Record<QueryIntent, string> = {
    data_query: "数据查询",
    general_chat: "通用回答",
    clarify: "需要澄清",
  };
  return labels[intent] ?? "通用回答";
}

function intentClass(intent: QueryIntent | string) {
  const normalizedIntent = intent === "data_query" ? "data_query" : "general_chat";
  return `intent-pill intent-pill--${normalizedIntent}`;
}

function resultColumns(result: QueryResult) {
  return result.columns.map((label) => ({ label, prop: label }));
}

function resultRows(response: QueryResponse) {
  const result = response.result;
  if (!result) return [];
  return result.rows.map((row, rowIndex) =>
    Object.assign(
      { __rowIndex: rowIndex },
      Object.fromEntries(result.columns.map((column, index) => [column, row[index]])),
    ),
  );
}

async function referenceRow(message: { turn_id: string }, rowIndex: number) {
  if (!store.activeConversationId.value || !message.turn_id) return;
  try {
    const reference = await createResultReference(
      store.activeConversationId.value,
      message.turn_id,
      rowIndex,
    );
    referenceIds.value = [reference.id];
    ElMessage.success(`${reference.label} 已加入下一次查询`);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "该行暂时不能引用。");
  }
}

async function scrollToBottom() {
  await nextTick();
  if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight;
}
</script>

<template>
  <section class="query-page">
    <div
      ref="conversation"
      class="conversation-panel"
      :class="{ 'conversation-panel--active': messages.length }"
    >
      <div v-if="!messages.length" class="empty-state">
        <div class="empty-state__content">
          <h1>想先查询什么？</h1>
          <form class="composer empty-composer" @submit.prevent="handleSubmit">
            <div class="composer__main">
              <button
                class="composer__icon-button"
                type="button"
                title="添加附件"
                aria-label="添加附件"
                :disabled="loading"
              >
                <Plus :size="23" :stroke-width="1.8" />
              </button>
              <textarea
                ref="emptyQuestionInput"
                v-model="question"
                rows="1"
                maxlength="2000"
                placeholder="向 Chain 查询数据"
                aria-label="输入查询问题"
                :disabled="loading"
                @input="handleQuestionInput"
                @keydown.enter.exact.prevent="handleSubmit"
              />
              <div class="composer__actions">
                <button
                  class="send-button"
                  type="submit"
                  :class="{ 'send-button--loading': loading }"
                  :disabled="!canSubmit"
                  aria-label="发送查询"
                  title="发送查询"
                >
                  <AudioLines :size="20" :stroke-width="2" />
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div v-else class="message-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="message-row"
          :class="`message-row--${message.role}`"
        >
          <div class="message-bubble">
            <div class="message-meta">{{ message.role === "user" ? "你" : "Chain Agent" }}</div>
            <p v-if="message.role === 'user'">{{ message.content }}</p>

            <details v-if="message.progress?.length" class="reasoning-timeline" open>
              <summary class="reasoning-timeline__title">
                <span>执行过程</span>
                <ChevronDown class="reasoning-timeline__chevron" :size="17" aria-hidden="true" />
              </summary>
              <div
                v-for="step in message.progress"
                :key="`${step.node}-${step.iteration}`"
                class="reasoning-step"
              >
                <span class="reasoning-step__dot" />
                <div class="reasoning-step__body">
                  <strong>{{ step.message }}</strong>
                  <small>{{ step.explanation }}</small>
                  <code v-if="step.sql">{{ step.sql }}</code>
                </div>
              </div>
            </details>

            <div
              v-if="message.role === 'assistant'"
              class="message-answer message-markdown"
              v-html="renderMarkdown(message.content)"
            />
            <span
              v-if="message.response && message.response.intent !== 'data_query'"
              :class="intentClass(message.response.intent)"
            >
              {{ intentLabel(message.response.intent) }}
            </span>

            <div v-if="message.response?.intent === 'data_query'" class="response-card">
              <div class="response-card__header">
                <div class="response-card__title"><Database :size="16" />{{ databaseId || "未选择数据库" }}</div>
                <span :class="statusClass(message.response.status)"
                  >{{ intentLabel(message.response.intent) }} ·
                  {{ statusLabel(message.response.status) }}</span
                >
              </div>
              <el-table
                v-if="message.response.result?.rows.length"
                :data="resultRows(message.response)"
                size="small"
                stripe
                class="result-table"
              >
                <el-table-column
                  v-for="column in resultColumns(message.response.result)"
                  :key="column.prop"
                  v-bind="column"
                  min-width="130"
                />
                <el-table-column label="引用" width="58" fixed="right">
                  <template #default="scope">
                    <button
                      class="row-reference-button"
                      type="button"
                      title="引用此行"
                      aria-label="引用此行"
                      @click="referenceRow(message, scope.row.__rowIndex)"
                    >
                      <CornerDownRight :size="15" aria-hidden="true" />
                    </button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-else class="result-empty">没有返回数据行</div>
              <div class="response-card__footer">
                <span>返回 {{ message.response.result?.row_count ?? 0 }} 行</span>
              </div>
            </div>

            <details v-if="message.response?.knowledge_hits?.length" class="knowledge-hits" open>
              <summary class="knowledge-hits__title">
                <span><FileText :size="15" />知识命中</span>
                <ChevronDown class="knowledge-hits__chevron" :size="16" aria-hidden="true" />
              </summary>
              <div class="knowledge-hits__list">
                <article
                  v-for="hit in message.response.knowledge_hits"
                  :key="hit.document_id"
                  class="knowledge-hit"
                >
                  <div class="knowledge-hit__meta">
                    <strong>{{ hit.title }}</strong
                    ><span>{{ hit.category }}</span>
                  </div>
                  <p>{{ hit.excerpt }}</p>
                </article>
              </div>
            </details>
          </div>
        </article>
        <div v-if="loading" class="message-row message-row--assistant">
          <div class="message-bubble message-bubble--loading">
            <LoaderCircle class="spin" :size="17" aria-hidden="true" />
            {{ agentStep }}<span class="loading-dots">...</span>
          </div>
        </div>
      </div>
    </div>

    <footer v-if="messages.length" class="composer-wrap">
      <div v-if="clarificationRequired && databases.length" class="clarification-control">
        <label for="clarification-database">选择数据库后重新提交</label>
        <select id="clarification-database" :value="databaseId || ''" @change="handleDatabaseChange">
          <option value="" disabled>选择数据库</option>
          <option v-for="database in databases" :key="database" :value="database">{{ database }}</option>
        </select>
      </div>
      <form class="composer" @submit.prevent="handleSubmit">
        <div class="composer__main">
          <button
            class="composer__icon-button"
            type="button"
            title="添加附件"
            aria-label="添加附件"
          >
            <Plus :size="22" :stroke-width="1.8" />
          </button>
          <textarea
            ref="activeQuestionInput"
            v-model="question"
            rows="1"
            maxlength="2000"
            placeholder="向 Chain 查询演示数据"
            aria-label="输入查询问题"
            @input="handleQuestionInput"
            @keydown.enter.exact.prevent="handleSubmit"
          />
          <div class="composer__actions">
            <button
              class="send-button"
              type="submit"
              :disabled="!canSubmit"
              aria-label="发送查询"
              title="发送查询"
            >
              <LoaderCircle v-if="loading" class="spin" :size="18" />
              <AudioLines v-else :size="19" :stroke-width="2" />
            </button>
          </div>
        </div>
      </form>
      <p class="composer-note">Chain 可能会出错，请核对重要结果。</p>
    </footer>
  </section>
</template>

<style scoped>
.query-page {
  display: flex;
  height: 100vh;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  color: #202123;
  font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", system-ui, sans-serif;
  font-weight: 400;
  letter-spacing: 0;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
.query-topbar {
  display: flex;
  height: 58px;
  flex: 0 0 58px;
  align-items: center;
  justify-content: space-between;
  padding: 0 clamp(18px, 3vw, 42px);
}
.query-topbar__title {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #202123;
  font-size: 14px;
  font-weight: 650;
}
.query-topbar__mark {
  display: grid;
  width: 27px;
  height: 27px;
  place-items: center;
  border-radius: 8px;
  color: #fff;
  background: #202123;
}
.reset-button {
  display: inline-flex;
  height: 32px;
  align-items: center;
  gap: 7px;
  border: 1px solid #e6e6e6;
  border-radius: 8px;
  padding: 0 10px;
  color: #666;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
  transition:
    background 0.16s,
    color 0.16s;
}
.reset-button:hover {
  color: #202123;
  background: #f7f7f7;
}
.conversation-panel {
  width: 100%;
  min-height: 0;
  flex: 1 1 auto;
  overflow: auto;
  padding: 0 18px 18px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.conversation-panel::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
.conversation-panel--active {
  max-width: 900px;
  margin: 0 auto;
}
.empty-state {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 0 7vh;
  text-align: center;
}
.empty-state__content {
  width: min(720px, 100%);
}
.empty-state h1 {
  margin: 0;
  color: #1f1f1f;
  font-size: 32px;
  font-weight: 600;
  letter-spacing: 0;
}
.message-list {
  display: flex;
  flex-direction: column;
  gap: 30px;
  width: 100%;
  padding: 34px 8px 140px;
}
.message-row {
  display: flex;
  align-items: flex-start;
}
.message-row--user {
  flex-direction: row-reverse;
}
.message-bubble {
  max-width: min(680px, 100%);
  color: #303030;
  font-size: 21px;
  line-height: 1.72;
}
.message-row--user .message-bubble {
  text-align: right;
}
.message-meta {
  display: none;
}
.message-bubble > p {
  display: inline-block;
  margin: 0;
  max-width: 100%;
  border-radius: 18px;
  padding: 11px 18px;
  background: #f2f2f2;
  text-align: left;
  overflow-wrap: anywhere;
}
.message-row--assistant .message-bubble > p {
  border-radius: 4px;
  padding: 2px 0;
  background: transparent;
  font-size: 21px;
  line-height: 1.75;
}
.message-answer {
  margin-top: 16px !important;
  color: #303030;
}
.message-markdown {
  display: block;
  max-width: 100%;
  overflow-wrap: anywhere;
  text-align: left;
}
.message-markdown :deep(p),
.message-markdown :deep(ul),
.message-markdown :deep(ol),
.message-markdown :deep(blockquote),
.message-markdown :deep(pre),
.message-markdown :deep(h1),
.message-markdown :deep(h2),
.message-markdown :deep(h3),
.message-markdown :deep(h4),
.message-markdown :deep(h5),
.message-markdown :deep(h6) {
  margin: 0 0 14px;
}
.message-markdown :deep(p:last-child),
.message-markdown :deep(ul:last-child),
.message-markdown :deep(ol:last-child),
.message-markdown :deep(blockquote:last-child),
.message-markdown :deep(pre:last-child),
.message-markdown :deep(h1:last-child),
.message-markdown :deep(h2:last-child),
.message-markdown :deep(h3:last-child),
.message-markdown :deep(h4:last-child),
.message-markdown :deep(h5:last-child),
.message-markdown :deep(h6:last-child) {
  margin-bottom: 0;
}
.message-markdown :deep(h1),
.message-markdown :deep(h2),
.message-markdown :deep(h3),
.message-markdown :deep(h4),
.message-markdown :deep(h5),
.message-markdown :deep(h6) {
  color: #202123;
  font-weight: 700;
  line-height: 1.35;
}
.message-markdown :deep(h1) {
  font-size: 1.35em;
}
.message-markdown :deep(h2) {
  font-size: 1.25em;
}
.message-markdown :deep(h3) {
  font-size: 1.15em;
}
.message-markdown :deep(ul),
.message-markdown :deep(ol) {
  padding-left: 1.45em;
}
.message-markdown :deep(li + li) {
  margin-top: 5px;
}
.message-markdown :deep(blockquote) {
  border-left: 3px solid #d8d8d8;
  padding-left: 14px;
  color: #6d6d6d;
}
.message-markdown :deep(code) {
  border-radius: 4px;
  padding: 0.12em 0.35em;
  color: #3f3f3f;
  background: #f0f0f0;
  font:
    0.86em/1.5 ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
}
.message-markdown :deep(pre) {
  overflow-x: auto;
  border-radius: 7px;
  padding: 12px 14px;
  color: #303030;
  background: #f4f4f4;
  white-space: pre;
}
.message-markdown :deep(pre code) {
  padding: 0;
  color: inherit;
  background: transparent;
  font-size: 0.78em;
}
.message-markdown :deep(a) {
  color: #356fc4;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.message-markdown :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}
.message-row--user .message-bubble > p {
  border-bottom-right-radius: 4px;
}
.intent-pill {
  display: inline-block;
  margin-top: 11px;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 700;
}
.intent-pill--general_chat {
  color: #486bb1;
  background: #eaf1ff;
}
.message-bubble--loading {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 0;
  color: #777;
}
.loading-dots {
  color: #333;
}
.reasoning-timeline {
  width: min(100%, 676px);
  margin-top: 10px;
  padding: 6px 0 2px;
  border: 0;
  border-radius: 0;
  background: transparent;
  text-align: left;
}
.reasoning-timeline__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  color: #777;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.4;
  cursor: pointer;
  list-style: none;
}
.reasoning-timeline__title::-webkit-details-marker {
  display: none;
}
.reasoning-timeline__title:focus-visible {
  outline: 2px solid #c8c8c8;
  outline-offset: 3px;
  border-radius: 4px;
}
.reasoning-timeline__chevron {
  flex: 0 0 auto;
  color: #a7a7a7;
  transition: transform 0.18s ease;
}
.reasoning-timeline[open] .reasoning-timeline__chevron {
  transform: rotate(180deg);
}
.reasoning-timeline:not([open]) {
  padding-bottom: 2px;
}
.reasoning-timeline:not([open]) .reasoning-timeline__title {
  margin-bottom: 0;
}
.reasoning-step {
  display: flex;
  gap: 9px;
  position: relative;
  padding-bottom: 10px;
}
.reasoning-step:last-child {
  padding-bottom: 0;
}
.reasoning-step:not(:last-child)::before {
  content: "";
  position: absolute;
  top: 9px;
  bottom: 0;
  left: 3px;
  width: 1px;
  background: #e5e5e5;
}
.reasoning-step__dot {
  z-index: 1;
  width: 6px;
  height: 6px;
  margin-top: 5px;
  flex: 0 0 6px;
  border-radius: 50%;
  background: #b8b8b8;
}
.reasoning-step__body {
  min-width: 0;
}
.reasoning-step strong,
.reasoning-step small,
.reasoning-step code {
  display: block;
}
.reasoning-step strong {
  color: #5f5f5f;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.45;
}
.reasoning-step small {
  margin-top: 2px;
  color: #9a9a9a;
  font-size: 12px;
  line-height: 1.5;
}
.reasoning-step code {
  overflow-x: auto;
  max-width: 100%;
  margin-top: 5px;
  padding: 5px 7px;
  border-radius: 5px;
  color: #3f3f3f;
  background: #f3f3f3;
  font:
    10.5px/1.45 ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
  white-space: pre-wrap;
  word-break: break-word;
}
.response-card {
  margin-top: 14px;
  overflow: hidden;
  border: 1px solid #e4e4e4;
  border-radius: 9px;
  background: #fff;
  text-align: left;
}
.knowledge-hits {
  margin-top: 14px;
  overflow: hidden;
  border: 1px solid #e4e4e4;
  border-radius: 9px;
  background: #fff;
  text-align: left;
}
.knowledge-hits__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 42px;
  padding: 0 13px;
  color: #4a4b49;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  list-style: none;
}
.knowledge-hits__title::-webkit-details-marker {
  display: none;
}
.knowledge-hits__title span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.knowledge-hits__chevron {
  transition: transform 150ms ease;
}
.knowledge-hits[open] .knowledge-hits__chevron {
  transform: rotate(180deg);
}
.knowledge-hits__list {
  display: grid;
  gap: 8px;
  padding: 0 13px 13px;
}
.knowledge-hit {
  border-top: 1px solid #f0f0ef;
  padding-top: 9px;
}
.knowledge-hit__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.knowledge-hit__meta strong {
  overflow: hidden;
  color: #353634;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.knowledge-hit__meta span {
  flex: 0 0 auto;
  color: #8a8b87;
  font-size: 10px;
}
.knowledge-hit p {
  margin: 5px 0 0;
  color: #777875;
  font-size: 11px;
  line-height: 1.55;
}
.response-card__header,
.response-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
}
.response-card__header {
  border-bottom: 1px solid #ededed;
}
.response-card__title {
  display: flex;
  gap: 7px;
  align-items: center;
  color: #555;
  font-size: 12px;
  font-weight: 700;
}
.status-pill {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
}
.status-pill--succeeded {
  color: #18855c;
  background: #e7f7ef;
}
.status-pill--blocked {
  color: #b46615;
  background: #fff3dc;
}
.status-pill--failed {
  color: #c04855;
  background: #ffebed;
}
.status-pill--running {
  color: #6356c8;
  background: #eeeaff;
}
.result-table {
  width: 100%;
}
.row-reference-button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: 5px;
  color: #5f6963;
  background: transparent;
  cursor: pointer;
}
.row-reference-button:hover,
.row-reference-button:focus-visible {
  outline: 0;
  color: #202b26;
  background: #eaf1ed;
}
.result-empty {
  padding: 24px 14px;
  color: #9da2af;
  font-size: 13px;
}
.response-card__footer {
  color: #8a8a8a;
  font-size: 12px;
}
.composer-wrap {
  z-index: 2;
  flex: 0 0 auto;
  width: min(760px, calc(100% - 36px));
  margin: auto;
  padding: 12px 0 17px;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0), #fff 24%);
}
.clarification-control {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 10px;
  color: #666;
  font-size: 12px;
}
.clarification-control select {
  min-height: 30px;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 0 8px;
  color: #333;
  background: #fff;
}
.composer {
  padding: 9px 11px 8px;
  border: 1px solid #e1e1e1;
  border-radius: 25px;
  background: #fff;
  transition: border-color 0.16s;
}
.empty-composer {
  width: 100%;
  margin-top: 44px;
  border-radius: 40px;
  padding: 12px 14px;
}
.empty-composer .composer__main {
  min-height: 52px;
  gap: 9px;
}
.empty-composer textarea {
  min-height: 32px;
  padding: 7px 4px;
  font-size: 21px;
}
.empty-composer .composer__icon-button {
  width: 42px;
  height: 42px;
  flex-basis: 42px;
}
.empty-composer .send-button {
  width: 48px;
  height: 48px;
  flex-basis: 48px;
}
.empty-composer .send-button--loading:disabled {
  color: #fff;
  background: #3f82f5;
  cursor: default;
}
.composer:focus-within {
  border-color: #c6c6c6;
}
.composer__main {
  display: flex;
  min-height: 42px;
  align-items: center;
  gap: 7px;
}
.composer textarea {
  display: block;
  min-width: 0;
  width: 100%;
  flex: 1 1 auto;
  min-height: 26px;
  max-height: 180px;
  border: 0;
  outline: 0;
  padding: 6px 2px;
  box-sizing: border-box;
  resize: none;
  overflow-y: hidden;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  scrollbar-color: #b8b8b8 transparent;
  scrollbar-width: thin;
  color: #242424;
  background: transparent;
  font:
    21px/1.45 "Microsoft YaHei",
    "PingFang SC",
    "Segoe UI",
    system-ui,
    sans-serif;
}
.composer textarea::-webkit-scrollbar {
  width: 8px;
}
.composer textarea::-webkit-scrollbar-track {
  background: transparent;
}
.composer textarea::-webkit-scrollbar-thumb {
  border: 2px solid transparent;
  border-radius: 8px;
  background: #b8b8b8;
  background-clip: padding-box;
}
.composer textarea::placeholder {
  color: #929292;
}
.composer__actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 2px;
}
.composer__icon-button {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  color: #4e4e4e;
  background: transparent;
  cursor: pointer;
  transition:
    background 0.16s,
    color 0.16s;
}
.composer__icon-button:hover {
  color: #202123;
  background: #f1f1f1;
}
.send-button {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  color: #fff;
  background: #3f82f5;
  cursor: pointer;
  transition:
    background 0.16s,
    transform 0.16s;
}
.send-button:hover:not(:disabled) {
  background: #276ddd;
  transform: scale(1.03);
}
.send-button:disabled {
  color: #b7b7b7;
  background: #ececec;
  cursor: default;
}
.composer-note {
  margin: 8px 0 0;
  color: #999;
  font-size: 11px;
  text-align: center;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 700px) {
  .query-page {
    height: 100vh;
  }
  .query-topbar {
    padding-inline: 16px;
  }
  .reset-button span {
    display: none;
  }
  .conversation-panel {
    padding-inline: 14px;
  }
  .empty-state {
    padding-bottom: 5vh;
  }
  .empty-state h1 {
    font-size: 26px;
  }
  .empty-composer {
    margin-top: 30px;
    border-radius: 30px;
    padding: 9px 10px;
  }
  .empty-composer .composer__main {
    min-height: 46px;
    gap: 4px;
  }
  .empty-composer textarea {
    min-width: 0;
    padding-inline: 0;
    font-size: 18px;
  }
  .empty-composer .composer__icon-button {
    width: 38px;
    height: 38px;
    flex-basis: 38px;
  }
  .empty-composer .send-button {
    width: 42px;
    height: 42px;
    flex-basis: 42px;
  }
  .message-list {
    gap: 25px;
    padding-inline: 0;
    padding-top: 16px;
  }
  .message-bubble {
    max-width: 100%;
    font-size: 18px;
    line-height: 1.7;
  }
  .message-bubble > p {
    max-width: none;
    padding: 10px 14px;
    overflow-wrap: normal;
  }
  .message-row--assistant .message-bubble > p {
    font-size: 18px;
    line-height: 1.7;
  }
  .message-answer {
    margin-top: 14px !important;
  }
  .message-markdown :deep(p),
  .message-markdown :deep(ul),
  .message-markdown :deep(ol),
  .message-markdown :deep(blockquote),
  .message-markdown :deep(pre),
  .message-markdown :deep(h1),
  .message-markdown :deep(h2),
  .message-markdown :deep(h3),
  .message-markdown :deep(h4),
  .message-markdown :deep(h5),
  .message-markdown :deep(h6) {
    margin-bottom: 11px;
  }
  .intent-pill {
    margin-top: 8px;
    padding: 4px 8px;
    font-size: 11px;
  }
  .reasoning-timeline {
    width: auto;
    margin-top: 8px;
    padding: 5px 0 2px;
    border: 0;
    border-radius: 0;
    background: transparent;
  }
  .reasoning-timeline__title {
    margin-bottom: 8px;
    font-size: 13px;
  }
  .reasoning-step {
    gap: 8px;
    padding-bottom: 9px;
  }
  .reasoning-step:not(:last-child)::before {
    top: 8px;
    left: 2.5px;
  }
  .reasoning-step__dot {
    width: 5px;
    height: 5px;
    margin-top: 5px;
    flex-basis: 5px;
  }
  .reasoning-step strong {
    font-size: 14px;
  }
  .reasoning-step small {
    margin-top: 2px;
    font-size: 11px;
    line-height: 1.5;
  }
  .composer-wrap {
    width: calc(100% - 24px);
    padding-bottom: 12px;
  }
  .composer {
    border-radius: 20px;
  }
  .composer textarea {
    font-size: 18px;
  }
}
</style>
