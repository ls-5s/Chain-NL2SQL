<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { Database, LoaderCircle, Send, Sparkles, UserRound } from "lucide-vue-next";

import { fetchDatabases, streamQuery } from "@/api/client";
import type { QueryResponse, QueryResult, QueryStatus, QueryStreamEvent } from "@/types/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: QueryResponse;
  progress?: QueryStreamEvent[];
}

const question = ref("");
const databaseId = ref("demo");
const databases = ref<string[]>([]);
  const loading = ref(false);
const messages = ref<ChatMessage[]>([]);
const conversation = ref<HTMLElement | null>(null);
const agentStep = ref("正在准备查询");

const canSubmit = computed(() => question.value.trim().length > 0 && !loading.value);

onMounted(async () => {
  try {
    databases.value = await fetchDatabases();
    databaseId.value = databases.value[0] || "demo";
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "无法加载数据库列表");
  }
});

async function askQuestion(value = question.value) {
  const text = value.trim();
  if (!text || loading.value) return;

  question.value = "";
  messages.value.push({ id: crypto.randomUUID(), role: "user", content: text });
  const assistantMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "正在准备查询",
    progress: [],
  };
  messages.value.push(assistantMessage);
  loading.value = true;
  agentStep.value = "正在连接查询 Agent";
  await scrollToBottom();

  try {
    const response = await streamQuery(
      { question: text, database_id: databaseId.value },
      (event) => {
        if (event.message) {
          agentStep.value = event.message;
          assistantMessage.content = event.message;
        }
        if (event.node) assistantMessage.progress?.push(event);
      },
    );
    assistantMessage.content = response.final_answer;
    assistantMessage.response = response;
  } catch (error) {
    assistantMessage.content = error instanceof Error ? error.message : "查询服务暂时不可用，请稍后重试。";
  } finally {
    loading.value = false;
    agentStep.value = "正在准备查询";
    await scrollToBottom();
  }
}

function handleSubmit() {
  void askQuestion();
}

function statusLabel(status: QueryStatus) {
  return { succeeded: "查询完成", blocked: "已拦截", failed: "执行失败", running: "处理中" }[status];
}

function statusClass(status: QueryStatus) {
  return `status-pill status-pill--${status}`;
}

function resultColumns(result: QueryResult) {
  return result.columns.map((label) => ({ label, prop: label }));
}

function resultRows(response: QueryResponse) {
  const result = response.result;
  if (!result) return [];
  return result.rows.map((row) => Object.fromEntries(result.columns.map((column, index) => [column, row[index]])));
}

async function scrollToBottom() {
  await nextTick();
  if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight;
}
</script>

