import axios, { AxiosError } from "axios";

import type {
  ApprovalItem,
  ApprovalStatus,
  DatabaseListResponse,
  KnowledgeDocument,
  QueryRequest,
  QueryResponse,
} from "@/types/api";

const client = axios.create({ baseURL: "/api/v1", timeout: 20_000 });

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

export async function submitQuery(payload: QueryRequest): Promise<QueryResponse> {
  try {
    const { data } = await client.post<QueryResponse>("/query", payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
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

