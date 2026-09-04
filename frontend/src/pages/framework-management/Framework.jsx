/* eslint-disable react/prop-types */

import { useState } from "react";
import { Helmet } from "react-helmet-async";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import UploadFrameworkModal from "./components/UploadFrameworkModal";
import UpdateFrameworkModal from "./components/UpdateFrameworkModal";
import { DeleteFrameworkModal } from "@/components/custom/modal";
import UserMiniCard from "@/components/custom/UserMiniCard";
import FileTypeCard from "@/components/custom/FileTypeCard";
import ActionDropdown from "@/components/custom/ActionDropdown";
import {
  downloadFrameworkFile,
  getAllFrameworks,
  deleteFramework,
} from "@/services/frameworkService";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { useAuth } from "@/context/authContext/useAuth";
import {
  isExpert,
  getAiStatusFilterLabel,
  getApprovalFilterLabel,
  STATUS_UPLOADED,
  STATUS_FAILED,
  STATUS_PENDING,
  STATUS_PROCESSING,
  STATUS_EXTRACTED,
  STATUS_APPROVED,
  STATUS_REJECTED,
} from "@/utils/commonUtils";
import { useExpertCategoryAccess } from "@/hooks/useExpertCategoryAccess";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import StatusCard from "@/components/custom/StatusCard";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

// ========== HELPER FUNCTIONS ==========
// Extract expert actions to reduce cognitive complexity of renderActions
const buildExpertActions = (
  row,
  hasAccess,
  handleUpdateFramework,
  handleDeleteFramework
) => {
  const actions = [
    {
      id: `update-${row.fileInfo.versionFileId}`,
      label: hasAccess ? "Update Framework" : "No Access to Update",
      icon: "edit",
      onClick: hasAccess ? () => handleUpdateFramework(row) : undefined,
      disabled: !hasAccess,
    },
  ];

  if (row.approval?.status !== "approved") {
    actions.push({
      id: `delete-${row.fileInfo.versionFileId}`,
      label: hasAccess ? "Delete Framework" : "No Access to Delete",
      icon: "trash",
      variant: "destructive",
      onClick: hasAccess ? () => handleDeleteFramework(row) : undefined,
      disabled: !hasAccess,
    });
  }

  return actions;
};

