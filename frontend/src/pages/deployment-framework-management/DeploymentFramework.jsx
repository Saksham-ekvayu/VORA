import { useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { DeleteDeploymentFrameworkModal } from "@/components/custom/modal";
import ActionDropdown from "@/components/custom/ActionDropdown";
import {
  downloadDeploymentFrameworkFile,
  getAllDeploymentFrameworks,
  deleteDeploymentFramework,
} from "@/services/deploymentFrameworkService";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { useAuth } from "@/context/authContext/useAuth";
import {
  isAuditor,
  isCustomerAdmin,
  isExpert,
  getReviewStatusFilterLabel,
  getAiExtractionStatusFilterLabel,
  STATUS_PENDING,
  STATUS_APPROVED,
  STATUS_REJECTED,
  STATUS_REQUESTED,
  STATUS_UPLOADED,
  STATUS_FAILED,
  STATUS_PROCESSING,
  STATUS_EXTRACTED,
} from "@/utils/commonUtils";
import DataTable from "@/components/data-table/DataTable";
import StatusCard from "@/components/custom/StatusCard";
import UserMiniCard from "@/components/custom/UserMiniCard";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import UploadDeploymentFrameworkModal from "./components/UploadDeploymentFrameworkModal";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

function DeploymentFramework() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [isDownloading, setIsDownloading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [frameworkToDelete, setFrameworkToDelete] = useState(null);

  // Use custom hook for table data management
  const {
    data: deploymentFrameworks,
    loading,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    onFilterChange,
    refetch,
  } = useTableData(getAllDeploymentFrameworks, {
    defaultLimit: 10,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No deployment frameworks found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleAiExtractionStatusFilter = (aiExtractionStatus) => {
    onFilterChange("aiExtractionStatus", aiExtractionStatus);
  };

  const handleRequestReviewStatusFilter = (requestReviewStatus) => {
    onFilterChange("requestReviewStatus", requestReviewStatus);
  };

  const handleUploadSuccess = async () => {
    await refetch();
  };

  const handleDeleteFramework = (framework) => {
    setFrameworkToDelete(framework);
  };

  const handleDeleteConfirm = async () => {
    if (!frameworkToDelete) return;
    try {
      const result = await deleteDeploymentFramework(frameworkToDelete.id);
      toast.success(result.message || "Framework deleted successfully");
      refetch();
      setFrameworkToDelete(null);
    } catch (error) {
      console.error("Delete framework error:", error);
      toast.error(error.message || "Failed to delete framework");
    }
  };

  const handleDeleteCancel = () => {
    setFrameworkToDelete(null);
  };

  const handleDownloadFramework = async (row) => {
    if (!row.fileInfo?.versionFileId) {
      toast.error("File information not available");
      return;
    }
    setIsDownloading(true);

    try {
      await downloadDeploymentFrameworkFile(
        row.id, // frameworkId
        row.fileInfo.versionFileId,
        row.fileInfo.originalFileName
      );
    } catch (err) {
      toast.error(err.message);
      throw err;
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
          link={`/deployment-frameworks/${row.id}`}
        />
      ),
    },
    {
      key: "package",
      label: "Package Info",
      sortable: false,
      render: (value, row) => {
        const documentCount = row.document?.count ?? 0;
        const isPlural = documentCount > 1;
        return (
          <div className="flex flex-col">
            <span className="text-sm font-medium">
              v{row.currentPackageVersion || "1.0.0"}
            </span>
            <span className="text-xs text-muted-foreground">
              {documentCount} document{isPlural ? "s" : ""}
            </span>
          </div>
        );
      },
    },
    {
      key: "aiExtraction",
      label: "AI Extraction",
      sortable: false,
      render: (value) => <StatusCard item={value} />,
    },
    {
      key: "requestReview",
      label: "Review Status",
      sortable: false,
      render: (value) => <StatusCard item={value} />,
    },
    {
      key: "packageStatus",
      label: "Package Status",
      sortable: false,
      render: (value, row) => <StatusCard item={row.package} />,
    },
    {
      key: "uploadedBy",
      label: "Created By",
      sortable: false,
      render: (value) => (
        <UserMiniCard
          name={value?.name}
          email={value?.email}
          avatar={value?.avatar}
        />
      ),
    },
    {
      key: "createdAt",
      label: "Created On",
      sortable: true,
      render: (value) => (
        <span className="text-sm whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
  ];

  const renderActions = (row) => {
    const actions = [
      {
        id: `view-${row.id}`,
        label: "View Details",
        icon: "eye",
        onClick: () => navigate(`/deployment-frameworks/${row.id}`),
      },
      {
        id: `download-${row.id}`,
        label: "Download Framework",
        icon: "download",
        onClick: () => handleDownloadFramework(row),
        disabled: isDownloading,
      },
      (isAuditor(user.role) || isCustomerAdmin(user.role)) &&
        row.requestReview?.status !== "approved" && {
          id: `delete-${row.id}`,
          label: "Delete Framework",
          icon: "trash",
          variant: "destructive",
          onClick: () => handleDeleteFramework(row),
        },
    ].filter(Boolean);

    return (
      <div className="flex justify-center">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const aiExtractionStatusFilter = urlParams.get("aiExtractionStatus") || "";
    const requestReviewStatusFilter =
      urlParams.get("requestReviewStatus") || "";

    return [
      {
        type: "dropdown",
        label: getReviewStatusFilterLabel(requestReviewStatusFilter),
        triggerClassName: "w-fit",
        options: [
          {
            label: "All Status",
            onClick: () => handleRequestReviewStatusFilter(""),
          },
          ...[
            STATUS_PENDING,
            STATUS_REQUESTED,
            STATUS_APPROVED,
            STATUS_REJECTED,
          ]
            .filter((s) => !(isExpert(user.role) && s === STATUS_PENDING))
            .map((s, idx) => ({
              label: s,
              onClick: () => handleRequestReviewStatusFilter(s),
              separatorBefore: idx === 0,
            })),
        ],
      },
      isAuditor(user.role) && {
        type: "dropdown",
        label: getAiExtractionStatusFilterLabel(aiExtractionStatusFilter),
        triggerClassName: "w-fit",
        options: [
          {
            label: "All Extraction",
            onClick: () => handleAiExtractionStatusFilter(""),
          },
          ...[
            STATUS_PENDING,
            STATUS_UPLOADED,
            STATUS_FAILED,
            STATUS_PROCESSING,
            STATUS_EXTRACTED,
          ].map((s) => ({
            label: s,
            onClick: () => handleAiExtractionStatusFilter(s),
          })),
        ],
      },
      isAuditor(user.role) && {
        type: "button",
        label: "Add Deployment Framework",
        icon: "plus",
        className: "bg-primary text-primary-foreground hover:bg-primary/90",
        onClick: () => setUploadModalOpen(true),
      },
    ].filter(Boolean);
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <DataTable
        entityName="Deployment Frameworks"
        columns={columns}
        data={deploymentFrameworks}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search framework name, code, or uploader..."
        emptyMessage={emptyMessage}
      />

      {uploadModalOpen && (
        <UploadDeploymentFrameworkModal
          isOpen={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          onSuccess={handleUploadSuccess}
        />
      )}

      {frameworkToDelete && (
        <DeleteDeploymentFrameworkModal
          open={!!frameworkToDelete}
          onCancel={handleDeleteCancel}
          onConfirm={handleDeleteConfirm}
          framework={frameworkToDelete}
        />
      )}
    </div>
  );
}

export default DeploymentFramework;
