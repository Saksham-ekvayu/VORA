/* eslint-disable react/prop-types */
import { useState, useEffect, useCallback } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useModalState } from "@/hooks/useModalState";
import {
  useModalPaginatedList,
  ModalTableBody,
  ModalTablePagination,
  ModalSearchInput,
  ModalHeader,
  ModalFooter,
} from "./index";
import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";

/**
 * DualSelectionModal - Generic two-column picker component
 *
 * @param {boolean} isOpen - Dialog state
 * @param {Function} onClose - Dialog close handler
 * @param {Function} onSubmit - Form submit handler (receives selectedLeft and selectedRight)
 * @param {string} title - Title of the modal
 * @param {string} description - Subtitle/description of the modal
 * @param {string} icon - Header icon name
 * @param {string|Function} actionLabel - Text to display on submit button. Can be a function: (left, right) => string
 * @param {string} savingLabel - Text to display when saving
 * @param {string} actionIcon - Icon for submit button
 * @param {Object} leftConfig - Config for the left column:
 *    { title, icon, fetchFn, extraParams, errorMessage, placeholder, renderRow, selectSingle }
 * @param {Object} rightConfig - Config for the right column:
 *    { title, icon, fetchFn, extraParams, errorMessage, placeholder, renderRow }
 */
export default function DualSelectionModal({
  isOpen,
  onClose,
  onSubmit,
  title,
  description,
  icon = "shield",
  actionLabel = "Submit",
  savingLabel = "Saving...",
  actionIcon = "check",
  leftConfig = {},
  rightConfig = {},
}) {
  const {
    title: leftTitle,
    icon: leftIcon = "users",
    fetchFn: leftFetchFn,
    extraParams: leftExtraParams,
    errorMessage: leftErrorMessage = "Failed to load items",
    placeholder: leftPlaceholder = "Search...",
    renderRow: leftRenderRow,
    selectSingle = false,
  } = leftConfig;

  const {
    title: rightTitle,
    icon: rightIcon = "shield",
    fetchFn: rightFetchFn,
    extraParams: rightExtraParams,
    errorMessage: rightErrorMessage = "Failed to load items",
    placeholder: rightPlaceholder = "Search...",
    renderRow: rightRenderRow,
  } = rightConfig;

  const [selectedLeft, setSelectedLeft] = useState(selectSingle ? null : []);
  const [selectedRight, setSelectedRight] = useState([]);
  const { loading: saving, setLoading: setSaving } = useModalState();

  const leftList = useModalPaginatedList(leftFetchFn, {
    limit: 5,
    enabled: isOpen,
    extraParams: leftExtraParams,
    errorMessage: leftErrorMessage,
  });

  const rightList = useModalPaginatedList(rightFetchFn, {
    limit: 5,
    enabled: isOpen,
    extraParams: rightExtraParams,
    errorMessage: rightErrorMessage,
  });

  // Reset selections when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedLeft(selectSingle ? null : []);
      setSelectedRight([]);
    }
  }, [isOpen, selectSingle]);

  const handleLeftSelect = useCallback(
    (item) => {
      setSelectedLeft((prev) => {
        if (selectSingle) {
          return prev?.id === item.id ? null : item;
        } else {
          const exists = prev.some((x) => x.id === item.id);
          return exists
            ? prev.filter((x) => x.id !== item.id)
            : [...prev, item];
        }
      });
    },
    [selectSingle]
  );

  const handleRightSelect = useCallback((item) => {
    setSelectedRight((prev) => {
      const exists = prev.some((x) => x.id === item.id);
      return exists ? prev.filter((x) => x.id !== item.id) : [...prev, item];
    });
  }, []);

  const handleActionSubmit = async () => {
    const hasLeftSelection = selectSingle
      ? !!selectedLeft
      : selectedLeft.length > 0;
    if (!hasLeftSelection || selectedRight.length === 0) return;

    setSaving(true);
    try {
      await onSubmit(selectedLeft, selectedRight);
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const isActionDisabled = selectSingle
    ? !selectedLeft || selectedRight.length === 0
    : selectedLeft.length === 0 || selectedRight.length === 0;

  const dynamicActionLabel =
    typeof actionLabel === "function"
      ? actionLabel(selectedLeft, selectedRight)
      : actionLabel;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="lg:max-w-4xl">
        <ModalHeader icon={icon} title={title} description={description} />

        <div className="p-4 overflow-y-auto max-h-[calc(90vh-160px)]">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left Column */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                  <Icon name={leftIcon} size="16px" className="text-primary" />
                  {leftTitle}
                </h3>
                {selectSingle
                  ? selectedLeft && (
                      <span className="text-xs text-green-800 bg-green-100 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full font-medium">
                        Selected: {selectedLeft.name}
                      </span>
                    )
                  : selectedLeft.length > 0 && (
                      <span className="text-xs text-green-800 bg-green-100 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full font-medium">
                        Selected: {selectedLeft.length} customer
                        {selectedLeft.length === 1 ? "" : "s"}
                      </span>
                    )}
              </div>
              <div className="border border-border rounded bg-background">
                <div className="p-3 border-b border-border bg-muted/30">
                  <ModalSearchInput
                    value={leftList.searchTerm}
                    onChange={leftList.setSearchTerm}
                    placeholder={leftPlaceholder}
                  />
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted/80 border-b border-border">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider w-3/5">
                          Framework Experts
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      <ModalTableBody
                        loading={leftList.loading}
                        items={leftList.items}
                        renderRow={(item) =>
                          leftRenderRow(item, selectedLeft, handleLeftSelect)
                        }
                        emptyMessage="No items found"
                      />
                    </tbody>
                  </table>
                </div>
                {!leftList.loading && leftList.items.length > 0 && (
                  <ModalTablePagination
                    pagination={leftList.pagination}
                    onPageChange={leftList.onPageChange}
                  />
                )}
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                  <Icon name={rightIcon} size="16px" className="text-primary" />
                  {rightTitle}
                </h3>
                {selectedRight.length > 0 && (
                  <div className="text-xs text-green-800 bg-green-100 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
                    <Icon name="check-circle" size="12px" />
                    Selected: {selectedRight.length} framework
                    {selectedRight.length === 1 ? "" : "s"}
                  </div>
                )}
              </div>
              <div className="border border-border rounded overflow-hidden bg-background">
                <div className="p-3 border-b border-border bg-muted/30">
                  <div className="flex gap-2">
                    <ModalSearchInput
                      value={rightList.searchTerm}
                      onChange={rightList.setSearchTerm}
                      placeholder={rightPlaceholder}
                    />
                    {rightList.items.length > 0 && (
                      <div className="flex gap-1">
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() =>
                            setSelectedRight((prev) => {
                              const selectedIds = new Set(
                                prev.map((item) => item.id)
                              );
                              const newItems = rightList.items.filter(
                                (item) => !selectedIds.has(item.id)
                              );
                              return [...prev, ...newItems];
                            })
                          }
                          title="Select All"
                        >
                          <Icon name="check" size="15px" />
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => setSelectedRight([])}
                          title="Clear All"
                        >
                          <Icon name="close" size="15px" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted/80 border-b border-border">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Name/Code
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      <ModalTableBody
                        loading={rightList.loading}
                        items={rightList.items}
                        renderRow={(item) =>
                          rightRenderRow(item, selectedRight, handleRightSelect)
                        }
                        emptyMessage="No items found"
                      />
                    </tbody>
                  </table>
                </div>
                {!rightList.loading && rightList.items.length > 0 && (
                  <ModalTablePagination
                    pagination={rightList.pagination}
                    onPageChange={rightList.onPageChange}
                  />
                )}
              </div>
            </div>
          </div>
        </div>

        <ModalFooter
          onCancel={onClose}
          onSubmit={handleActionSubmit}
          isSaving={saving}
          savingLabel={savingLabel}
          actionLabel={dynamicActionLabel}
          actionIcon={actionIcon}
          actionType="button"
          isActionDisabled={isActionDisabled}
        />
      </DialogContent>
    </Dialog>
  );
}