<template>
  <section class="query-page">
    <header class="query-page__header">
      <div>
        <p class="eyebrow">NATURAL LANGUAGE QUERY</p>
        <h1>数据问答工作区</h1>
        <p class="query-page__subtitle">用自然语言提问，Agent 会读取 Schema、生成只读 SQL 并返回结果。</p>
      </div>
      <div class="query-page__controls">
        <span class="control-label">数据源</span>
        <el-select v-model="databaseId" size="large" :disabled="loading" aria-label="选择数据源">
          <el-option v-for="database in databases" :key="database" :label="database" :value="database" />
        </el-select>
      </div>
    </header>

    <div ref="conversation" class="conversation-panel">
      <div v-if="!messages.length" class="empty-state">
        <div class="empty-state__icon"><Sparkles :size="22" /></div>
        <h2>从一个业务问题开始</h2>
        <p>试试询问销售、订单或用户数据。当前 Agent 默认使用只读模式。</p>
        <div class="suggestion-list">
          <button @click="askQuestion('查询用户数量')">查询用户数量</button>
          <button @click="askQuestion('统计各类商品的销售情况')">统计各类商品的销售情况</button>
          <button @click="askQuestion('查询最近的订单')">查询最近的订单</button>
        </div>
      </div>

      <div v-else class="message-list">
        <article v-for="message in messages" :key="message.id" class="message-row" :class="`message-row--${message.role}`">
          <div class="message-avatar">
            <UserRound v-if="message.role === 'user'" :size="17" />
            <Sparkles v-else :size="17" />
          </div>
          <div class="message-bubble">
            <div class="message-meta">{{ message.role === "user" ? "你" : "Chain Agent" }}</div>
            <p>{{ message.content }}</p>

            <div v-if="message.progress?.length" class="reasoning-timeline">
              <div class="reasoning-timeline__title">执行过程</div>
              <div v-for="step in message.progress" :key="`${step.node}-${step.iteration}`" class="reasoning-step">
                <span class="reasoning-step__dot" />
                <div class="reasoning-step__body">
                  <strong>{{ step.message }}</strong>
                  <small>{{ step.explanation }}</small>
                  <code v-if="step.sql">{{ step.sql }}</code>
                </div>
              </div>
            </div>

            <div v-if="message.response" class="response-card">
              <div class="response-card__header">
                <div class="response-card__title"><Database :size="16" />{{ databaseId }}</div>
                <span :class="statusClass(message.response.status)">{{ statusLabel(message.response.status) }}</span>
              </div>
              <el-table
                v-if="message.response.result?.rows.length"
                :data="resultRows(message.response)"
                size="small"
                stripe
                class="result-table"
              >
                <el-table-column v-for="column in resultColumns(message.response.result)" :key="column.prop" v-bind="column" min-width="130" />
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
          <div class="message-bubble message-bubble--loading">{{ agentStep }}<span class="loading-dots">...</span></div>
        </div>
      </div>
    </div>

    <footer class="composer-wrap">
      <form class="composer" @submit.prevent="handleSubmit">
        <el-input v-model="question" type="textarea" :rows="2" resize="none" maxlength="2000" show-word-limit placeholder="例如：查询用户数量" @keydown.enter.exact.prevent="handleSubmit" />
        <div class="composer__footer">
          <span><span class="readonly-dot" />只读查询模式</span>
          <el-button type="primary" :loading="loading" :disabled="!canSubmit" native-type="submit">
            <Send :size="16" />发送
          </el-button>
        </div>
      </form>
    </footer>

  </section>
</template>

