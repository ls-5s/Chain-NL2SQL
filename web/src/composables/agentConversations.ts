import { computed, inject, provide, ref, type ComputedRef, type InjectionKey, type Ref } from "vue";

import {
  createConversation as createConversationRequest,
  deleteConversation as deleteConversationRequest,
  fetchConversation,
  fetchConversations,
  streamConversationQuery,
} from "@/api/client";
import type {
  ConversationDetail,
  ConversationMessage,
  ConversationSummary,
  QueryResponse,
  QueryStreamEvent,
} from "@/types/api";

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
  canCreateConversation: ComputedRef<boolean>;
  recentConversations: ComputedRef<ConversationSummary[]>;
  isBusy: ComputedRef<boolean>;
  isMutating: Ref<boolean>;
  isConversationBusy: (conversationId: string) => boolean;
  initializationError: Ref<string | null>;
  initialize: () => Promise<void>;
  createConversation: (databaseId?: string) => Promise<void>;
  selectConversation: (conversationId: string) => Promise<void>;
  deleteConversation: (conversationId: string) => Promise<void>;
  setDraft: (draft: string) => void;
  setDatabaseId: (databaseId: string) => void;
  sendQuestion: (
    question: string,
    onProgress: (event: QueryStreamEvent) => void,
    referenceIds?: string[],
  ) => Promise<void>;
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
  const conversationDetails = ref<Record<string, ConversationDetail>>({});
  const drafts = ref<Record<string, string>>({});
  const busyConversationIds = ref<Record<string, boolean>>({});
  const isMutating = ref(false);
  const initializationError = ref<string | null>(null);
  let selectionRequest = 0;

  function isConversationBusy(conversationId: string) {
    return Boolean(busyConversationIds.value[conversationId]);
  }

  const isBusy = computed(() => isConversationBusy(activeConversationId.value));
  const activeDetail = computed(() => conversationDetails.value[activeConversationId.value]);
  const activeConversation = computed<AgentConversation>(() =>
    activeDetail.value
      ? mapConversation(activeDetail.value, drafts.value[activeConversationId.value] ?? "")
      : {
          id: "",
          title: "新聊天",
          messages: [],
          draft: drafts.value[activeConversationId.value] ?? "",
          databaseId: DEFAULT_DATABASE_ID,
          createdAt: "",
          updatedAt: "",
        },
  );
  const canCreateConversation = computed(() => activeConversation.value.messages.length > 0);
  const recentConversations = computed(() => conversations.value);

  function setConversationBusy(conversationId: string, busy: boolean) {
    const next = { ...busyConversationIds.value };
    if (busy) next[conversationId] = true;
    else delete next[conversationId];
    busyConversationIds.value = next;
  }

  async function refreshList() {
    conversations.value = await fetchConversations();
  }

  async function loadConversation(conversationId: string, activate = true) {
    const detail = await fetchConversation(conversationId);
    conversationDetails.value = { ...conversationDetails.value, [conversationId]: detail };
    if (drafts.value[conversationId] === undefined) {
      drafts.value = { ...drafts.value, [conversationId]: "" };
    }
    if (activate) activeConversationId.value = conversationId;
  }

  async function createConversationInternal(databaseId = DEFAULT_DATABASE_ID) {
    const created = await createConversationRequest(databaseId);
    await refreshList();
    await loadConversation(created.id);
  }

  async function initialize() {
    if (isMutating.value) return;
    isMutating.value = true;
    initializationError.value = null;
    try {
      await refreshList();
      if (conversations.value.length) await loadConversation(conversations.value[0].id);
      else await createConversationInternal(DEFAULT_DATABASE_ID);
    } catch (error) {
      initializationError.value = error instanceof Error ? error.message : "无法加载会话，请重试。";
    } finally {
      isMutating.value = false;
    }
  }

  async function createConversation(databaseId = DEFAULT_DATABASE_ID) {
    if (isMutating.value || isBusy.value) return;
    isMutating.value = true;
    try {
      await createConversationInternal(databaseId);
    } finally {
      isMutating.value = false;
    }
  }

  async function selectConversation(conversationId: string) {
    if (conversationId === activeConversationId.value) return;
    const requestId = ++selectionRequest;
    if (conversationDetails.value[conversationId]) {
      activeConversationId.value = conversationId;
      if (drafts.value[conversationId] === undefined) {
        drafts.value = { ...drafts.value, [conversationId]: "" };
      }
      return;
    }

    const detail = await fetchConversation(conversationId);
    conversationDetails.value = { ...conversationDetails.value, [conversationId]: detail };
    if (drafts.value[conversationId] === undefined) {
      drafts.value = { ...drafts.value, [conversationId]: "" };
    }
    if (requestId === selectionRequest) activeConversationId.value = conversationId;
  }

  async function deleteConversation(conversationId: string) {
    if (isMutating.value || isConversationBusy(conversationId)) return;
    isMutating.value = true;
    try {
      await deleteConversationRequest(conversationId);
      const nextDetails = { ...conversationDetails.value };
      const nextDrafts = { ...drafts.value };
      delete nextDetails[conversationId];
      delete nextDrafts[conversationId];
      conversationDetails.value = nextDetails;
      drafts.value = nextDrafts;
      await refreshList();

      if (!conversations.value.length) {
        activeConversationId.value = "";
        await createConversationInternal(DEFAULT_DATABASE_ID);
      } else if (activeConversationId.value === conversationId) {
        const replacement = conversations.value.find((conversation) => !isConversationBusy(conversation.id));
        if (replacement) await loadConversation(replacement.id);
        else await createConversationInternal(DEFAULT_DATABASE_ID);
      }
    } finally {
      isMutating.value = false;
    }
  }

  function setDraft(value: string) {
    const conversationId = activeConversationId.value;
    if (!conversationId) return;
    drafts.value = { ...drafts.value, [conversationId]: value };
  }

  function setDatabaseId(databaseId: string) {
    if (activeDetail.value?.messages.length) return;
    if (activeDetail.value) activeDetail.value.database_id = databaseId;
  }

  async function sendQuestion(
    question: string,
    onProgress: (event: QueryStreamEvent) => void,
    referenceIds: string[] = [],
  ) {
    const conversationId = activeConversationId.value;
    const existing = conversationDetails.value[conversationId];
    if (!conversationId || !existing || isConversationBusy(conversationId)) return;

    setConversationBusy(conversationId, true);
    const timestamp = new Date().toISOString();
    existing.messages.push(
      {
        id: `local-user-${Date.now()}`,
        turn_id: "",
        role: "user",
        content: question,
        status: "succeeded",
        progress: [],
        created_at: timestamp,
      },
      {
        id: `local-assistant-${Date.now()}`,
        turn_id: "",
        role: "assistant",
        content: "正在准备查询",
        status: "running",
        progress: [],
        created_at: timestamp,
      },
    );
    drafts.value = { ...drafts.value, [conversationId]: "" };
    const assistant = existing.messages.at(-1);
    let response: QueryResponse | null = null;

    try {
      response = await streamConversationQuery(
        conversationId,
        { question, reference_ids: referenceIds },
        (event) => {
          if (assistant?.role === "assistant") {
            if (event.message) assistant.content = event.message;
            if (event.node) assistant.progress.push(event);
          }
          onProgress(event);
        },
      );
      if (assistant?.role === "assistant") {
        assistant.content = response.final_answer;
        assistant.status = response.status;
        assistant.response = response;
      }
      await refreshList();
      await loadConversation(conversationId, false);
    } catch (error) {
      if (!response && assistant?.role === "assistant") {
        assistant.status = "failed";
        assistant.content = error instanceof Error ? error.message : "查询未完成。";
      }
      throw error;
    } finally {
      setConversationBusy(conversationId, false);
    }
  }

  return {
    conversations,
    activeConversationId,
    activeConversation,
    canCreateConversation,
    recentConversations,
    isBusy,
    isMutating,
    isConversationBusy,
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
