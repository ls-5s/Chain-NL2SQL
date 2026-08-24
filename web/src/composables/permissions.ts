import { computed } from "vue";
import { authState } from "@/auth/auth";

export function usePermissions() {
  const isSuperAdmin = computed(() => authState.role === "super_admin");
  const isReadOnly = computed(() => !isSuperAdmin.value);

  return {
    isSuperAdmin,
    isReadOnly,
    canManageDatabases: isSuperAdmin,
    canManageKnowledge: isSuperAdmin,
    canManageMembers: isSuperAdmin,
    roleLabel: computed(() => (isSuperAdmin.value ? "超级管理员" : "普通成员 · 只读")),
  };
}
