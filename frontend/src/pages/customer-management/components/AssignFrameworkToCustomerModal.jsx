/* eslint-disable react/prop-types */
import { useState, useCallback } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useModalState } from "@/hooks/useModalState";
import {
  useModalPaginatedList,
  ModalTableBody,
  ModalTablePagination,
  ModalSearchInput,
  ModalHeader,
  ModalFooter,
  fetchApprovedFrameworksFn,
} from "@/components/custom/modal";
import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";
import { assignFrameworksToCustomers } from "@/services/adminService";

export default function AssignFrameworkToCustomerModal({
  isOpen,
  onClose,
  onSuccess,
  customer,
}) {
  const [selectedFrameworks, setSelectedFrameworks] = useState([]);
  const { loading: saving, setLoading: setSaving } = useModalState();

  const rightList = useModalPaginatedList(fetchApprovedFrameworksFn, {
    limit: 5,
    enabled: isOpen,
    errorMessage: "Failed to load approved frameworks",
  });

  const handleFrameworkSelect = useCallback((framework) => {
    setSelectedFrameworks((prev) => {
      const exists = prev.some((f) => f.id === framework.id);
      return exists
        ? prev.filter((f) => f.id !== framework.id)
        : [...prev, framework];
    });
  }, []);

  const handleAssignFrameworks = async () => {
    if (selectedFrameworks.length === 0 || !customer) return;

    setSaving(true);
    try {
      const frameworkIds = selectedFrameworks.map((f) => f.id);
      const res = await assignFrameworksToCustomers(
        customer.id,
        customer.tenantId,
        frameworkIds
      );
      toast.success(res.message);
      onSuccess?.();
    } catch (err) {
      toast.error(err.message);
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const isActionDisabled = selectedFrameworks.length === 0;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="lg:max-w-xl">
        <ModalHeader
          icon="shield"
          title="Assign Frameworks"
          description={`Select approved frameworks to assign to ${
            customer?.name || "the customer"
          }`}
        />

        <div className="p-4 overflow-y-auto max-h-[calc(90vh-160px)]">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Icon
                  name="check-circle"
                  size="16px"
                  className="text-primary"
                />
                Select Approved Frameworks
              </h3>
              {selectedFrameworks.length > 0 && (
                <div className="text-xs text-green-800 bg-green-100 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
                  <Icon name="check-circle" size="12px" />
                  Selected: {selectedFrameworks.length}
                </div>
              )}
            </div>
            <div className="border border-border rounded overflow-hidden bg-background">
              <div className="p-3 border-b border-border bg-muted/30">
                <div className="flex gap-2">
                  <ModalSearchInput
                    value={rightList.searchTerm}
                    onChange={rightList.setSearchTerm}
                    placeholder="Search frameworks..."
                    loading={rightList.loading}
                  />
                  {rightList.items.length > 0 && (
                    <div className="flex gap-1">
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          setSelectedFrameworks((prev) => {
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
                        onClick={() => setSelectedFrameworks([])}
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
                  <tbody
                    className={`divide-y divide-border transition-opacity duration-200 ${
                      rightList.loading && rightList.items.length > 0
                        ? "opacity-50 pointer-events-none"
                        : "opacity-100"
                    }`}
                  >
                    <ModalTableBody
                      loading={rightList.loading}
                      items={rightList.items}
                      renderRow={(framework) => {
                        const isSelected = selectedFrameworks.some(
                          (f) => f.id === framework.id
                        );
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
                                <div className="w-7 h-7 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center border border-green-200 dark:border-green-800">
                                  <Icon
                                    name="check-circle"
                                    size="16px"
                                    className="text-green-600 dark:text-green-400"
                                  />
                                </div>
                                <div className="flex flex-col min-w-0">
                                  <span className="font-medium text-foreground text-sm line-clamp-1">
                                    {framework.frameworkName}
                                  </span>
                                  <span className="text-xs text-muted-foreground font-mono">
                                    {framework.frameworkCode} version:
                                    {framework.frameworkVersion}
                                  </span>
                                </div>
                              </div>
                            </td>
                          </tr>
                        );
                      }}
                      emptyMessage="No items found"
                    />
                  </tbody>
                </table>
              </div>
              {rightList.items.length > 0 && (
                <ModalTablePagination
                  pagination={rightList.pagination}
                  onPageChange={rightList.onPageChange}
                  loading={rightList.loading}
                />
              )}
            </div>
          </div>
        </div>

        <ModalFooter
          onCancel={onClose}
          onSubmit={handleAssignFrameworks}
          isSaving={saving}
          savingLabel="Assigning..."
          actionLabel={`Assign Frameworks (${selectedFrameworks.length})`}
          actionIcon="check"
          actionType="button"
          isActionDisabled={isActionDisabled}
        />
      </DialogContent>
    </Dialog>
  );
}
