import { computed, inject, provide, ref, type ComputedRef, type InjectionKey, type Ref } from "vue";

import {
  createConversation as createConversationRequest,
  deleteConversation as deleteConversationRequest,
  fetchConversation,
  fetchConversations,
  streamConversationQuery,
} from "@/api/client";
import type { ConversationDetail, ConversationMessage, ConversationSummary, QueryResponse, QueryStreamEvent } from "@/types/api";

const DEFAULT_DATABASE_ID = "demo";

export interface AgentChatMessage extends ConversationMessage {}

export interface AgentConversation {
  id: string;
  title: string;
  messages: AgentChatMessage[];
  draft: string;
  databaseId: string;
  createdAt: string;
  updatedAt: string;
}

export interface AgentConversationStore {
  conversations: Ref<ConversationSummary[]>;
  activeConversationId: Ref<string>;
  activeConversation: ComputedRef<AgentConversation>;
  recentConversations: ComputedRef<ConversationSummary[]>;
  isBusy: Ref<boolean>;
  initializationError: Ref<string | null>;
  initialize: () => Promise<void>;
  createConversation: (databaseId?: string) => Promise<void>;
  selectConversation: (conversationId: string) => Promise<void>;
  deleteConversation: (conversationId: string) => Promise<void>;
  setDraft: (draft: string) => void;
  setDatabaseId: (databaseId: string) => void;
  sendQuestion: (question: string, onProgress: (event: QueryStreamEvent) => void, referenceIds?: string[]) => Promise<void>;
}

export const agentConversationStoreKey: InjectionKey<AgentConversationStore> = Symbol("agentConversationStore");

function mapConversation(detail: ConversationDetail, draft = ""): AgentConversation {
  return {
    id: detail.id,
    title: detail.title,
    messages: detail.messages,
    draft,
    databaseId: detail.database_id,
    createdAt: detail.created_at,
    updatedAt: detail.updated_at,
  };
}

export function createAgentConversationStore(): AgentConversationStore {
  const conversations = ref<ConversationSummary[]>([]);
  const activeConversationId = ref("");
  const activeDetail = ref<ConversationDetail | null>(null);
  const draft = ref("");
  const isBusy = ref(false);
  const initializationError = ref<string | null>(null);
  const activeConversation = computed<AgentConversation>(() =>
    activeDetail.value
      ? mapConversation(activeDetail.value, draft.value)
      : { id: "", title: "新聊天", messages: [], draft: draft.value, databaseId: DEFAULT_DATABASE_ID, createdAt: "", updatedAt: "" },
  );
  const recentConversations = computed(() => conversations.value);

  async function refreshList() {
    conversations.value = await fetchConversations();
  }

  async function loadConversation(conversationId: string) {
    activeDetail.value = await fetchConversation(conversationId);
    activeConversationId.value = conversationId;
    draft.value = "";
  }

  async function createConversationInternal(databaseId = DEFAULT_DATABASE_ID) {
    const created = await createConversationRequest(databaseId);
    await refreshList();
    await loadConversation(created.id);
  }

  async function initialize() {
    if (isBusy.value) return;
    isBusy.value = true;
    initializationError.value = null;
    try {
      await refreshList();
      if (conversations.value.length) await loadConversation(conversations.value[0].id);
      else await createConversationInternal(DEFAULT_DATABASE_ID);
    } catch (error) {
      initializationError.value = error instanceof Error ? error.message : "无法加载会话，请重试。";
    } finally {
      isBusy.value = false;
    }
  }

  async function createConversation(databaseId = DEFAULT_DATABASE_ID) {
    if (isBusy.value) return;
    isBusy.value = true;
    try {
      await createConversationInternal(databaseId);
    } finally {
      isBusy.value = false;
    }
  }

  async function selectConversation(conversationId: string) {
    if (isBusy.value || conversationId === activeConversationId.value) return;
    isBusy.value = true;
    try {
      await loadConversation(conversationId);
    } finally {
      isBusy.value = false;
    }
  }

  async function deleteConversation(conversationId: string) {
    if (isBusy.value) return;
    isBusy.value = true;
    try {
      await deleteConversationRequest(conversationId);
      await refreshList();
      if (!conversations.value.length) {
        activeConversationId.value = "";
        activeDetail.value = null;
        await createConversationInternal(DEFAULT_DATABASE_ID);
      }
      else if (activeConversationId.value === conversationId) await loadConversation(conversations.value[0].id);
    } finally {
      isBusy.value = false;
    }
  }

  function setDraft(value: string) {
    draft.value = value;
  }

  function setDatabaseId(databaseId: string) {
    if (activeDetail.value?.messages.length) return;
    if (activeDetail.value) activeDetail.value.database_id = databaseId;
  }

  async function sendQuestion(question: string, onProgress: (event: QueryStreamEvent) => void, referenceIds: string[] = []) {
    const conversationId = activeConversationId.value;
    if (!conversationId || isBusy.value) return;
    isBusy.value = true;
    const existing = activeDetail.value;
    const timestamp = new Date().toISOString();
    if (existing) {
      existing.messages.push(
        { id: `local-user-${Date.now()}`, turn_id: "", role: "user", content: question, status: "succeeded", progress: [], created_at: timestamp },
        { id: `local-assistant-${Date.now()}`, turn_id: "", role: "assistant", content: "正在准备查询", status: "running", progress: [], created_at: timestamp },
      );
    }
    draft.value = "";
    let response: QueryResponse | null = null;
    try {
      response = await streamConversationQuery(conversationId, { question, reference_ids: referenceIds }, (event) => {
        const assistant = activeDetail.value?.messages.at(-1);
        if (assistant?.role === "assistant") {
          if (event.message) assistant.content = event.message;
          if (event.node) assistant.progress.push(event);
        }
        onProgress(event);
      });
      const assistant = activeDetail.value?.messages.at(-1);
      if (assistant?.role === "assistant") {
        assistant.content = response.final_answer;
        assistant.status = response.status;
        assistant.response = response;
      }
      await refreshList();
      await loadConversation(conversationId);
    } catch (error) {
      if (!response) {
        const assistant = activeDetail.value?.messages.at(-1);
        if (assistant?.role === "assistant") {
          assistant.status = "failed";
          assistant.content = error instanceof Error ? error.message : "查询未完成。";
        }
      }
      throw error;
    } finally {
      isBusy.value = false;
    }
  }

  return {
    conversations,
    activeConversationId,
    activeConversation,
    recentConversations,
    isBusy,
    initializationError,
    initialize,
    createConversation,
    selectConversation,
    deleteConversation,
    setDraft,
    setDatabaseId,
    sendQuestion,
  };
}

export function provideAgentConversationStore() {
  const store = createAgentConversationStore();
  provide(agentConversationStoreKey, store);
  void store.initialize();
  return store;
}

export function useAgentConversationStore() {
  const store = inject(agentConversationStoreKey);
  if (!store) throw new Error("Agent conversation store is not available.");
  return store;
}
