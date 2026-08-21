import { computed, inject, provide, ref, type ComputedRef, type InjectionKey, type Ref } from "vue";

import {
  createConversation as createConversationRequest,
  deleteConversation as deleteConversationRequest,
  fetchConversation,
  fetchConversations,
  streamConversationQuery,
} from "@/api/client";
import type { ConversationDetail, ConversationMessage, ConversationSummary, QueryStreamEvent } from "@/types/api";

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

  async function initialize() {
    if (isBusy.value) return;
    isBusy.value = true;
    try {
      await refreshList();
      if (conversations.value.length) await loadConversation(conversations.value[0].id);
      else await createConversation(DEFAULT_DATABASE_ID);
    } finally {
      isBusy.value = false;
    }
  }

  async function createConversation(databaseId = DEFAULT_DATABASE_ID) {
    if (isBusy.value && activeConversationId.value) return;
    const created = await createConversationRequest(databaseId);
    await refreshList();
    await loadConversation(created.id);
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
        await createConversation(DEFAULT_DATABASE_ID);
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
    if (!activeConversationId.value || isBusy.value) return;
    isBusy.value = true;
    const existing = activeDetail.value;
    const hasHistory = Boolean(existing?.messages.length);
    if (existing && hasHistory) {
      existing.messages.push(
        { id: `local-user-${Date.now()}`, turn_id: "", role: "user", content: question, status: "succeeded", progress: [], created_at: new Date().toISOString() },
        { id: `local-assistant-${Date.now()}`, turn_id: "", role: "assistant", content: "正在准备查询", status: "running", progress: [], created_at: new Date().toISOString() },
      );
    }
    draft.value = "";
    try {
      await streamConversationQuery(activeConversationId.value, { question, reference_ids: referenceIds }, (event) => {
        if (hasHistory) {
          const assistant = activeDetail.value?.messages.at(-1);
          if (assistant?.role === "assistant") {
            if (event.message) assistant.content = event.message;
            if (event.node) assistant.progress.push(event);
          }
        }
        onProgress(event);
      });
      await refreshList();
      await loadConversation(activeConversationId.value);
    } finally {
      isBusy.value = false;
    }
  }

  return { conversations, activeConversationId, activeConversation, recentConversations, isBusy, initialize, createConversation, selectConversation, deleteConversation, setDraft, setDatabaseId, sendQuestion };
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
