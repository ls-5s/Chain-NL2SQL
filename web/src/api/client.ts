import axios, { AxiosError } from "axios";

import {
  mockApprovals,
  mockDatabases,
  mockDeleteKnowledge,
  mockKnowledgeDocuments,
  mockQuery,
  mockResolveApproval,
  mockUploadKnowledge,
} from "@/api/mock";
import type {
  ApprovalItem,
  ApprovalStatus,
  DatabaseListResponse,
  KnowledgeDocument,
  QueryRequest,
  QueryResponse,
} from "@/types/api";

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 20_000,
});
const useMockApi = import.meta.env.VITE_USE_MOCK_API !== "false";

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
  }
}

function toApiError(error: unknown): ApiRequestError {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    return new ApiRequestError(
      typeof detail === "string" ? detail : "请求未能完成。",
      error.response?.status,
    );
  }
  return new ApiRequestError("无法连接到服务。请确认后端已启动。");
}

export async function fetchDatabases(): Promise<string[]> {
  try {
    if (useMockApi) return mockDatabases();
    const { data } = await client.get<DatabaseListResponse>("/databases");
    return data.database_ids;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function submitQuery(payload: QueryRequest): Promise<QueryResponse> {
  try {
    if (useMockApi) return mockQuery(payload);
    const { data } = await client.post<QueryResponse>("/query", payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function fetchApprovals(): Promise<ApprovalItem[]> {
  if (useMockApi) return mockApprovals();
  throw new ApiRequestError("当前后端尚未提供审批接口。");
}

export async function resolveApproval(
  id: string,
  status: Extract<ApprovalStatus, "approved" | "rejected">,
): Promise<ApprovalItem> {
  if (useMockApi) return mockResolveApproval(id, status);
  throw new ApiRequestError("当前后端尚未提供审批接口。");
}

export async function fetchKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  if (useMockApi) return mockKnowledgeDocuments();
  throw new ApiRequestError("当前后端尚未提供知识库接口。");
}

export async function uploadKnowledgeDocument(
  file: File,
  category: string,
): Promise<KnowledgeDocument> {
  if (useMockApi) return mockUploadKnowledge(file, category);
  throw new ApiRequestError("当前后端尚未提供知识库接口。");
}

export async function deleteKnowledgeDocument(id: string): Promise<void> {
  if (useMockApi) return mockDeleteKnowledge(id);
  throw new ApiRequestError("当前后端尚未提供知识库接口。");
}
