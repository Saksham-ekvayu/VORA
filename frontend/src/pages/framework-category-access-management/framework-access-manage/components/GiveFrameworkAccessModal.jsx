/* eslint-disable react/prop-types */

import { useCallback } from "react";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import { assignFrameworkAccess } from "@/services/adminService";
import UserAvatar from "@/components/custom/UserAvatar";
import { ROLE_EXPERT } from "@/utils/commonUtils";
import {
  fetchUsersFn,
  fetchFrameworkCategoriesFn,
  DualSelectionModal,
} from "@/components/custom/modal";

export default function GiveFrameworkAccessModal({
  isOpen,
  onSuccess,
  onClose,
}) {
  const handleAssignAccess = useCallback(
    async (selectedUser, selectedFrameworks) => {
      const frameworkIds = selectedFrameworks.map((f) => f.id);
      const response = await assignFrameworkAccess(
        selectedUser.id,
        frameworkIds
      );
      toast.success(response.message);
      onSuccess?.();
    },
    [onSuccess]
  );

  const renderUserRow = useCallback(
    (user, selectedUser, handleUserSelect) => (
      <tr
        key={user.id}
        onClick={() => handleUserSelect(user)}
        className={`cursor-pointer transition-all duration-200 hover:bg-muted/80 ${
          selectedUser?.id === user.id
            ? "bg-primary/10 border-l-4 border-primary"
            : "border-l-4 border-transparent"
        }`}
      >
        <td className="px-3 py-2 w-[80%]">
          <div className="flex items-center gap-2">
            <UserAvatar user={user} size="sm" />
            <div className="flex flex-col">
              <span className="font-medium text-foreground text-sm line-clamp-1">
                {user.name}
              </span>
              <span className="text-xs text-muted-foreground">
                {user.email}
              </span>
            </div>
          </div>
        </td>
      </tr>
    ),
    []
  );

  const renderFrameworkRow = useCallback(
    (framework, selectedFrameworks, handleFrameworkSelect) => {
      const isSelected = selectedFrameworks.some((f) => f.id === framework.id);
      return (
        <tr
          key={framework.id}
          onClick={() => handleFrameworkSelect(framework)}
          className={`cursor-pointer transition-all duration-200 hover:bg-muted/50 ${
            isSelected
              ? "bg-primary/10 border-l-4 border-primary"
              : "border-l-4 border-transparent"
          }`}
        >
          <td className="px-3 py-2 align-top">
            <div className="flex items-start gap-2">
              <div className="w-7 h-7 rounded-full bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center border border-purple-200 dark:border-purple-800">
                <Icon
                  name="shield"
                  size="16px"
                  className="text-purple-600 dark:text-purple-400"
                />
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-foreground text-sm line-clamp-1">
                  {framework.frameworkCategoryName}
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  {framework.code}
                </span>
              </div>
            </div>
          </td>
          <td className="px-3 py-2 align-top">
            <span className="text-xs text-muted-foreground line-clamp-2 max-w-xs">
              {framework.description}
            </span>
          </td>
        </tr>
      );
    },
    []
  );

  const leftConfig = {
    title: "Select Expert",
    icon: "users",
    fetchFn: fetchUsersFn,
    extraParams: { role: ROLE_EXPERT },
    errorMessage: "Failed to load users",
    placeholder: "Search experts...",
    renderRow: renderUserRow,
    selectSingle: true,
  };

  const rightConfig = {
    title: "Select Active Framework Categories",
    icon: "shield",
    fetchFn: fetchFrameworkCategoriesFn,
    errorMessage: "Failed to load framework categories",
    placeholder: "Search frameworks...",
    renderRow: renderFrameworkRow,
  };

  return (
    <DualSelectionModal
      isOpen={isOpen}
      onClose={onClose}
      onSubmit={handleAssignAccess}
      title="Give Framework Access"
      description="Select an expert and one or more framework categories to assign access"
      icon="user-plus"
      actionLabel={(left, right) => `Assign Access (${right.length})`}
      savingLabel="Assigning..."
      leftConfig={leftConfig}
      rightConfig={rightConfig}
    />
  );
}