<style scoped>
.query-page { display: flex; flex-direction: column; min-height: calc(100vh - 72px); padding: 34px clamp(20px, 4vw, 64px) 28px; background: #f7f8fb; }
.query-page__header { display: flex; justify-content: space-between; gap: 28px; align-items: flex-end; max-width: 1180px; width: 100%; margin: 0 auto 24px; }
.eyebrow { margin: 0 0 8px; color: #6c5ce7; font-size: 11px; font-weight: 700; letter-spacing: .14em; }
h1 { margin: 0; color: #1b2030; font-size: clamp(24px, 3vw, 34px); letter-spacing: -.04em; }
.query-page__subtitle { margin: 9px 0 0; color: #7c8291; font-size: 14px; }
.query-page__controls { display: flex; flex-direction: column; gap: 7px; width: 180px; flex-shrink: 0; }
.control-label { color: #8b91a0; font-size: 12px; font-weight: 600; }
.conversation-panel { flex: 1; overflow: auto; max-width: 1180px; width: 100%; margin: 0 auto; padding: 20px 4px 28px; }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 370px; text-align: center; }
.empty-state__icon { display: grid; place-items: center; width: 48px; height: 48px; margin-bottom: 18px; border-radius: 16px; color: #6c5ce7; background: #ebe8ff; }
.empty-state h2 { margin: 0; color: #24283a; font-size: 22px; }
.empty-state p { max-width: 420px; margin: 10px 0 22px; color: #8a90a0; font-size: 14px; line-height: 1.7; }
.suggestion-list { display: flex; flex-wrap: wrap; justify-content: center; gap: 9px; }
.suggestion-list button { border: 1px solid #e3e5ec; border-radius: 10px; padding: 9px 13px; color: #636a7c; background: white; cursor: pointer; font: inherit; font-size: 12px; }
.suggestion-list button:hover { border-color: #b7adff; color: #5a4bc9; }
.message-list { display: flex; flex-direction: column; gap: 24px; max-width: 880px; margin: 0 auto; }
.message-row { display: flex; gap: 12px; align-items: flex-start; }
.message-row--user { flex-direction: row-reverse; }
.message-avatar { display: grid; place-items: center; width: 32px; height: 32px; flex: 0 0 32px; border-radius: 11px; color: #656b7c; background: #e9ebf2; }
.message-row--assistant .message-avatar { color: #6c5ce7; background: #e9e6ff; }
.message-bubble { max-width: min(760px, 84%); color: #303646; font-size: 14px; line-height: 1.65; }
.message-row--user .message-bubble { text-align: right; }
.message-meta { margin: 2px 0 5px; color: #969baa; font-size: 11px; font-weight: 600; }
.message-bubble > p { display: inline-block; margin: 0; padding: 11px 14px; border-radius: 4px 14px 14px 14px; background: white; box-shadow: 0 4px 16px rgba(35, 40, 62, .04); }
.message-row--user .message-bubble > p { border-radius: 14px 4px 14px 14px; color: white; background: #6858dc; }
.message-bubble--loading { padding: 11px 14px; border-radius: 4px 14px 14px 14px; background: white; color: #8b91a0; }
.loading-dots { color: #6c5ce7; }
.reasoning-timeline { margin-top: 12px; padding: 13px 14px; border: 1px solid #ececf3; border-radius: 12px; background: #fbfbfd; text-align: left; }
.reasoning-timeline__title { margin-bottom: 11px; color: #6f7585; font-size: 11px; font-weight: 700; }
.reasoning-step { display: flex; gap: 9px; position: relative; padding-bottom: 12px; }
.reasoning-step:last-child { padding-bottom: 0; }
.reasoning-step:not(:last-child)::before { content: ""; position: absolute; top: 10px; bottom: 0; left: 3px; width: 1px; background: #dedff0; }
.reasoning-step__dot { z-index: 1; width: 7px; height: 7px; margin-top: 5px; flex: 0 0 7px; border-radius: 50%; background: #7567e8; }
.reasoning-step__body { min-width: 0; }
.reasoning-step strong, .reasoning-step small, .reasoning-step code { display: block; }
.reasoning-step strong { color: #596073; font-size: 12px; font-weight: 650; }
.reasoning-step small { margin-top: 2px; color: #9499a8; font-size: 11px; line-height: 1.5; }
.reasoning-step code { overflow: auto; max-width: 100%; margin-top: 6px; padding: 6px 8px; border-radius: 6px; color: #5f579b; background: #f0effc; font: 11px/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; word-break: break-word; }
.response-card { margin-top: 12px; overflow: hidden; border: 1px solid #e7e8ef; border-radius: 14px; background: white; box-shadow: 0 8px 24px rgba(35, 40, 62, .05); text-align: left; }
.response-card__header, .response-card__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; }
.response-card__header { border-bottom: 1px solid #f0f1f5; }
.response-card__title { display: flex; gap: 7px; align-items: center; color: #545b6e; font-size: 12px; font-weight: 700; }
.status-pill { border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 700; }
.status-pill--succeeded { color: #18855c; background: #e7f7ef; }.status-pill--blocked { color: #b46615; background: #fff3dc; }.status-pill--failed { color: #c04855; background: #ffebed; }.status-pill--running { color: #6356c8; background: #eeeaff; }
.result-table { width: 100%; }
.result-empty { padding: 24px 14px; color: #9da2af; font-size: 13px; }
.response-card__footer { color: #9b9fac; font-size: 12px; }
.composer-wrap { max-width: 880px; width: 100%; margin: auto; }
.composer { padding: 10px; border: 1px solid #dedfea; border-radius: 16px; background: white; box-shadow: 0 10px 28px rgba(35, 40, 62, .07); }
.composer :deep(.el-textarea__inner) { border: 0; padding: 7px 8px; box-shadow: none; color: #323749; }
.composer__footer { display: flex; align-items: center; justify-content: space-between; padding: 5px 5px 0 8px; color: #9a9eaa; font-size: 11px; }
.composer__footer span { display: flex; align-items: center; gap: 6px; }.readonly-dot { width: 6px; height: 6px; border-radius: 50%; background: #36b37e; }
.composer__footer :deep(.el-button) { display: inline-flex; align-items: center; gap: 7px; border-radius: 9px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 700px) { .query-page { padding: 24px 14px 18px; }.query-page__header { align-items: stretch; flex-direction: column; gap: 17px; }.query-page__controls { width: 100%; }.message-bubble { max-width: 90%; }.empty-state { min-height: 310px; }.suggestion-list { flex-direction: column; }.suggestion-list button { width: 100%; } }
</style>
