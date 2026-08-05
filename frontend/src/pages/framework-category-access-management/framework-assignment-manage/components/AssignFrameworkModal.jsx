/* eslint-disable react/prop-types */

import { useCallback } from "react";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import { assignFrameworksToCustomers } from "@/services/adminService";
import UserAvatar from "@/components/custom/UserAvatar";
import { ROLE_CUSTOMER_ADMIN } from "@/utils/commonUtils";
import {
  fetchCustomersFn,
  fetchApprovedFrameworksFn,
  DualSelectionModal,
} from "@/components/custom/modal";

export default function AssignFrameworkModal({ isOpen, onSuccess, onClose }) {
  const handleAssignFrameworks = useCallback(
    async (selectedCustomers, selectedFrameworks) => {
      const frameworkIds = selectedFrameworks.map((f) => f.id);
      await Promise.all(
        selectedCustomers.map(async (customer) => {
          try {
            const res = await assignFrameworksToCustomers(
              customer.id,
              customer.tenantId,
              frameworkIds
            );
            toast.success(res.message);
          } catch (err) {
            toast.error(err.message);
            console.error(err);
          }
        })
      );
      onSuccess?.();
    },
    [onSuccess]
  );

  const renderCustomerRow = useCallback(
    (customer, selectedCustomers, handleCustomerSelect) => {
      const isSelected = selectedCustomers.some((c) => c.id === customer.id);
      return (
        <tr
          key={customer.id}
          onClick={() => handleCustomerSelect(customer)}
          className={`cursor-pointer transition-all duration-200 hover:bg-muted/80 ${
            isSelected
              ? "bg-primary/10 border-l-4 border-primary"
              : "border-l-4 border-transparent"
          }`}
        >
          <td className="px-3 py-2 w-[80%]">
            <div className="flex items-center gap-2">
              <UserAvatar user={customer} />
              <div className="flex flex-col">
                <span className="font-medium text-foreground text-sm line-clamp-1">
                  {customer.name}
                </span>
                <span className="text-xs text-muted-foreground">
                  {customer.email}
                </span>
              </div>
            </div>
          </td>
        </tr>
      );
    },
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
                  {framework.frameworkCode} version:{framework.frameworkVersion}
                </span>
              </div>
            </div>
          </td>
        </tr>
      );
    },
    []
  );

  const leftConfig = {
    title: "Select Customer",
    icon: "building",
    fetchFn: fetchCustomersFn,
    extraParams: { role: ROLE_CUSTOMER_ADMIN },
    errorMessage: "Failed to load customers",
    placeholder: "Search customer...",
    renderRow: renderCustomerRow,
  };

  const rightConfig = {
    title: "Select Approved Frameworks",
    icon: "check-circle",
    fetchFn: fetchApprovedFrameworksFn,
    errorMessage: "Failed to load approved frameworks",
    placeholder: "Search frameworks...",
    renderRow: renderFrameworkRow,
  };

  return (
    <DualSelectionModal
      isOpen={isOpen}
      onClose={onClose}
      onSubmit={handleAssignFrameworks}
      title="Assign Frameworks to Customer"
      description="Select customer and approved frameworks to assign access"
      icon="shield"
      actionLabel={(left, right) =>
        `Assign Frameworks (${left.length} × ${right.length})`
      }
      savingLabel="Assigning..."
      leftConfig={leftConfig}
      rightConfig={rightConfig}
    />
  );
}
