import { defineStore } from "pinia";
import { fetchDatabases, submitQuery } from "@/api/client";
import type { QueryResponse } from "@/types/api";

export const useQueryStore = defineStore("query", {
  state: () => ({ question: "", databaseId: "", databases: [] as string[], isLoading: false, errorMessage: null as string | null, response: null as QueryResponse | null }),
  getters: { canSubmit: (state) => state.question.trim().length > 0 && !state.isLoading },
  actions: {
    async loadDatabases() { try { this.databases = await fetchDatabases(); this.databaseId ||= this.databases[0] ?? ""; } catch (error) { this.errorMessage = error instanceof Error ? error.message : "Unable to load databases."; } },
    async runQuery() { if (!this.canSubmit) return; this.isLoading = true; this.errorMessage = null; this.response = null; try { this.response = await submitQuery({ question: this.question.trim(), database_id: this.databaseId }); } catch (error) { this.errorMessage = error instanceof Error ? error.message : "Query request failed."; } finally { this.isLoading = false; } },
    reset() { this.question = ""; this.errorMessage = null; this.response = null; },
  },
});
