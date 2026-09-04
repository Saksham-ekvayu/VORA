/* eslint-disable react/prop-types */

import { useState } from "react";
import { Helmet } from "react-helmet-async";
import Icon from "@/components/custom/Icon";
import { getFrameworkCategory } from "@/services/frameworkService";
import RequestAccessModal from "./components/RequestAccessModal";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import GridCardView from "@/components/grid-card/GridCardView";
import FrameworkCategoryCard from "../framework-category-access-management/framework-category-manage/components/custom/FrameworkCategoryCard";
import { Button } from "@/components/ui/button";
import {
  getAccessStatusFilterLabel,
  getRequestActionIcon,
  getRequestActionLabel,
  getStatusFilterLabel,
  STATUS_APPROVED,
  STATUS_PENDING,
  STATUS_REJECTED,
  STATUS_REVOKED,
} from "@/utils/commonUtils";

function FrameworkCategory() {
  const [requestModalState, setRequestModalState] = useState({
    isOpen: false,
    framework: null,
  });

  // Use custom hook for table data management
  const {
    data: categories,
    loading,
    error,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onFilterChange,
    onSearch: handleSearch,
    onSort: handleSort,
    refetch,
  } = useTableData(getFrameworkCategory, {
    defaultLimit: 12,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No framework category found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleStatusFilter = (status) => {
    onFilterChange("isActive", status);
  };

  const handleAccessStatusFilter = (status) => {
    onFilterChange("accessStatus", status);
  };

  /* ---------------- REQUEST ACCESS HANDLERS ---------------- */
  const handleRequestAccessSuccess = () => {
    refetch();
    setRequestModalState({ isOpen: false, framework: null });
  };

  /* ---------------- CONFIG ---------------- */
  const renderPrimaryAction = (category) => {
    const { hasRequested, requestStatus, isActive } = category;

    // We show the "Request" button if:
    // 1. It hasn't been requested yet
    // 2. OR it was previously requested but is now STATUS_REVOKED or "rejected"
    const canRequest =
      !hasRequested ||
      requestStatus === STATUS_REVOKED ||
      requestStatus === STATUS_REJECTED;

    if (!isActive || !canRequest) return null;

    const isReRequest =
      requestStatus === STATUS_REVOKED || requestStatus === STATUS_REJECTED;

    return (
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
        <Button
          size="xs"
          onClick={() =>
            setRequestModalState({ isOpen: true, framework: category })
          }
        >
          <Icon
            name={isReRequest ? "refresh" : "plus"}
            size="14px"
            className="mr-2"
          />
          {isReRequest ? "Re-request Access" : "Request Access"}
        </Button>
      </div>
    );
  };

  const renderActions = (row) => {
    const isActive = row.isActive;
    const hasRequested = row.hasRequested;
    const requestStatus = row.requestStatus;

    // Allow requesting if not requested or if revoked / rejected
    const canRequest =
      !hasRequested ||
      requestStatus === STATUS_REVOKED ||
      requestStatus === STATUS_REJECTED;
    const isDisabled = !isActive || !canRequest;

    const actions = [
      {
        id: `request-${row.id}`,
        label: getRequestActionLabel(requestStatus, hasRequested),
        icon: getRequestActionIcon(requestStatus, hasRequested),
        className:
          hasRequested && requestStatus !== STATUS_REVOKED
            ? "text-muted-foreground"
            : "",
        disabled: isDisabled,
        onClick: () => {
          if (!isDisabled) {
            setRequestModalState({ isOpen: true, framework: row });
          }
        },
      },
    ];

    return (
      <div className="h-8 w-8 flex items-center justify-center bg-muted/40 rounded border border-border/40 hover:bg-muted/60 transition-colors">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const statusFilter = urlParams.get("isActive") || "";
    const accessStatusFilter = urlParams.get("accessStatus") || "";

    return [
      {
        type: "dropdown",
        label: getStatusFilterLabel(statusFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Status", onClick: () => handleStatusFilter("") },
          {
            label: "Active",
            onClick: () => handleStatusFilter("true"),
            separatorBefore: true,
          },
          { label: "Inactive", onClick: () => handleStatusFilter("false") },
        ],
      },
      {
        type: "dropdown",
        label: getAccessStatusFilterLabel(accessStatusFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Status", onClick: () => handleAccessStatusFilter("") },
          {
            label: "Pending",
            onClick: () => handleAccessStatusFilter(STATUS_PENDING),
            separatorBefore: true,
          },
          {
            label: "Approved",
            onClick: () => handleAccessStatusFilter(STATUS_APPROVED),
          },
          {
            label: "Rejected",
            onClick: () => handleAccessStatusFilter(STATUS_REJECTED),
          },
          {
            label: "Revoked",
            onClick: () => handleAccessStatusFilter(STATUS_REVOKED),
          },
        ],
      },
    ].filter(Boolean);
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <Helmet>
        <title>VORA - Framework Categories</title>
      </Helmet>
      <GridCardView
        data={categories}
        loading={loading}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        sortOrder={sortConfig.sortOrder}
        onSortChange={() => handleSort(sortConfig.sortBy)}
        pagination={pagination}
        headerActions={getHeaderActions()}
        renderCard={(category) => (
          <div key={category.id} className="relative group">
            <FrameworkCategoryCard
              category={category}
              renderActions={renderActions}
            />
            {renderPrimaryAction(category)}
          </div>
        )}
        searchPlaceholder="Filter categories by name or code..."
        emptyMessage={emptyMessage}
        error={error}
        gridCols="grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3"
      />

      {/* Request Access Modal */}
      {requestModalState.isOpen && requestModalState.framework && (
        <RequestAccessModal
          framework={requestModalState.framework}
          onSuccess={handleRequestAccessSuccess}
          onClose={() =>
            setRequestModalState({ isOpen: false, framework: null })
          }
        />
      )}
    </div>
  );
}

export default FrameworkCategory;
