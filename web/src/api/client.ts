import axios, { AxiosError } from "axios";

import type {
  ApprovalItem,
  ApprovalStatus,
  DatabaseListResponse,
  KnowledgeDocument,
  QueryRequest,
  QueryResponse,
  QueryStreamEvent,
  ConversationDetail,
  ConversationSummary,
  LoginRequest,
  ResultReferenceResponse,
  SessionResponse,
} from "@/types/api";

const client = axios.create({ baseURL: "/api/v1", timeout: 20_000, withCredentials: true });

export class ApiRequestError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
  }
}

function toApiError(error: unknown): ApiRequestError {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    return new ApiRequestError(typeof detail === "string" ? detail : "请求未能完成。", error.response?.status);
  }
  return new ApiRequestError("无法连接到服务，请确认后端已启动。");
}

export async function fetchDatabases(): Promise<string[]> {
  try {
    const { data } = await client.get<DatabaseListResponse>("/databases");
    return data.database_ids;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function loginSession(payload: LoginRequest): Promise<SessionResponse> {
  try {
    const { data } = await client.post<SessionResponse>("/auth/login", payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function logoutSession(): Promise<void> {
  try {
    await client.post("/auth/logout");
  } catch (error) {
    throw toApiError(error);
  }
}

export async function fetchSession(): Promise<SessionResponse> {
  try {
    const { data } = await client.get<SessionResponse>("/auth/session");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function fetchConversations(): Promise<ConversationSummary[]> {
  try {
    const { data } = await client.get<ConversationSummary[]>("/conversations");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function createConversation(databaseId: string): Promise<ConversationSummary> {
  try {
    const { data } = await client.post<ConversationSummary>("/conversations", { database_id: databaseId });
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function fetchConversation(conversationId: string): Promise<ConversationDetail> {
  try {
    const { data } = await client.get<ConversationDetail>(`/conversations/${conversationId}`);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function deleteConversation(conversationId: string): Promise<void> {
  try {
    await client.delete(`/conversations/${conversationId}`);
  } catch (error) {
    throw toApiError(error);
  }
}

export async function createResultReference(
  conversationId: string,
  turnId: string,
  rowIndex: number,
): Promise<ResultReferenceResponse> {
  try {
    const { data } = await client.post<ResultReferenceResponse>(`/conversations/${conversationId}/references`, {
      turn_id: turnId,
      row_index: rowIndex,
    });
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function submitQuery(payload: QueryRequest): Promise<QueryResponse> {
  try {
    const { data } = await client.post<QueryResponse>("/query", payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function streamQuery(
  payload: QueryRequest,
  onProgress: (event: QueryStreamEvent) => void,
): Promise<QueryResponse> {
  let response: Response;
  try {
    response = await fetch("/api/v1/query", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      credentials: "include",
      body: JSON.stringify(payload),
    });
  } catch {
    throw new ApiRequestError("无法连接到服务，请确认后端已启动。");
  }

  if (!response.ok) {
    let detail = "请求未能完成。";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the generic error when the server did not return JSON.
    }
    throw new ApiRequestError(detail, response.status);
  }
  if (!response.body) throw new ApiRequestError("服务未返回 SSE 数据流。", response.status);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed: QueryResponse | null = null;
  const consume = (chunk: string) => {
    buffer += chunk;
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const eventName = frame.match(/^event:\s*(.+)$/m)?.[1];
      const dataLine = frame.match(/^data:\s*(.+)$/m)?.[1];
      if (!eventName || !dataLine) continue;
      const data = JSON.parse(dataLine) as QueryStreamEvent & QueryResponse;
      if (eventName === "progress" || eventName === "start") onProgress(data);
      if (eventName === "complete") completed = data as QueryResponse;
      if (eventName === "error") throw new ApiRequestError(data.detail || "查询服务暂时不可用。", data.status_code);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    consume(decoder.decode(value, { stream: true }));
  }
  consume(decoder.decode());
  if (!completed) throw new ApiRequestError("查询流未返回最终结果。", response.status);
  return completed;
}

export async function streamConversationQuery(
  conversationId: string,
  payload: { question: string; max_iterations?: number; reference_ids?: string[] },
  onProgress: (event: QueryStreamEvent) => void,
): Promise<QueryResponse> {
  return streamSse(`/api/v1/conversations/${conversationId}/query`, payload, onProgress);
}

async function streamSse(
  url: string,
  payload: object,
  onProgress: (event: QueryStreamEvent) => void,
): Promise<QueryResponse> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      credentials: "include",
      body: JSON.stringify(payload),
    });
  } catch {
    throw new ApiRequestError("无法连接到服务，请确认后端已启动。");
  }
  if (!response.ok) {
    let detail = "请求未能完成。";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the generic error when the server did not return JSON.
    }
    throw new ApiRequestError(detail, response.status);
  }
  if (!response.body) throw new ApiRequestError("服务未返回 SSE 数据流。", response.status);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed: QueryResponse | null = null;
  const consume = (chunk: string) => {
    buffer += chunk;
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const eventName = frame.match(/^event:\s*(.+)$/m)?.[1];
      const dataLine = frame.match(/^data:\s*(.+)$/m)?.[1];
      if (!eventName || !dataLine) continue;
      const data = JSON.parse(dataLine) as QueryStreamEvent & QueryResponse;
      if (eventName === "progress" || eventName === "start") onProgress(data);
      if (eventName === "complete") completed = data as QueryResponse;
      if (eventName === "error") throw new ApiRequestError(data.detail || "查询服务暂时不可用。", data.status_code);
    }
  };
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    consume(decoder.decode(value, { stream: true }));
  }
  consume(decoder.decode());
  if (!completed) throw new ApiRequestError("查询流未返回最终结果。", response.status);
  return completed;
}

export async function fetchApprovals(): Promise<ApprovalItem[]> {
  try {
    const { data } = await client.get<ApprovalItem[]>("/approvals");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function resolveApproval(id: string, status: Extract<ApprovalStatus, "approved" | "rejected">): Promise<ApprovalItem> {
  try {
    const { data } = await client.post<ApprovalItem>(`/approvals/${id}/resolve`, { status });
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function fetchKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  try {
    const { data } = await client.get<KnowledgeDocument[]>("/knowledge");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function uploadKnowledgeDocument(file: File, category: string): Promise<KnowledgeDocument> {
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);
    const { data } = await client.post<KnowledgeDocument>("/knowledge", formData);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function deleteKnowledgeDocument(id: string): Promise<void> {
  try {
    await client.delete(`/knowledge/${id}`);
  } catch (error) {
    throw toApiError(error);
  }
}

