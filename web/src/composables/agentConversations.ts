import { computed, inject, provide, ref, type ComputedRef, type InjectionKey, type Ref } from "vue";

import type { QueryResponse, QueryStreamEvent } from "@/types/api";

export const AGENT_CONVERSATIONS_STORAGE_KEY = "chain-nl2sql-agent-conversations-v1";

const STORAGE_VERSION = 1;
const DEFAULT_DATABASE_ID = "demo";
const DEFAULT_TITLE = "新聊天";

export interface AgentChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: QueryResponse;
  progress?: QueryStreamEvent[];
}

export interface AgentConversation {
  id: string;
  title: string;
  messages: AgentChatMessage[];
  draft: string;
  databaseId: string;
  createdAt: number;
  updatedAt: number;
}

interface StoredConversations {
  version: number;
  activeConversationId: string;
  conversations: AgentConversation[];
}

export interface AgentConversationStore {
  conversations: Ref<AgentConversation[]>;
  activeConversationId: Ref<string>;
  activeConversation: ComputedRef<AgentConversation>;
  recentConversations: ComputedRef<AgentConversation[]>;
  isBusy: Ref<boolean>;
  createConversation: () => void;
  selectConversation: (conversationId: string) => void;
  deleteConversation: (conversationId: string) => void;
  setDraft: (draft: string) => void;
  setDatabaseId: (databaseId: string) => void;
  appendMessage: (message: AgentChatMessage) => void;
  updateMessage: (messageId: string, update: (message: AgentChatMessage) => void) => void;
  setBusy: (busy: boolean) => void;
}

export const agentConversationStoreKey: InjectionKey<AgentConversationStore> =
  Symbol("agentConversationStore");

function createId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `conversation-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function createConversation(): AgentConversation {
  const now = Date.now();
  return {
    id: createId(),
    title: DEFAULT_TITLE,
    messages: [],
    draft: "",
    databaseId: DEFAULT_DATABASE_ID,
    createdAt: now,
    updatedAt: now,
  };
}

function isChatMessage(value: unknown): value is AgentChatMessage {
  if (!value || typeof value !== "object") return false;
  const message = value as Partial<AgentChatMessage>;
  return (
    typeof message.id === "string" &&
    (message.role === "user" || message.role === "assistant") &&
    typeof message.content === "string" &&
    (message.progress === undefined || Array.isArray(message.progress))
  );
}

function isConversation(value: unknown): value is AgentConversation {
  if (!value || typeof value !== "object") return false;
  const conversation = value as Partial<AgentConversation>;
  return (
    typeof conversation.id === "string" &&
    typeof conversation.title === "string" &&
    Array.isArray(conversation.messages) &&
    conversation.messages.every(isChatMessage) &&
    typeof conversation.draft === "string" &&
    typeof conversation.databaseId === "string" &&
    typeof conversation.createdAt === "number" &&
    typeof conversation.updatedAt === "number"
  );
}

function readStoredConversations(): StoredConversations | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(AGENT_CONVERSATIONS_STORAGE_KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as Partial<StoredConversations>;
    if (
      stored.version !== STORAGE_VERSION ||
      typeof stored.activeConversationId !== "string" ||
      !Array.isArray(stored.conversations) ||
      !stored.conversations.every(isConversation)
    ) {
      return null;
    }
    return stored as StoredConversations;
  } catch {
    return null;
  }
}

function titleForQuestion(question: string) {
  return question.trim().slice(0, 24) || DEFAULT_TITLE;
}

export function createAgentConversationStore(): AgentConversationStore {
  const stored = readStoredConversations();
  const initialConversations = stored?.conversations.length ? stored.conversations : [createConversation()];
  const conversations = ref(initialConversations);
  const activeConversationId = ref(
    stored && initialConversations.some((conversation) => conversation.id === stored.activeConversationId)
      ? stored.activeConversationId
      : initialConversations[0].id,
  );
  const isBusy = ref(false);

  const activeConversation = computed(() => {
    const conversation = conversations.value.find(
      (item) => item.id === activeConversationId.value,
    );
    if (conversation) return conversation;

    const fallback = createConversation();
    conversations.value.push(fallback);
    activeConversationId.value = fallback.id;
    return fallback;
  });
  const recentConversations = computed(() =>
    [...conversations.value].sort((left, right) => right.updatedAt - left.updatedAt),
  );

  function persist() {
    if (typeof window === "undefined") return;
    const payload: StoredConversations = {
      version: STORAGE_VERSION,
      activeConversationId: activeConversationId.value,
      conversations: conversations.value,
    };
    window.localStorage.setItem(AGENT_CONVERSATIONS_STORAGE_KEY, JSON.stringify(payload));
  }

  function touch(conversation: AgentConversation) {
    conversation.updatedAt = Date.now();
    persist();
  }

  function createNewConversation() {
    const current = activeConversation.value;
    if (!current.messages.length && !current.draft.trim()) return;

    const conversation = createConversation();
    conversations.value.push(conversation);
    activeConversationId.value = conversation.id;
    persist();
  }

  function selectConversation(conversationId: string) {
    if (isBusy.value || !conversations.value.some((conversation) => conversation.id === conversationId))
      return;
    activeConversationId.value = conversationId;
    persist();
  }

  function deleteConversation(conversationId: string) {
    if (isBusy.value) return;
    const index = conversations.value.findIndex((conversation) => conversation.id === conversationId);
    if (index === -1) return;

    const wasActive = activeConversationId.value === conversationId;
    conversations.value.splice(index, 1);
    if (!conversations.value.length) {
      const conversation = createConversation();
      conversations.value.push(conversation);
      activeConversationId.value = conversation.id;
    } else if (wasActive) {
      activeConversationId.value = recentConversations.value[0].id;
    }
    persist();
  }

  function setDraft(draft: string) {
    activeConversation.value.draft = draft;
    touch(activeConversation.value);
  }

  function setDatabaseId(databaseId: string) {
    activeConversation.value.databaseId = databaseId;
    touch(activeConversation.value);
  }

  function appendMessage(message: AgentChatMessage) {
    const conversation = activeConversation.value;
    conversation.messages.push(message);
    if (message.role === "user" && conversation.title === DEFAULT_TITLE && conversation.messages.length === 1) {
      conversation.title = titleForQuestion(message.content);
    }
    touch(conversation);
  }

  function updateMessage(messageId: string, update: (message: AgentChatMessage) => void) {
    const conversation = activeConversation.value;
    const message = conversation.messages.find((item) => item.id === messageId);
    if (!message) return;
    update(message);
    touch(conversation);
  }

  persist();

  return {
    conversations,
    activeConversationId,
    activeConversation,
    recentConversations,
    isBusy,
    createConversation: createNewConversation,
    selectConversation,
    deleteConversation,
    setDraft,
    setDatabaseId,
    appendMessage,
    updateMessage,
    setBusy: (busy) => {
      isBusy.value = busy;
    },
  };
}

export function provideAgentConversationStore() {
  const store = createAgentConversationStore();
  provide(agentConversationStoreKey, store);
  return store;
}

export function useAgentConversationStore() {
  const store = inject(agentConversationStoreKey);
  if (!store) throw new Error("Agent conversation store is not available.");
  return store;
}
