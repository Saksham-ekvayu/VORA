import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAssignmentFrameworks } from "@/services/deploymentFrameworkService";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import UserMiniCard from "@/components/custom/UserMiniCard";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import {
  downloadFrameworkFile,
  getFrameworkById,
} from "@/services/frameworkService";
import {
  getAssignmentStatusFilterLabel,
  getFinalizationStatusFilterLabel,
  STATUS_ASSIGNED,
  STATUS_FINALIZED,
  STATUS_PENDING,
  STATUS_REVOKED,
} from "@/utils/commonUtils";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

function AssignedFrameworks() {
  const navigate = useNavigate();
  const [isDownloading, setIsDownloading] = useState(false);
  const {
    data: assignmentResults,
    loading,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    onFilterChange,
  } = useTableData(getAssignmentFrameworks, {
    defaultLimit: 10,
    defaultSortBy: "assignedAt",
    defaultSortOrder: "desc",
    emptyMessage: "No frameworks have been assigned yet",
  });

  const handleFrameworkAssignmentFilter = (assignmentStatus) => {
    onFilterChange("assignmentStatus", assignmentStatus);
  };

  const handleFinalizationFilter = (finalizationStatus) => {
    onFilterChange("finalizationStatus", finalizationStatus);
  };

  const handleDownloadFramework = async (framework) => {
    if (!framework.frameworkId) {
      toast.error("Framework id not found.");
      return;
    }
    setIsDownloading(true);

    try {
      const response = await getFrameworkById(framework.frameworkId);
      if (response.success && response.data) {
        const frameworkData = response.data;
        const currentVersion =
          frameworkData.fileVersions?.find(
            (v) => v.fileVersion === frameworkData.currentFileVersion
          ) || frameworkData.fileVersions?.[0];

        if (!currentVersion?.fileId) {
          toast.error("File information not available");
          return;
        }

        await downloadFrameworkFile(
          frameworkData.id,
          currentVersion.fileId,
          currentVersion.originalFileName || frameworkData.frameworkName
        );
      }
    } catch (err) {
      toast.error(err.message || "Failed to download framework");
    } finally {
      setIsDownloading(false);
    }
  };

  /* ---------------- TABLE CONFIG ---------------- */
  const columns = [
    {
      key: "frameworkName",
      label: "Framework Name",
      sortable: false,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row.frameworkName}
          description={row.frameworkVersion}
          link={`/assigned-frameworks/${row.id}`}
        />
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      render: (value) => <CustomBadge status={value} size="sm" />,
    },
    {
      key: "finalization",
      label: "Finalization",
      sortable: false,
      render: (value, row) => (
        <CustomBadge
          size="sm"
          status={row.finalization?.isFinalized ? "Finalized" : "Pending"}
        />
      ),
    },
    {
      key: "assignedBy",
      label: "Action By",
      sortable: false,
      render: (value, row) => {
        let user = null;
        if (row.status === "revoked" && row.revocation?.revokedBy) {
          user = row.revocation.revokedBy;
        } else if (row.assignment?.assignedBy) {
          user = row.assignment.assignedBy;
        }

        if (user) {
          return (
            <UserMiniCard
              name={user.name}
              email={user.email}
              avatar={user.avatar}
            />
          );
        }
        return <span className="text-sm font-medium">System</span>;
      },
    },
    {
      key: "assignedAt",
      label: "Action At",
      sortable: true,
      render: (value, row) => {
        let date = row.assignedAt;
        if (row.status === "revoked" && row.revocation?.revokedAt) {
          date = row.revocation.revokedAt;
        } else if (row.assignment?.assignedAt) {
          date = row.assignment.assignedAt;
        }
        return (
          <span className="text-sm whitespace-nowrap">
            {formatDateWithMonthNameAndTime(date)}
          </span>
        );
      },
    },
  ];

  const renderActions = (row) => {
    const actions = [
      {
        id: `view-${row.id}`,
        label: "View Details",
        icon: "eye",
        onClick: () => navigate(`/assigned-frameworks/${row.id}`),
      },
      {
        id: `download-${row.id}`,
        label: "Download Framework",
        icon: "download",
        onClick: () => handleDownloadFramework(row),
        disabled: isDownloading,
      },
    ];

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
    const finalizationStatusFilter = urlParams.get("finalizationStatus") || "";

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
          ...[STATUS_ASSIGNED, STATUS_REVOKED].map((s, idx) => ({
            label: s,
            onClick: () => handleFrameworkAssignmentFilter(s),
            separatorBefore: idx === 0,
          })),
        ],
      },
      {
        type: "dropdown",
        label: getFinalizationStatusFilterLabel(finalizationStatusFilter),
        triggerClassName: "w-fit",
        options: [
          {
            label: "All Status",
            onClick: () => handleFinalizationFilter(""),
          },
          {
            label: "Finalized",
            separatorBefore: true,
            onClick: () => handleFinalizationFilter(STATUS_FINALIZED),
          },
          {
            label: "Pending",
            onClick: () => handleFinalizationFilter(STATUS_PENDING),
          },
        ],
      },
    ].filter(Boolean);
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <DataTable
        entityName="Assigned Frameworks"
        columns={columns}
        data={assignmentResults}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search by framework name or code..."
        emptyMessage={emptyMessage}
      />
    </div>
  );
}

export default AssignedFrameworks;
