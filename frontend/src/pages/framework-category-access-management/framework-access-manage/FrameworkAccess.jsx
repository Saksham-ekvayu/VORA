/* eslint-disable react/prop-types */

import { useState } from "react";
import { toast } from "sonner";
import {
  getAdminFrameworkAccess,
  approveFrameworkAccessRequest,
  rejectFrameworkAccessRequest,
  revokeFrameworkAccess,
  assignFrameworkAccess,
} from "@/services/adminService";
import DataTable from "@/components/data-table/DataTable";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import AccessViewModal from "./components/AccessViewModal";
import ManageAccessModal from "./components/ManageAccessModal";
import GiveFrameworkAccessModal from "./components/GiveFrameworkAccessModal";
import UserMiniCard from "@/components/custom/UserMiniCard";
import CustomBadge from "@/components/custom/CustomBadge";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import {
  getAccessStatusFilterLabel,
  STATUS_APPROVED,
  STATUS_PENDING,
  STATUS_REJECTED,
  STATUS_REVOKED,
} from "@/utils/commonUtils";

function FrameworkAccess() {
  const [viewModalState, setViewModalState] = useState({
    isOpen: false,
    accessRecord: null,
  });

  const [approveModalState, setApproveModalState] = useState({
    isOpen: false,
    accessRecord: null,
  });

  const [rejectModalState, setRejectModalState] = useState({
    isOpen: false,
    accessRecord: null,
  });

  const [revokeModalState, setRevokeModalState] = useState({
    isOpen: false,
    accessRecord: null,
  });

  const [giveAccessModalState, setGiveAccessModalState] = useState({
    isOpen: false,
  });

  const [loadingStates, setLoadingStates] = useState({});

  // Use custom hook for table data management
  const {
    data: frameworkAccessRecords,
    loading,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    onFilterChange,
    refetch,
  } = useTableData(getAdminFrameworkAccess, {
    defaultLimit: 10,
    defaultSortBy: "updatedAt",
    defaultSortOrder: "desc",
    emptyMessage: "No framework access records found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleStatusFilter = (status) => {
    onFilterChange("status", status);
  };

  /* ---------------- APPROVE ACCESS ---------------- */
  const handleApproveAccess = async () => {
    try {
      const accessRecord = approveModalState.accessRecord;
      const requestId = accessRecord?.id;

      if (!requestId) {
        toast.error("Invalid access record. Cannot approve access.");
        return;
      }

      const response = await approveFrameworkAccessRequest(requestId);
      toast.success(
        response.message || "Framework access approved successfully"
      );
      setApproveModalState({ isOpen: false, accessRecord: null });
      refetch();
    } catch (e) {
      console.error("Approve access error:", e);
      throw e;
    }
  };

  /* ---------------- REJECT ACCESS ---------------- */
  const handleRejectAccess = async () => {
    try {
      const accessRecord = rejectModalState.accessRecord;
      const requestId = accessRecord?.id;

      if (!requestId) {
        toast.error("Invalid access record. Cannot reject access.");
        return;
      }

      const response = await rejectFrameworkAccessRequest(requestId);
      toast.success(
        response.message || "Framework access rejected successfully"
      );
      setRejectModalState({ isOpen: false, accessRecord: null });
      refetch();
    } catch (e) {
      console.error("Reject access error:", e);
      throw e;
    }
  };

  /* ---------------- REVOKE ACCESS ---------------- */
  const handleRevokeAccess = async () => {
    try {
      const accessRecord = revokeModalState.accessRecord;
      const expertId = accessRecord?.expert?.id;
      const frameworkId = accessRecord?.frameworkCategory?.frameworkId;

      if (!expertId || !frameworkId) {
        toast.error("Invalid access record. Cannot revoke access.");
        return;
      }

      const response = await revokeFrameworkAccess(expertId, frameworkId);
      toast.success(
        response.message || "Framework access revoked successfully"
      );
      setRevokeModalState({ isOpen: false, accessRecord: null });
      refetch();
    } catch (e) {
      console.error("Revoke access error:", e);
      throw e;
    }
  };

  /* ---------------- GIVE ACCESS SUCCESS ---------------- */
  const handleGiveAccessSuccess = () => {
    setGiveAccessModalState({ isOpen: false });
    refetch();
  };

  /* ---------------- GIVE ACCESS FROM DROPDOWN ---------------- */
  const handleGiveAccessFromDropdown = async (row) => {
    const expertId = row?.expert?.id;
    const frameworkCategoryId = row?.frameworkCategory?.frameworkId;

    if (!expertId || !frameworkCategoryId) {
      toast.error("Invalid expert or framework information");
      return;
    }

    const loadingKey = `give-access-${row.id}`;
    setLoadingStates((prev) => ({ ...prev, [loadingKey]: true }));

    try {
      const response = await assignFrameworkAccess(expertId, [
        frameworkCategoryId,
      ]);
      toast.success(
        response.message || "Framework access assigned successfully"
      );
      refetch();
    } catch (e) {
      toast.error(e.message || "Failed to assign framework access");
    } finally {
      setLoadingStates((prev) => ({ ...prev, [loadingKey]: false }));
    }
  };

  /* ---------------- TABLE CONFIG ---------------- */
  const columns = [
    {
      key: "expert.name",
      label: "Expert",
      sortable: false,
      render: (value, row) => (
        <UserMiniCard
          name={row.expert?.name}
          email={row.expert?.email}
          avatar={row.expert?.avatar}
        />
      ),
    },
    {
      key: "frameworkCategory.frameworkCode",
      label: "Framework Code",
      sortable: false,
      render: (value, row) => (
        <span className="font-mono text-sm bg-muted px-2 py-1 rounded uppercase">
          {row.frameworkCategory?.frameworkCode}
        </span>
      ),
    },
    {
      key: "frameworkCategory.frameworkCategoryName",
      label: "Framework Name",
      sortable: false,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row.frameworkCategory?.frameworkCategoryName}
          description={row.frameworkCategory?.description}
        />
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      render: (value) => {
        return <CustomBadge status={value} />;
      },
    },
    {
      key: "actionBy",
      label: "Action By",
      sortable: false,
      render: (value, row) => {
        if (row.status === STATUS_APPROVED && row.approval?.approvedBy) {
          return (
            <UserMiniCard
              name={row.approval.approvedBy.name}
              email={row.approval.approvedBy.email}
              avatar={row.approval.approvedBy.avatar}
            />
          );
        } else if (
          row.status === STATUS_REJECTED &&
          row.rejection?.rejectedBy
        ) {
          return (
            <UserMiniCard
              name={row.rejection.rejectedBy.name}
              email={row.rejection.rejectedBy.email}
              avatar={row.rejection.rejectedBy.avatar}
            />
          );
        } else if (row.status === STATUS_REVOKED && row.revocation?.revokedBy) {
          return (
            <UserMiniCard
              name={row.revocation.revokedBy.name}
              email={row.revocation.revokedBy.email}
              avatar={row.revocation.revokedBy.avatar}
            />
          );
        } else if (row.status === STATUS_PENDING) {
          return (
            <UserMiniCard
              name="Pending"
              email="Awaiting admin action"
              icon="clock"
              isRequestPending={true}
            />
          );
        }
        return <span className="text-muted-foreground text-sm">—</span>;
      },
    },
    {
      key: "actionDate",
      label: "Action On",
      sortable: false,
      render: (value, row) => {
        let date = null;
        if (row.status === STATUS_APPROVED && row.approval?.approvedAt) {
          date = row.approval.approvedAt;
        } else if (
          row.status === STATUS_REJECTED &&
          row.rejection?.rejectedAt
        ) {
          date = row.rejection.rejectedAt;
        } else if (row.status === STATUS_REVOKED && row.revocation?.revokedAt) {
          date = row.revocation.revokedAt;
        } else if (row.status === STATUS_PENDING) {
          date = row.createdAt;
        }

        return date ? (
          <span className="text-sm whitespace-nowrap">
            {formatDateWithMonthNameAndTime(date)}
          </span>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        );
      },
    },
  ];

  const renderActions = (row) => {
    const isPending = row.status === STATUS_PENDING;
    const isApproved = row.status === STATUS_APPROVED;
    const isRejected = row.status === STATUS_REJECTED;
    const isRevoked = row.status === STATUS_REVOKED;
    const loadingKey = `give-access-${row.id}`;
    const isGivingAccess = loadingStates[loadingKey];

    const actions = [
      {
        id: `view-${row.id}`,
        label: "View Details",
        icon: "eye",
        onClick: () => setViewModalState({ isOpen: true, accessRecord: row }),
      },
    ];

    if (isPending) {
      actions.push(
        {
          id: `approve-${row.id}`,
          label: "Approve Access",
          icon: "check",
          onClick: () =>
            setApproveModalState({ isOpen: true, accessRecord: row }),
        },
        {
          id: `reject-${row.id}`,
          label: "Reject Access",
          icon: "x",
          variant: "destructive",
          onClick: () =>
            setRejectModalState({ isOpen: true, accessRecord: row }),
        }
      );
    }

    if (isApproved) {
      actions.push({
        id: `revoke-${row.id}`,
        label: "Revoke Access",
        icon: "ban",
        variant: "destructive",
        onClick: () => setRevokeModalState({ isOpen: true, accessRecord: row }),
      });
    }

    if (isRejected || isRevoked) {
      actions.push({
        id: `give-access-${row.id}`,
        label: isGivingAccess ? "Giving Access..." : "Give Access",
        icon: isGivingAccess ? "loader" : "plus",
        onClick: () => handleGiveAccessFromDropdown(row),
        disabled: isGivingAccess,
      });
    }

    return (
      <div className="flex justify-center">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const statusFilter = urlParams.get("status") || "";

    return [
      {
        type: "dropdown",
        label: getAccessStatusFilterLabel(statusFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Status", onClick: () => handleStatusFilter("") },
          {
            label: "Pending",
            onClick: () => handleStatusFilter(STATUS_PENDING),
            separatorBefore: true,
          },
          {
            label: "Approved",
            onClick: () => handleStatusFilter(STATUS_APPROVED),
          },
          {
            label: "Rejected",
            onClick: () => handleStatusFilter(STATUS_REJECTED),
          },
          {
            label: "Revoked",
            onClick: () => handleStatusFilter(STATUS_REVOKED),
          },
        ],
      },
      {
        type: "button",
        label: "Give Framework Access",
        icon: "plus",
        onClick: () => setGiveAccessModalState({ isOpen: true }),
      },
    ];
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="mt-5 pb-5 space-y-8">
      {/* Data Table */}
      <DataTable
        entityName="Access Records"
        columns={columns}
        data={frameworkAccessRecords}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search expert, framework, status..."
        emptyMessage={emptyMessage}
      />

      {viewModalState.isOpen && viewModalState.accessRecord && (
        <AccessViewModal
          accessRecord={viewModalState.accessRecord}
          onClose={() =>
            setViewModalState({ isOpen: false, accessRecord: null })
          }
        />
      )}

      {approveModalState.isOpen && approveModalState.accessRecord && (
        <ManageAccessModal
          type="approve"
          accessRecord={approveModalState.accessRecord}
          onConfirm={handleApproveAccess}
          onCancel={() =>
            setApproveModalState({ isOpen: false, accessRecord: null })
          }
        />
      )}

      {rejectModalState.isOpen && rejectModalState.accessRecord && (
        <ManageAccessModal
          type="reject"
          accessRecord={rejectModalState.accessRecord}
          onConfirm={handleRejectAccess}
          onCancel={() =>
            setRejectModalState({ isOpen: false, accessRecord: null })
          }
        />
      )}

      {revokeModalState.isOpen && revokeModalState.accessRecord && (
        <ManageAccessModal
          type="revoke"
          accessRecord={revokeModalState.accessRecord}
          onConfirm={handleRevokeAccess}
          onCancel={() =>
            setRevokeModalState({ isOpen: false, accessRecord: null })
          }
        />
      )}

      {giveAccessModalState.isOpen && (
        <GiveFrameworkAccessModal
          isOpen={giveAccessModalState.isOpen}
          onSuccess={handleGiveAccessSuccess}
          onClose={() => setGiveAccessModalState({ isOpen: false })}
        />
      )}
    </div>
  );
}

export default FrameworkAccess;
