import { defineStore } from "pinia";
import { deleteKnowledgeDocument, fetchKnowledgeDocuments, uploadKnowledgeDocument } from "@/api/client";
import type { KnowledgeDocument } from "@/types/api";
const acceptedExtensions = new Set(["txt", "md", "pdf", "docx", "csv"]);
export const useKnowledgeStore = defineStore("knowledge", {
  state: () => ({ items: [] as KnowledgeDocument[], isLoading: false, errorMessage: null as string | null }),
  actions: {
    async load() { this.isLoading = true; try { this.items = await fetchKnowledgeDocuments(); } catch (error) { this.errorMessage = error instanceof Error ? error.message : "Unable to load knowledge documents."; } finally { this.isLoading = false; } },
    async upload(file: File, category: string) { const extension = file.name.split(".").pop()?.toLowerCase(); if (!extension || !acceptedExtensions.has(extension)) { this.errorMessage = "仅支持 TXT、Markdown、PDF、DOCX 和 CSV 文件。"; return false; } try { const document = await uploadKnowledgeDocument(file, category); this.items.unshift(document); return true; } catch (error) { this.errorMessage = error instanceof Error ? error.message : "Upload failed."; return false; } },
    async remove(id: string) { await deleteKnowledgeDocument(id); this.items = this.items.filter((item) => item.id !== id); },
  },
});
