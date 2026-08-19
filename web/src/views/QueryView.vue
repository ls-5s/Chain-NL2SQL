<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { Database, LoaderCircle, RotateCcw, Send, Sparkles, UserRound } from "lucide-vue-next";

import { fetchDatabases, streamQuery } from "@/api/client";
import type { QueryIntent, QueryResponse, QueryResult, QueryStatus, QueryStreamEvent } from "@/types/api";

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

function clearConversation() {
  messages.value = [];
  question.value = "";
}

function statusLabel(status: QueryStatus) {
  return { succeeded: "查询完成", blocked: "已拦截", failed: "执行失败", running: "处理中" }[status];
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
  return result.rows.map((row) => Object.fromEntries(result.columns.map((column, index) => [column, row[index]])));
}

async function scrollToBottom() {
  await nextTick();
  if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight;
}
</script>

<template>
  <section class="query-page">
    <header class="query-topbar">
      <div class="query-topbar__title">
        <span class="query-topbar__mark"><Sparkles :size="16" /></span>
        <span>Chain 查询</span>
      </div>
      <button v-if="messages.length" class="reset-button" type="button" title="新建对话" @click="clearConversation">
        <RotateCcw :size="16" />
        <span>新建对话</span>
      </button>
    </header>

    <div ref="conversation" class="conversation-panel" :class="{ 'conversation-panel--active': messages.length }">
      <div v-if="!messages.length" class="empty-state">
        <div class="empty-state__icon"><Sparkles :size="26" /></div>
        <h1>今天想查询什么？</h1>
        <p>查询演示数据或直接提问，系统会判断是否需要生成只读 SQL。</p>
        <div class="suggestion-list">
          <button type="button" @click="askQuestion('查询用户数量')">查询用户数量</button>
          <button type="button" @click="askQuestion('统计各类商品的销售情况')">统计各类商品的销售情况</button>
          <button type="button" @click="askQuestion('查询最近的订单')">查询最近的订单</button>
          <button type="button" @click="askQuestion('按订单状态统计订单数量')">按状态统计订单</button>
          <button type="button" @click="askQuestion('帮我写一封会议邀请邮件')">帮我写一封会议邀请邮件</button>
          <button type="button" @click="askQuestion('订单情况怎么样？')">订单情况怎么样？</button>
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
            <p v-if="message.role === 'user'">{{ message.content }}</p>

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

            <p v-if="message.role === 'assistant'" class="message-answer">{{ message.content }}</p>
            <span v-if="message.response && message.response.intent !== 'data_query'" :class="intentClass(message.response.intent)">
              {{ intentLabel(message.response.intent) }}
            </span>

            <div v-if="message.response?.intent === 'data_query'" class="response-card">
              <div class="response-card__header">
                <div class="response-card__title"><Database :size="16" />{{ databaseId }}</div>
                <span :class="statusClass(message.response.status)">{{ intentLabel(message.response.intent) }} · {{ statusLabel(message.response.status) }}</span>
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
        <textarea
          v-model="question"
          rows="1"
          maxlength="2000"
          placeholder="向 Chain 查询演示数据"
          aria-label="输入查询问题"
          @keydown.enter.exact.prevent="handleSubmit"
        />
        <div class="composer__footer">
          <div class="composer__context">
            <span class="readonly-badge"><span class="readonly-dot" />只读模式</span>
            <label class="database-picker">
              <Database :size="14" />
              <span class="sr-only">选择数据源</span>
              <select v-model="databaseId" :disabled="loading" aria-label="选择数据源">
                <option v-for="database in databases" :key="database" :value="database">{{ database }}</option>
              </select>
            </label>
          </div>
          <button class="send-button" type="submit" :disabled="!canSubmit" aria-label="发送查询">
            <LoaderCircle v-if="loading" class="spin" :size="17" />
            <Send v-else :size="17" />
          </button>
        </div>
      </form>
      <p class="composer-note">Chain 可能会出错，请核对重要结果。</p>
    </footer>
  </section>
</template>

