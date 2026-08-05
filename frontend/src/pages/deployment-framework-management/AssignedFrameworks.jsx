/* eslint-disable react/prop-types */

import { useState } from "react";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAssignmentFrameworks } from "@/services/deploymentFrameworkService";
import GridCardView from "@/components/grid-card/GridCardView";
import AssignedFrameworkCard from "./components/custom/AssignedFrameworkCard";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
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
    defaultLimit: 12,
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
        const framework = response.data;
        const currentVersion =
          framework.fileVersions?.find(
            (v) => v.fileVersion === framework.currentFileVersion
          ) || framework.fileVersions?.[0];

        if (!currentVersion?.fileId) {
          toast.error("File information not available");
          return;
        }

        await downloadFrameworkFile(
          framework.id,
          currentVersion.fileId,
          currentVersion.originalFileName || framework.frameworkName
        );
      }
    } catch (err) {
      toast.error(err.message || "Failed to download framework");
    } finally {
      setIsDownloading(false);
    }
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
            label: "Not finalized",
            onClick: () => handleFinalizationFilter(STATUS_PENDING),
          },
        ],
      },
    ].filter(Boolean);
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <GridCardView
        data={assignmentResults}
        loading={loading}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        sortOrder={sortConfig.sortOrder}
        headerActions={getHeaderActions()}
        onSortChange={() => handleSort(sortConfig.sortBy)}
        pagination={pagination}
        renderCard={(assignment) => (
          <AssignedFrameworkCard
            key={assignment.id}
            framework={assignment}
            onNavigate={(id) => navigate(`/assigned-frameworks/${id}`)}
            onDownload={handleDownloadFramework}
            isDownloading={isDownloading}
          />
        )}
        searchPlaceholder="Search by framework name or code..."
        emptyMessage={emptyMessage}
      />
    </div>
  );
}

export default AssignedFrameworks;