function Framework() {
  const { user } = useAuth();
  const { hasAccessToCategory } = useExpertCategoryAccess();
  const navigate = useNavigate();

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [frameworkToDelete, setFrameworkToDelete] = useState(null);
  const [frameworkToUpdate, setFrameworkToUpdate] = useState(null);

  // Use custom hook for table data management
  const {
    data: frameworks,
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
  } = useTableData(getAllFrameworks, {
    defaultLimit: 10,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No frameworks found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleStatusFilter = (status) => {
    onFilterChange("aiStatus", status);
  };

  const handleApprovalFilter = (approval) => {
    onFilterChange("approvalStatus", approval);
  };

  const handleUploadSuccess = async () => {
    await new Promise((resolve) => {
      setTimeout(resolve, 100);
    });
    await refetch();
  };

  const handleUpdateFramework = (framework) => {
    setFrameworkToUpdate(framework);
    setUpdateModalOpen(true);
  };

  const handleUpdateSuccess = () => {
    refetch();
  };

  const handleDeleteFramework = (framework) => {
    setFrameworkToDelete(framework);
  };

  const handleDeleteConfirm = async () => {
    if (!frameworkToDelete) return;
    try {
      const result = await deleteFramework(frameworkToDelete.id);
      toast.success(result.message || "Framework deleted successfully");
      refetch();
      setFrameworkToDelete(null);
    } catch (error) {
      console.error("Delete error:", error);
      toast.error(error.message || "Failed to delete framework");
      throw error;
    }
  };

  const handleDeleteCancel = () => {
    setFrameworkToDelete(null);
  };

  const handleDownloadFramework = async (row) => {
    if (!row.fileInfo?.fileId) return;

    try {
      await downloadFrameworkFile(
        row.id, // frameworkId
        row.fileInfo.fileId, // fileId
        row.fileInfo.originalFileName
      );
    } catch (err) {
      toast.error(err.message);
      throw err;
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
          link={`/frameworks/${row.id}`}
        />
      ),
    },
    {
      key: "frameworkType",
      label: "File Info",
      sortable: false,
      render: (value, row) => {
        return (
          <div className="max-w-40">
            <FileTypeCard
              fileType={row.fileInfo.fileType}
              fileSize={row.fileInfo?.fileSize}
              fileName={row.fileInfo?.originalFileName}
              fileId={row.fileInfo?.fileId}
              onDownload={() => handleDownloadFramework(row)}
              serviceType="framework"
              frameworkId={row.id}
            />
          </div>
        );
      },
    },
    {
      key: "aiExtraction",
      label: "Ai Extraction",
      sortable: false,
      render: (value, row) => <StatusCard item={row.aiExtraction} />,
    },
    {
      key: "approval.status",
      label: "Approval",
      sortable: false,
      render: (value, row) => {
        return <StatusCard item={row.approval} />;
      },
    },
    {
      key: "uploadedBy",
      label: "Created By",
      sortable: false,
      render: (value) => {
        return (
          <UserMiniCard
            name={value.name}
            email={value.email}
            avatar={value.avatar}
          />
        );
      },
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
    const hasAccess = isExpert(user.role)
      ? hasAccessToCategory(row.frameworkCategoryId)
      : true;

    const actions = [
      {
        id: `view-${row.id}`,
        label: "View Details",
        icon: "eye",
        onClick: () => navigate(`/frameworks/${row.id}`),
      },
      ...(isExpert(user.role)
        ? buildExpertActions(
            row,
            hasAccess,
            handleUpdateFramework,
            handleDeleteFramework
          )
        : []),
    ];

    return (
      <div className="flex justify-center">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const statusFilter = urlParams.get("aiStatus") || "";
    const approvalFilter = urlParams.get("approvalStatus") || "";

    return [
      {
        type: "dropdown",
        label: getAiStatusFilterLabel(statusFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Status", onClick: () => handleStatusFilter("") },
          {
            label: "Uploaded",
            onClick: () => handleStatusFilter(STATUS_UPLOADED),
            separatorBefore: true,
          },
          { label: "Failed", onClick: () => handleStatusFilter(STATUS_FAILED) },
          {
            label: "Pending",
            onClick: () => handleStatusFilter(STATUS_PENDING),
          },
          {
            label: "Processing",
            onClick: () => handleStatusFilter(STATUS_PROCESSING),
          },
          {
            label: "Extracted",
            onClick: () => handleStatusFilter(STATUS_EXTRACTED),
          },
        ],
      },
      {
        type: "dropdown",
        label: getApprovalFilterLabel(approvalFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Status", onClick: () => handleApprovalFilter("") },
          {
            label: "Pending",
            onClick: () => handleApprovalFilter(STATUS_PENDING),
            separatorBefore: true,
          },
          {
            label: "Approved",
            onClick: () => handleApprovalFilter(STATUS_APPROVED),
          },
          {
            label: "Rejected",
            onClick: () => handleApprovalFilter(STATUS_REJECTED),
          },
        ],
      },
      {
        type: "button",
        label: "Add Framework",
        icon: "plus",
        onClick: () => setUploadModalOpen(true),
      },
    ];
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <Helmet>
        <title>VORA - Frameworks</title>
      </Helmet>
      {/* Data Table */}
      <DataTable
        entityName="Frameworks"
        columns={columns}
        data={frameworks}
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
        error={error}
      />

      {/* Upload Framework Modal */}
      {uploadModalOpen && (
        <UploadFrameworkModal
          isOpen={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          onSuccess={handleUploadSuccess}
        />
      )}

      {/* Update Framework Modal */}
      {updateModalOpen && frameworkToUpdate && (
        <UpdateFrameworkModal
          isOpen={updateModalOpen}
          onClose={() => {
            setUpdateModalOpen(false);
            setFrameworkToUpdate(null);
          }}
          onSuccess={handleUpdateSuccess}
          framework={frameworkToUpdate}
        />
      )}

      {/* Delete Framework Modal */}
      {frameworkToDelete && (
        <DeleteFrameworkModal
          open={!!frameworkToDelete}
          onCancel={handleDeleteCancel}
          onConfirm={handleDeleteConfirm}
          framework={frameworkToDelete}
        />
      )}
    </div>
  );
}

export default Framework;