<style scoped>
.query-page { display: flex; height: calc(100vh - 68px); min-height: 0; flex-direction: column; overflow: hidden; background: #ffffff; color: #242424; }
.query-topbar { display: flex; height: 58px; flex: 0 0 58px; align-items: center; justify-content: space-between; padding: 0 clamp(18px, 3vw, 44px); }
.query-topbar__title { display: flex; align-items: center; gap: 9px; font-size: 15px; font-weight: 650; }
.query-topbar__mark { display: grid; width: 27px; height: 27px; place-items: center; border-radius: 8px; color: #ffffff; background: #1f2933; }
.reset-button { display: inline-flex; height: 32px; align-items: center; gap: 7px; border: 1px solid #e5e5e5; border-radius: 7px; padding: 0 10px; color: #555; background: #fff; font-size: 12px; cursor: pointer; }
.reset-button:hover { background: #f7f7f7; color: #1f1f1f; }
.conversation-panel { width: 100%; min-height: 0; flex: 1 1 auto; overflow: auto; padding: 0 18px 20px; scrollbar-width: none; -ms-overflow-style: none; }
.conversation-panel::-webkit-scrollbar { display: none; width: 0; height: 0; }
.conversation-panel--active { max-width: 900px; margin: 0 auto; }
.empty-state { display: flex; min-height: min(510px, calc(100vh - 250px)); flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.empty-state__icon { display: grid; width: 54px; height: 54px; margin-bottom: 18px; place-items: center; border-radius: 16px; color: #fff; background: #1f2933; }
.empty-state h1 { margin: 0; color: #202020; font-size: 30px; font-weight: 650; letter-spacing: 0; }
.empty-state p { max-width: 480px; margin: 11px 0 25px; color: #777; font-size: 14px; line-height: 1.6; }
.suggestion-list { display: grid; width: min(580px, 100%); grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.suggestion-list button { min-height: 44px; border: 1px solid #e5e5e5; border-radius: 9px; padding: 10px 13px; color: #424242; background: #fff; font: inherit; font-size: 13px; text-align: left; cursor: pointer; transition: background .15s, border-color .15s; }
.suggestion-list button:hover { border-color: #cfcfcf; background: #f8f8f8; }
.message-list { display: flex; flex-direction: column; gap: 25px; width: 100%; padding: 22px 0 140px; }
.message-row { display: flex; gap: 12px; align-items: flex-start; }
.message-row--user { flex-direction: row-reverse; }
.message-avatar { display: grid; width: 30px; height: 30px; flex: 0 0 30px; place-items: center; border-radius: 50%; color: #fff; background: #343434; }
.message-row--assistant .message-avatar { color: #fff; background: #1f2933; }
.message-bubble { max-width: min(720px, calc(100% - 44px)); color: #303030; font-size: 14px; line-height: 1.7; }
.message-row--user .message-bubble { text-align: right; }
.message-meta { display: none; }
.message-bubble > p { display: inline-block; margin: 0; border-radius: 18px; padding: 10px 14px; background: #f1f1f1; text-align: left; }
.message-row--assistant .message-bubble > p { border-radius: 4px; padding: 2px 0; background: transparent; }
.message-answer { margin-top: 14px !important; color: #303030; }
.message-row--user .message-bubble > p { border-bottom-right-radius: 4px; }
.intent-pill { display: inline-block; margin-top: 8px; border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 700; }
.intent-pill--general_chat { color: #486bb1; background: #eaf1ff; }.intent-pill--clarification { color: #a06a16; background: #fff2d9; }
.message-bubble--loading { padding: 4px 0; color: #777; }
.loading-dots { color: #333; }
.reasoning-timeline { margin-top: 14px; padding: 12px 13px; border: 1px solid #e7e7e7; border-radius: 8px; background: #fafafa; text-align: left; }
.reasoning-timeline__title { margin-bottom: 11px; color: #5e5e5e; font-size: 11px; font-weight: 700; }
.reasoning-step { display: flex; gap: 9px; position: relative; padding-bottom: 12px; }
.reasoning-step:last-child { padding-bottom: 0; }
.reasoning-step:not(:last-child)::before { content: ""; position: absolute; top: 10px; bottom: 0; left: 3px; width: 1px; background: #dddddd; }
.reasoning-step__dot { z-index: 1; width: 7px; height: 7px; margin-top: 5px; flex: 0 0 7px; border-radius: 50%; background: #2f2f2f; }
.reasoning-step__body { min-width: 0; }
.reasoning-step strong, .reasoning-step small, .reasoning-step code { display: block; }
.reasoning-step strong { color: #494949; font-size: 12px; font-weight: 650; }
.reasoning-step small { margin-top: 2px; color: #878787; font-size: 11px; line-height: 1.5; }
.reasoning-step code { overflow: auto; max-width: 100%; margin-top: 6px; padding: 6px 8px; border-radius: 6px; color: #3f3f3f; background: #f0f0f0; font: 11px/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; word-break: break-word; }
.response-card { margin-top: 14px; overflow: hidden; border: 1px solid #e4e4e4; border-radius: 9px; background: #fff; text-align: left; }
.response-card__header, .response-card__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; }
.response-card__header { border-bottom: 1px solid #ededed; }
.response-card__title { display: flex; gap: 7px; align-items: center; color: #555; font-size: 12px; font-weight: 700; }
.status-pill { border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 700; }
.status-pill--succeeded { color: #18855c; background: #e7f7ef; }.status-pill--blocked { color: #b46615; background: #fff3dc; }.status-pill--failed { color: #c04855; background: #ffebed; }.status-pill--running { color: #6356c8; background: #eeeaff; }
.result-table { width: 100%; }
.result-empty { padding: 24px 14px; color: #9da2af; font-size: 13px; }
.response-card__footer { color: #8a8a8a; font-size: 12px; }
.composer-wrap { z-index: 2; flex: 0 0 auto; width: min(760px, calc(100% - 36px)); margin: auto; padding: 16px 0 18px; background: linear-gradient(to bottom, rgba(255, 255, 255, 0), #fff 30%); }
.composer { padding: 12px; border: 1px solid #d9d9d9; border-radius: 14px; background: #fff; box-shadow: 0 6px 22px rgba(0, 0, 0, .08); }
.composer:focus-within { border-color: #aaaaaa; box-shadow: 0 6px 22px rgba(0, 0, 0, .11); }
.composer textarea { display: block; width: 100%; min-height: 28px; max-height: 160px; border: 0; outline: 0; padding: 3px 2px 7px; resize: none; color: #242424; background: transparent; font: 14px/1.55 var(--font-sans); }
.composer textarea::placeholder { color: #999; }
.composer__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.composer__context { display: flex; min-width: 0; align-items: center; gap: 8px; }
.readonly-badge, .database-picker { display: inline-flex; height: 27px; align-items: center; gap: 5px; border-radius: 6px; color: #6b6b6b; font-size: 11px; }
.readonly-badge { padding: 0 7px; background: #f5f5f5; }
.readonly-dot { width: 6px; height: 6px; border-radius: 50%; background: #1f8c62; }
.database-picker { border: 1px solid #e6e6e6; padding: 0 7px; color: #555; }
.database-picker select { min-width: 54px; border: 0; outline: 0; color: inherit; background: transparent; font: inherit; cursor: pointer; }
.send-button { display: grid; width: 30px; height: 30px; flex: 0 0 30px; place-items: center; border: 0; border-radius: 8px; color: #fff; background: #212121; cursor: pointer; }
.send-button:hover:not(:disabled) { background: #000; }
.send-button:disabled { color: #aaa; background: #ededed; cursor: default; }
.composer-note { margin: 8px 0 0; color: #949494; font-size: 11px; text-align: center; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 700px) { .query-topbar { padding-inline: 16px; }.reset-button span { display: none; }.conversation-panel { padding-inline: 14px; }.empty-state { min-height: min(470px, calc(100vh - 220px)); }.empty-state h1 { font-size: 26px; }.suggestion-list { grid-template-columns: 1fr; }.message-list { padding-top: 16px; }.message-bubble { max-width: calc(100% - 42px); }.composer-wrap { width: calc(100% - 24px); padding-bottom: 12px; }.readonly-badge { display: none; } }
</style>
