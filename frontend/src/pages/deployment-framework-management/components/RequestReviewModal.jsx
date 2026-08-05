/* eslint-disable react/prop-types */

import { useState, useCallback, useEffect } from "react";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import UserAvatar from "@/components/custom/UserAvatar";
import { requestExpertReview } from "@/services/deploymentFrameworkService";
import { getAllUsers } from "@/services/userService";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useModalState } from "@/hooks/useModalState";
import { ROLE_INTERNAL_EXPERT } from "@/utils/commonUtils";
import {
  useModalPaginatedList,
  ModalTableBody,
  ModalTablePagination,
  ModalSearchInput,
  ModalFooter,
  ModalHeader,
} from "@/components/custom/modal";

/**
 * Stable fetch wrapper for internal experts (active users with ROLE_INTERNAL_EXPERT).
 */
async function fetchInternalExpertsFn({ page, limit, search }) {
  const res = await getAllUsers({
    page,
    limit,
    search,
    role: ROLE_INTERNAL_EXPERT,
    isActive: true,
  });
  if (!res?.success)
    throw new Error(res?.message || "Failed to load internal experts");

  const data = (res.data || []).map((user) => ({
    id: user._id || user.id,
    name: user.name,
    email: user.email,
    role: user.role,
    avatar: user.avatar,
    status: user.isActive ? "active" : "inactive",
  }));

  return { data, pagination: res.pagination };
}

export default function RequestReviewModal({
  frameworkId,
  frameworkName,
  packageVersion,
  onSuccess,
  onClose,
  isOpen,
}) {
  const [selectedExpert, setSelectedExpert] = useState(null);
  const { loading: requesting, setLoading: setRequesting } = useModalState();

  const internalList = useModalPaginatedList(fetchInternalExpertsFn, {
    enabled: isOpen,
    errorMessage: "Failed to load internal experts",
  });

  const handleSearch = useCallback(
    (term) => {
      internalList.setSearchTerm(term);
    },
    [internalList]
  );

  // Reset selection when modal closes
  useEffect(() => {
    if (!isOpen) setSelectedExpert(null);
  }, [isOpen]);

  const handleExpertSelect = useCallback((expert) => {
    setSelectedExpert((prev) => (prev?.id === expert.id ? null : expert));
  }, []);

  const handleRequestReview = async () => {
    setRequesting(true);
    try {
      const response = await requestExpertReview(frameworkId, {
        expertId: selectedExpert.id,
        packageVersion,
      });
      toast.success(response.message);
      onSuccess?.();
      onClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRequesting(false);
    }
  };

  const renderExpertRow = useCallback(
    (expert) => (
      <tr
        key={expert.id}
        onClick={() => handleExpertSelect(expert)}
        className={`cursor-pointer transition-all duration-200 hover:bg-muted/80 ${
          selectedExpert?.id === expert.id
            ? "bg-primary/10 border-l-4 border-primary"
            : "border-l-4 border-transparent"
        }`}
      >
        <td className="px-3 py-2">
          <div className="flex items-center gap-2">
            <UserAvatar user={{ name: expert.name, avatar: expert.avatar }} />
            <div className="flex flex-col">
              <span className="font-medium text-foreground text-sm line-clamp-1">
                {expert.name}
              </span>
              <span className="text-xs text-muted-foreground">
                {expert.email}
              </span>
            </div>
          </div>
        </td>
      </tr>
    ),
    [selectedExpert, handleExpertSelect]
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="lg:max-w-lg">
        <ModalHeader
          icon="user-check"
          title="Request Expert Review"
          description={`Select an expert to review: ${frameworkName}`}
        />

        <div className="flex flex-col gap-3 p-2">
          <div className="flex items-center justify-between gap-3">
            <ModalSearchInput
              value={internalList.searchTerm}
              onChange={handleSearch}
              onClear={() => handleSearch("")}
              placeholder="Search experts..."
              className="max-w-full"
            />
            {selectedExpert && (
              <span className="text-xs text-green-800 bg-green-100 dark:bg-green-900/30 dark:text-green-400 px-3 py-2 rounded font-medium shadow-sm flex items-center gap-2 shrink-0">
                <Icon name="check-circle" size="14px" />
                Selected: {selectedExpert.name}
              </span>
            )}
          </div>

          {/* Internal Experts List only */}
          <div className="flex flex-col border border-border rounded bg-background overflow-hidden flex-1">
            <div className="px-3 py-2 bg-muted/60 border-b border-border flex items-center gap-2">
              <Icon
                name="briefcase"
                size="15px"
                className="text-blue-600 dark:text-blue-400"
              />
              <h3 className="text-sm font-semibold text-foreground">
                Select an Internal Expert
              </h3>
            </div>
            <div className="overflow-x-auto flex-1">
              <table className="w-full">
                <tbody className="divide-y divide-border">
                  <ModalTableBody
                    loading={internalList.loading}
                    items={internalList.items}
                    renderRow={renderExpertRow}
                    emptyMessage="No experts found"
                    colSpan={1}
                    loadingLabel="Loading experts..."
                  />
                </tbody>
              </table>
            </div>
            {!internalList.loading && internalList.items.length > 0 && (
              <ModalTablePagination
                pagination={internalList.pagination}
                onPageChange={internalList.onPageChange}
              />
            )}
          </div>
        </div>

        <ModalFooter
          onCancel={onClose}
          onSubmit={handleRequestReview}
          isSaving={requesting}
          isActionDisabled={!selectedExpert}
          actionLabel="Request Review"
          savingLabel="Requesting..."
          actionIcon="check"
          actionType="button"
        />
      </DialogContent>
    </Dialog>
  );
}
