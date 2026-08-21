<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  AudioLines,
  Database,
  LoaderCircle,
  Mic,
  Plus,
  Sparkles,
  UserRound,
} from "lucide-vue-next";

import { fetchDatabases, streamQuery } from "@/api/client";
import { useAgentConversationStore, type AgentChatMessage } from "@/composables/agentConversations";
import type {
  QueryIntent,
  QueryResponse,
  QueryResult,
  QueryStatus,
} from "@/types/api";

const question = ref("");
const databaseId = ref("demo");
const databases = ref<string[]>([]);
const loading = ref(false);
const conversation = ref<HTMLElement | null>(null);
const agentStep = ref("正在准备查询");
const store = useAgentConversationStore();
const messages = computed(() => store.activeConversation.value.messages);

watch(
  () => store.activeConversationId.value,
  () => {
    question.value = store.activeConversation.value.draft;
    databaseId.value = store.activeConversation.value.databaseId;
    loading.value = false;
    void scrollToBottom();
  },
  { immediate: true },
);

watch(question, (value) => {
  if (!loading.value && value !== store.activeConversation.value.draft) store.setDraft(value);
});

watch(databaseId, (value) => {
  if (value !== store.activeConversation.value.databaseId) store.setDatabaseId(value);
});

const canSubmit = computed(() => question.value.trim().length > 0 && !loading.value);

onMounted(async () => {
  try {
    databases.value = await fetchDatabases();
    if (databases.value.length && !databases.value.includes(databaseId.value)) {
      databaseId.value = databases.value[0];
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "无法加载数据库列表");
  }
});

async function askQuestion(value = question.value) {
  const text = value.trim();
  if (!text || loading.value) return;

  question.value = "";
  const userMessage: AgentChatMessage = { id: crypto.randomUUID(), role: "user", content: text };
  store.appendMessage(userMessage);
  const assistantMessage: AgentChatMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "正在准备查询",
    progress: [],
  };
  store.appendMessage(assistantMessage);
  loading.value = true;
  store.setBusy(true);
  store.setDraft("");
  agentStep.value = "正在连接查询 Agent";
  await scrollToBottom();

  try {
    const response = await streamQuery(
      { question: text, database_id: databaseId.value },
      (event) => {
        if (event.message) {
          agentStep.value = event.message;
          store.updateMessage(assistantMessage.id, (message) => {
            message.content = event.message || message.content;
            message.progress = message.progress || [];
          });
        }
        if (event.node) {
          store.updateMessage(assistantMessage.id, (message) => {
            message.progress = message.progress || [];
            message.progress.push(event);
          });
        }
      },
    );
    store.updateMessage(assistantMessage.id, (message) => {
      message.content = response.final_answer;
      message.response = response;
    });
  } catch (error) {
    store.updateMessage(assistantMessage.id, (message) => {
      message.content = error instanceof Error ? error.message : "查询服务暂时不可用，请稍后重试。";
    });
  } finally {
    loading.value = false;
    store.setBusy(false);
    agentStep.value = "正在准备查询";
    await scrollToBottom();
  }
}

function handleSubmit() {
  void askQuestion();
}

function statusLabel(status: QueryStatus) {
  return { succeeded: "查询完成", blocked: "已拦截", failed: "执行失败", running: "处理中" }[
    status
  ];
}

function statusClass(status: QueryStatus) {
  return `status-pill status-pill--${status}`;
}

function intentLabel(intent: QueryIntent) {
  return {
    data_query: "数据查询",
    general_chat: "通用回答",
    clarification: "需要补充信息",
  }[intent];
}

function intentClass(intent: QueryIntent) {
  return `intent-pill intent-pill--${intent}`;
}

function resultColumns(result: QueryResult) {
  return result.columns.map((label) => ({ label, prop: label }));
}

