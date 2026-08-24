import { describe, expect, it } from "vitest";
import { authState } from "@/auth/auth";
import { usePermissions } from "@/composables/permissions";

describe("usePermissions", () => {
  it("maps a super administrator to management permissions", () => {
    authState.role = "super_admin";
    const permissions = usePermissions();

    expect(permissions.isSuperAdmin.value).toBe(true);
    expect(permissions.isReadOnly.value).toBe(false);
    expect(permissions.canManageDatabases.value).toBe(true);
    expect(permissions.canManageKnowledge.value).toBe(true);
    expect(permissions.canManageMembers.value).toBe(true);
    expect(permissions.roleLabel.value).toBe("超级管理员");
  });

  it("maps a regular member to read-only permissions", () => {
    authState.role = "member";
    const permissions = usePermissions();

    expect(permissions.isSuperAdmin.value).toBe(false);
    expect(permissions.isReadOnly.value).toBe(true);
    expect(permissions.canManageDatabases.value).toBe(false);
    expect(permissions.canManageKnowledge.value).toBe(false);
    expect(permissions.canManageMembers.value).toBe(false);
    expect(permissions.roleLabel.value).toBe("普通成员 · 只读");
  });
});
