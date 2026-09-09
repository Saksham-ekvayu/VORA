/* eslint-disable react/prop-types */

import { useState } from "react";
import { Helmet } from "react-helmet-async";
import { getFrameworkCategory } from "@/services/frameworkService";
import RequestAccessModal from "./components/RequestAccessModal";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import {
  getAccessStatusFilterLabel,
  getRequestActionIcon,
  getRequestActionLabel,
  getStatusFilterLabel,
  STATUS_PENDING,
  STATUS_APPROVED,
  STATUS_REJECTED,
  STATUS_REVOKED,
} from "@/utils/commonUtils";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

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

  /* ---------------- TABLE CONFIG ---------------- */
  const columns = [
    {
      key: "frameworkCategoryName",
      label: "Framework Category",
      sortable: true,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row.frameworkCategoryName}
          description={row.code}
        />
      ),
    },
    {
      key: "description",
      label: "Description",
      sortable: false,
      render: (value) => (
        <span className="block w-96 max-w-full text-xs line-clamp-2 whitespace-normal wrap-break-word">
          {value || "No description provided"}
        </span>
      ),
    },
    {
      key: "isActive",
      label: "Status",
      sortable: true,
      render: (value) => (
        <CustomBadge size="sm" isActive={value} className="w-fit" />
      ),
    },
    {
      key: "requestStatus",
      label: "Access Status",
      sortable: false,
      render: (value) => {
        if (!value)
          return <span className="text-muted-foreground text-sm">—</span>;

        return <CustomBadge size="sm" status={value} className="w-fit" />;
      },
    },
    {
      key: "createdAt",
      label: "Created At",
      sortable: true,
      render: (value) => (
        <span className="">{formatDateWithMonthNameAndTime(value)}</span>
      ),
    },
  ];

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

    return <ActionDropdown actions={actions} />;
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
    ];
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <Helmet>
        <title>VORA - Framework Categories</title>
      </Helmet>
      <DataTable
        columns={columns}
        data={categories}
        loading={loading}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        onSort={handleSort}
        sortConfig={sortConfig}
        pagination={pagination}
        headerActions={getHeaderActions()}
        renderActions={renderActions}
        searchPlaceholder="Filter categories by name or code..."
        emptyMessage={emptyMessage}
        error={error}
        entityName="Framework Categories"
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