function resultRows(response: QueryResponse) {
  const result = response.result;
  if (!result) return [];
  return result.rows.map((row) =>
    Object.fromEntries(result.columns.map((column, index) => [column, row[index]])),
  );
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
        <div class="empty-state__icon"><Sparkles :size="26" /></div>
        <h1>准备好了，随时开始</h1>
        <p>用自然语言查询演示数据，Chain 会判断是否需要生成只读 SQL。</p>
        <div class="suggestion-list">
          <button type="button" @click="askQuestion('查询用户数量')">
            <span class="suggestion-copy">查询用户数量</span>
            <span class="suggestion-type suggestion-type--data">数据查询</span>
          </button>
          <button type="button" @click="askQuestion('统计各类商品的销售情况')">
            <span class="suggestion-copy">统计各类商品的销售情况</span>
            <span class="suggestion-type suggestion-type--data">数据查询</span>
          </button>
          <button type="button" @click="askQuestion('查询最近的订单')">
            <span class="suggestion-copy">查询最近的订单</span>
            <span class="suggestion-type suggestion-type--data">数据查询</span>
          </button>
          <button type="button" @click="askQuestion('按订单状态统计订单数量')">
            <span class="suggestion-copy">按订单状态统计订单数量</span>
            <span class="suggestion-type suggestion-type--data">数据查询</span>
          </button>
          <button type="button" @click="askQuestion('帮我写一封会议邀请邮件')">
            <span class="suggestion-copy">帮我写一封会议邀请邮件</span>
            <span class="suggestion-type suggestion-type--general">通用问答</span>
          </button>
          <button type="button" @click="askQuestion('订单情况怎么样？')">
            <span class="suggestion-copy">订单情况怎么样？</span>
            <span class="suggestion-type suggestion-type--clarification">需补充信息</span>
          </button>
        </div>
      </div>

      <div v-else class="message-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="message-row"
          :class="`message-row--${message.role}`"
        >
          <div class="message-avatar">
            <UserRound v-if="message.role === 'user'" :size="17" />
            <Sparkles v-else :size="17" />
          </div>
          <div class="message-bubble">
            <div class="message-meta">{{ message.role === "user" ? "你" : "Chain Agent" }}</div>
            <p v-if="message.role === 'user'">{{ message.content }}</p>

            <div v-if="message.progress?.length" class="reasoning-timeline">
              <div class="reasoning-timeline__title">执行过程</div>
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
            </div>

            <p v-if="message.role === 'assistant'" class="message-answer">{{ message.content }}</p>
            <span
              v-if="message.response && message.response.intent !== 'data_query'"
              :class="intentClass(message.response.intent)"
            >
              {{ intentLabel(message.response.intent) }}
            </span>

            <div v-if="message.response?.intent === 'data_query'" class="response-card">
              <div class="response-card__header">
                <div class="response-card__title"><Database :size="16" />{{ databaseId }}</div>
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
              </el-table>
              <div v-else class="result-empty">没有返回数据行</div>
              <div class="response-card__footer">
                <span>返回 {{ message.response.result?.row_count ?? 0 }} 行</span>
              </div>
            </div>
          </div>
        </article>
        <div v-if="loading" class="message-row message-row--assistant">
          <div class="message-avatar"><LoaderCircle class="spin" :size="17" /></div>
          <div class="message-bubble message-bubble--loading">
            {{ agentStep }}<span class="loading-dots">...</span>
          </div>
        </div>
      </div>
    </div>

    <footer class="composer-wrap">
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
            v-model="question"
            rows="1"
            maxlength="2000"
            placeholder="向 Chain 查询演示数据"
            aria-label="输入查询问题"
            @keydown.enter.exact.prevent="handleSubmit"
          />
          <div class="composer__actions">
            <label class="database-picker" title="选择数据源">
              <Database :size="16" />
              <span class="sr-only">选择数据源</span>
              <select v-model="databaseId" :disabled="loading" aria-label="选择数据源">
                <option v-for="database in databases" :key="database" :value="database">
                  {{ database }}
                </option>
              </select>
            </label>
            <button
              class="composer__icon-button composer__mic"
              type="button"
              title="语音输入"
              aria-label="语音输入"
            >
              <Mic :size="20" :stroke-width="1.8" />
            </button>
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
        <div class="composer__context">
          <span class="readonly-badge"><span class="readonly-dot" />只读模式</span>
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
  min-height: min(550px, calc(100vh - 240px));
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 20px;
  text-align: center;
}
.empty-state__icon {
  display: grid;
  width: 52px;
  height: 52px;
  margin-bottom: 20px;
  place-items: center;
  border-radius: 15px;
  color: #fff;
  background: #202123;
}
.empty-state h1 {
  margin: 0;
  color: #202123;
  font-size: clamp(27px, 3vw, 34px);
  font-weight: 500;
  letter-spacing: 0;
}
.empty-state p {
  max-width: 480px;
  margin: 12px 0 24px;
  color: #8a8a8a;
  font-size: 13px;
  line-height: 1.55;
}
.suggestion-list {
  display: grid;
  width: min(580px, 100%);
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.suggestion-list button {
  display: flex;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  padding: 9px 12px;
  color: #4d4d4d;
  background: #fff;
  font: inherit;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.16s,
    background 0.16s,
    transform 0.16s;
}
.suggestion-list button:hover {
  border-color: #cfcfcf;
  background: #fafafa;
  transform: translateY(-1px);
}
.suggestion-copy {
  min-width: 0;
  overflow-wrap: anywhere;
}
.suggestion-type {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 3px 7px;
  font-size: 10px;
  line-height: 1.2;
  white-space: nowrap;
}
.suggestion-type--data {
  color: #366f9b;
  background: #eef6fc;
}
.suggestion-type--general {
  color: #327457;
  background: #edf8f1;
}
.suggestion-type--clarification {
  color: #9a6a2b;
  background: #fff6e7;
}
.message-list {
  display: flex;
  flex-direction: column;
  gap: 25px;
  width: 100%;
  padding: 22px 0 140px;
}
.message-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.message-row--user {
  flex-direction: row-reverse;
}
.message-avatar {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: #343434;
}
.message-row--assistant .message-avatar {
  color: #fff;
  background: #1f2933;
}
.message-bubble {
  max-width: min(720px, calc(100% - 44px));
  color: #303030;
  font-size: 14px;
  line-height: 1.7;
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
  border-radius: 18px;
  padding: 10px 14px;
  background: #f1f1f1;
  text-align: left;
}
.message-row--assistant .message-bubble > p {
  border-radius: 4px;
  padding: 2px 0;
  background: transparent;
}
.message-answer {
  margin-top: 14px !important;
  color: #303030;
}
.message-row--user .message-bubble > p {
  border-bottom-right-radius: 4px;
}
.intent-pill {
  display: inline-block;
  margin-top: 8px;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
}
.intent-pill--general_chat {
  color: #486bb1;
  background: #eaf1ff;
}
.intent-pill--clarification {
  color: #a06a16;
  background: #fff2d9;
}
.message-bubble--loading {
  padding: 4px 0;
  color: #777;
}
.loading-dots {
  color: #333;
}
.reasoning-timeline {
  margin-top: 14px;
  padding: 12px 13px;
  border: 1px solid #e7e7e7;
  border-radius: 8px;
  background: #fafafa;
  text-align: left;
}
.reasoning-timeline__title {
  margin-bottom: 11px;
  color: #5e5e5e;
  font-size: 11px;
  font-weight: 700;
}
.reasoning-step {
  display: flex;
  gap: 9px;
  position: relative;
  padding-bottom: 12px;
}
.reasoning-step:last-child {
  padding-bottom: 0;
}
.reasoning-step:not(:last-child)::before {
  content: "";
  position: absolute;
  top: 10px;
  bottom: 0;
  left: 3px;
  width: 1px;
  background: #dddddd;
}
.reasoning-step__dot {
  z-index: 1;
  width: 7px;
  height: 7px;
  margin-top: 5px;
  flex: 0 0 7px;
  border-radius: 50%;
  background: #2f2f2f;
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
  color: #494949;
  font-size: 12px;
  font-weight: 650;
}
.reasoning-step small {
  margin-top: 2px;
  color: #878787;
  font-size: 11px;
  line-height: 1.5;
}
.reasoning-step code {
  overflow: auto;
  max-width: 100%;
  margin-top: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  color: #3f3f3f;
  background: #f0f0f0;
  font:
    11px/1.5 ui-monospace,
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
.composer {
  padding: 9px 11px 8px;
  border: 1px solid #e1e1e1;
  border-radius: 25px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.055);
  transition:
    border-color 0.16s,
    box-shadow 0.16s;
}
.composer:focus-within {
  border-color: #c6c6c6;
  box-shadow: 0 3px 16px rgba(0, 0, 0, 0.09);
}
.composer__main {
  display: flex;
  min-height: 42px;
  align-items: center;
  gap: 7px;
}
.composer textarea {
  display: block;
  width: 100%;
  min-height: 26px;
  max-height: 130px;
  border: 0;
  outline: 0;
  padding: 6px 2px;
  resize: none;
  color: #242424;
  background: transparent;
  font: 15px/1.45 var(--font-sans);
}
.composer textarea::placeholder {
  color: #929292;
}
.composer__actions {
  display: flex;
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
.composer__mic {
  display: grid;
}
.database-picker {
  display: inline-flex;
  height: 34px;
  align-items: center;
  gap: 4px;
  border: 0;
  border-radius: 8px;
  padding: 0 5px;
  color: #777;
  font-size: 12px;
}
.database-picker:hover {
  background: #f5f5f5;
  color: #333;
}
.database-picker select {
  max-width: 78px;
  min-width: 32px;
  border: 0;
  outline: 0;
  color: inherit;
  background: transparent;
  font: inherit;
  cursor: pointer;
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
.composer__context {
  display: flex;
  align-items: center;
  padding: 3px 2px 0 41px;
}
.readonly-badge {
  display: inline-flex;
  height: 22px;
  align-items: center;
  gap: 5px;
  border-radius: 999px;
  padding: 0 7px;
  color: #668073;
  background: #f0f7f3;
  font-size: 10px;
}
.readonly-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #25a36f;
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
    min-height: min(470px, calc(100vh - 220px));
    padding-top: 0;
  }
  .empty-state h1 {
    font-size: 27px;
  }
  .empty-state p {
    max-width: 330px;
  }
  .suggestion-list {
    grid-template-columns: 1fr;
  }
  .message-list {
    padding-top: 16px;
  }
  .message-bubble {
    max-width: calc(100% - 42px);
  }
  .composer-wrap {
    width: calc(100% - 24px);
    padding-bottom: 12px;
  }
  .composer {
    border-radius: 20px;
  }
  .composer__context {
    padding-left: 39px;
  }
  .database-picker select {
    max-width: 50px;
  }
}
</style>
