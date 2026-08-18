import { defineStore } from "pinia";
import { fetchApprovals, resolveApproval } from "@/api/client";
import type { ApprovalItem, ApprovalStatus } from "@/types/api";

export const useApprovalStore = defineStore("approval", {
  state: () => ({ items: [] as ApprovalItem[], isLoading: false, errorMessage: null as string | null }),
  actions: {
    async load() { this.isLoading = true; try { this.items = await fetchApprovals(); } catch (error) { this.errorMessage = error instanceof Error ? error.message : "Unable to load approvals."; } finally { this.isLoading = false; } },
    async decide(id: string, status: Extract<ApprovalStatus, "approved" | "rejected">) { try { const resolved = await resolveApproval(id, status); const index = this.items.findIndex((item) => item.id === id); if (index >= 0) this.items.splice(index, 1, resolved); } catch (error) { this.errorMessage = error instanceof Error ? error.message : "Approval action failed."; } },
  },
});
