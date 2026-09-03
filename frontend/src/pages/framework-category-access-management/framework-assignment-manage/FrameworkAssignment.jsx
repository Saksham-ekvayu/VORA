/* eslint-disable react/prop-types */

import { useState } from "react";
import { toast } from "sonner";
import DataTable from "@/components/data-table/DataTable";
import Icon from "@/components/custom/Icon";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import AssignFrameworkModal from "./components/AssignFrameworkModal";
import RevokeAssignmentModal from "./components/RevokeAssignmentModal";
import AssignmentViewModal from "./components/AssignmentViewModal";
import UserMiniCard from "@/components/custom/UserMiniCard";
import CustomBadge from "@/components/custom/CustomBadge";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAssignmentStatusFilterLabel } from "@/utils/commonUtils";
import {
  getFrameworkAssignments,
  revokeFrameworkAssignment,
  assignFrameworksToCustomers,
} from "@/services/adminService";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

function FrameworkAssignment() {
  const [assignModalOpen, setAssignModalOpen] = useState(false);

  const [viewModalState, setViewModalState] = useState({
    isOpen: false,
    assignment: null,
  });

  const [revokeModalState, setRevokeModalState] = useState({
    isOpen: false,
    assignment: null,
  });

  // Use custom hook for table data management
  const {
    data: assignments,
    loading,
    error,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    onFilterChange,
    refetch,
  } = useTableData(getFrameworkAssignments, {
    defaultLimit: 10,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No framework assignments found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleFrameworkAssignmentFilter = (assignmentStatus) => {
    onFilterChange("assignmentStatus", assignmentStatus);
  };

  /* ---------------- REVOKE ---------------- */
  const handleRevokeAssignment = async () => {
    try {
      const assignment = revokeModalState.assignment;
      const customerId = assignment?.customer?.id;
      const frameworkId = assignment?.frameworkId;

      if (!customerId || !frameworkId) {
        toast.error("Invalid assignment record. Cannot revoke.");
        return;
      }

      const response = await revokeFrameworkAssignment(customerId, frameworkId);
      toast.success(response.message);
      setRevokeModalState({ isOpen: false, assignment: null });
      refetch();
    } catch (e) {
      toast.error(e.message);
      throw e;
    }
  };

  /* ---------------- REASSIGN ---------------- */
  const handleReassignAssignment = async (row) => {
    try {
      const customerId = row?.customer?.id;
      const tenantId = row?.tenantId;
      const frameworkId = row?.frameworkId;

      if (!customerId || !tenantId || !frameworkId) {
        toast.error("Invalid assignment record. Cannot reassign.");
        return;
      }

      const response = await assignFrameworksToCustomers(customerId, tenantId, [
        frameworkId,
      ]);
      toast.success(response.message);
      refetch();
    } catch (err) {
      toast.error(err.message);
      console.error(err);
    }
  };

  /* ---------------- TABLE CONFIG ---------------- */
  const columns = [
    {
      key: "customer.name",
      label: "Organization",
      sortable: false,
      render: (value, row) => (
        <UserMiniCard
          name={row.customer?.name}
          email={row.customer?.email}
          avatar={row.customer?.avatar}
        />
      ),
    },
    {
      key: "frameworkName",
      label: "Framework",
      sortable: false,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row?.frameworkName}
          description={row?.frameworkVersion}
        />
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      render: (value) => <CustomBadge status={value} />,
    },
    {
      key: "assignment.assignedBy",
      label: "Assigned By",
      sortable: false,
      render: (value, row) =>
        row.assignment?.assignedBy?.name ? (
          <UserMiniCard
            name={row.assignment.assignedBy.name}
            email={row.assignment.assignedBy.email}
            avatar={row.assignment.assignedBy.avatar}
          />
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        ),
    },
    {
      key: "assignment.assignedAt",
      label: "Assigned On",
      sortable: false,
      render: (value, row) =>
        row.assignment?.assignedAt ? (
          <div className="flex items-center gap-2">
            <Icon
              name="calendar"
              size="14px"
              className="text-muted-foreground"
            />
            <span className="text-sm whitespace-nowrap">
              {formatDateWithMonthNameAndTime(row.assignment.assignedAt)}
            </span>
          </div>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        ),
    },
  ];

  const renderActions = (row) => {
    const actions = [
      {
        id: `view-${row.id}`,
        label: "View Details",
        icon: "eye",
        onClick: () => setViewModalState({ isOpen: true, assignment: row }),
      },
    ];

    if (row.status === "assigned") {
      actions.push({
        id: `revoke-${row.id}`,
        label: "Revoke Assignment",
        icon: "ban",
        variant: "destructive",
        onClick: () => setRevokeModalState({ isOpen: true, assignment: row }),
      });
    }

    if (row.status === "revoked") {
      actions.push({
        id: `reassign-${row.id}`,
        label: "Reassign Framework",
        icon: "refresh",
        onClick: () => handleReassignAssignment(row),
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
    const assignmentFrameworkStatusFilter =
      urlParams.get("assignmentStatus") || "";

    return [
      {
        type: "dropdown",
        label: getAssignmentStatusFilterLabel(assignmentFrameworkStatusFilter),
        triggerClassName: "w-fit",
        options: [
          {
            label: "All Status",
            onClick: () => handleFrameworkAssignmentFilter(""),
          },
          ...["assigned", "revoked"].map((s, idx) => ({
            label: s,
            onClick: () => handleFrameworkAssignmentFilter(s),
            separatorBefore: idx === 0,
          })),
        ],
      },
      {
        type: "button",
        label: "Assign Frameworks",
        icon: "plus",
        onClick: () => setAssignModalOpen(true),
      },
    ];
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="mt-5 pb-5 space-y-8">
      <DataTable
        entityName="Assignments"
        columns={columns}
        data={assignments}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search customer or framework..."
        emptyMessage={emptyMessage}
        error={error}
      />

      {viewModalState.isOpen && viewModalState.assignment && (
        <AssignmentViewModal
          assignment={viewModalState.assignment}
          onClose={() => setViewModalState({ isOpen: false, assignment: null })}
        />
      )}

      {assignModalOpen && (
        <AssignFrameworkModal
          isOpen={assignModalOpen}
          onSuccess={() => {
            setAssignModalOpen(false);
            refetch();
          }}
          onClose={() => setAssignModalOpen(false)}
        />
      )}

      {revokeModalState.isOpen && revokeModalState.assignment && (
        <RevokeAssignmentModal
          assignment={revokeModalState.assignment}
          onConfirm={handleRevokeAssignment}
          onCancel={() =>
            setRevokeModalState({ isOpen: false, assignment: null })
          }
        />
      )}
    </div>
  );
}

export default FrameworkAssignment;
