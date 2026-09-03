/* eslint-disable react/prop-types */

import { useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import UploadDeploymentDocumentModal from "./components/UploadDeploymentDocumentModal";
import UpdateDeploymentDocumentModal from "./components/UpdateDeploymentDocumentModal";
import { ConfirmDeleteModal } from "@/components/custom/modal";
import UserMiniCard from "@/components/custom/UserMiniCard";
import FileTypeCard from "@/components/custom/FileTypeCard";
import ActionDropdown from "@/components/custom/ActionDropdown";
import {
  downloadDeploymentDocumentFile,
  getAllDeploymentDocuments,
  deleteDeploymentDocument,
  uploadDeploymentDocumentToAi,
} from "@/services/deploymentDocumentService";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { useAuth } from "@/context/authContext/useAuth";
import { isAdmin, isExpert, isCustomerAdmin } from "@/utils/commonUtils";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";
import StatusCard from "@/components/custom/StatusCard";

function DeploymentDocument() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState(null);
  const [documentToUpdate, setDocumentToUpdate] = useState(null);

  // Use custom hook for table data management
  const {
    data: deploymentDocuments,
    loading,
    error,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    refetch,
  } = useTableData(getAllDeploymentDocuments, {
    defaultLimit: 10,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No deployment documents found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleUploadSuccess = async () => {
    await refetch();
  };

  const handleUpdateDocument = (document) => {
    setDocumentToUpdate(document);
    setUpdateModalOpen(true);
  };

  const handleUpdateSuccess = () => {
    refetch();
  };

  const handleDeleteDocument = (document) => {
    setDocumentToDelete(document);
  };

  const handleDeleteConfirm = async () => {
    if (!documentToDelete) return;
    try {
      const result = await deleteDeploymentDocument(documentToDelete.id);
      toast.success(result.message || "Document deleted successfully");
      refetch();
      setDocumentToDelete(null);
    } catch (error) {
      console.error("Delete error:", error);
      toast.error(error.message || "Failed to delete document");
      throw error;
    }
  };

  const handleDeleteCancel = () => {
    setDocumentToDelete(null);
  };

  const handleDownloadDocument = async (row) => {
    if (!row.fileInfo?.versionFileId) return;

    try {
      await downloadDeploymentDocumentFile(
        row.id,
        row.fileInfo.versionFileId,
        row.fileInfo.originalFileName
      );
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const handleUploadToAi = async (documentId, fileId) => {
    try {
      const result = await uploadDeploymentDocumentToAi(documentId, fileId);
      toast.success(result.message || "Document uploaded to AI successfully");
      refetch();
    } catch (error) {
      toast.error(error.message || "Failed to upload to AI");
      refetch();
    }
  };

  /* ---------------- TABLE CONFIG ---------------- */
  const columns = [
    {
      key: "deploymentFramework",
      label: "Deployment Framework",
      sortable: false,
      render: (value) => (
        <FrameworkMiniCard
          name={value?.frameworkName}
          description={`Code: ${value?.frameworkCode} | Version: ${value?.frameworkVersion}`}
        />
      ),
    },
    {
      key: "documentName",
      label: "Document Name",
      sortable: false,
      render: (value) => (
        <span
          className="font-medium text-foreground line-clamp-1 max-w-60"
          title={value}
        >
          {value}
        </span>
      ),
    },
    {
      key: "documentType",
      label: "File Info",
      sortable: false,
      render: (value, row) => (
        <div className="max-w-40">
          <FileTypeCard
            fileType={value || row.documentType}
            fileSize={row.fileInfo?.fileSize}
            fileName={row.fileInfo?.originalFileName || row.documentName}
            fileId={row.fileInfo?.versionFileId}
            onDownload={handleDownloadDocument}
            serviceType="deployment-document"
          />
        </div>
      ),
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
      key: "aiExtraction",
      label: "Ai Extraction",
      sortable: false,
      render: (value, row) => <StatusCard item={row.aiExtraction} />,
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
        onClick: () => navigate(`/deployment-documents/${row.id}`),
      },
      {
        id: `update-${row.id}`,
        label: "Update Document",
        icon: "edit",
        onClick: () => handleUpdateDocument(row),
      },
      (!row.aiUpload || !["completed"].includes(row.aiUpload?.status)) && {
        id: `ai-upload-${row.fileInfo?.versionFileId}`,
        label:
          row.aiUpload?.status === "failed" ||
          row.aiUpload?.status === "skipped"
            ? "Retry AI Upload"
            : "Upload to AI",
        icon: "upload-cloud",
        onClick: () => handleUploadToAi(row.id, row.fileInfo?.versionFileId),
        disabled:
          row.aiUpload?.status === "uploaded" ||
          row.aiUpload?.status === "processing",
      },
      {
        id: `delete-${row.id}`,
        label: "Delete Document",
        icon: "trash",
        variant: "destructive",
        onClick: () => handleDeleteDocument(row),
      },
    ].filter(Boolean);

    return (
      <div className="flex justify-center">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () =>
    [
      !(
        isAdmin(user?.role) ||
        isExpert(user?.role) ||
        isCustomerAdmin(user?.role)
      ) && {
        type: "button",
        label: "Add New Document",
        icon: "plus",
        onClick: () => setUploadModalOpen(true),
      },
    ].filter(Boolean);

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <DataTable
        entityName="Documents"
        columns={columns}
        data={deploymentDocuments}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search document name or uploader..."
        emptyMessage={emptyMessage}
        error={error}
      />

      {uploadModalOpen && (
        <UploadDeploymentDocumentModal
          isOpen={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          onSuccess={handleUploadSuccess}
        />
      )}

      {updateModalOpen && documentToUpdate && (
        <UpdateDeploymentDocumentModal
          isOpen={updateModalOpen}
          onClose={() => {
            setUpdateModalOpen(false);
            setDocumentToUpdate(null);
          }}
          onSuccess={handleUpdateSuccess}
          document={documentToUpdate}
        />
      )}

      {documentToDelete && (
        <ConfirmDeleteModal
          open={!!documentToDelete}
          onCancel={handleDeleteCancel}
          onConfirm={handleDeleteConfirm}
          title="Delete Document"
          description="Confirm deletion of deployment document"
          bodyText="Are you sure you want to delete this document? This action cannot be undone."
          entityIcon="document"
          entityName={documentToDelete.documentName}
          badges={[
            {
              text: documentToDelete.documentType?.toUpperCase() || "PDF",
              className:
                "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
            },
            documentToDelete.fileInfo?.fileSize && {
              text: documentToDelete.fileInfo.fileSize,
              className:
                "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
            },
          ].filter(Boolean)}
          metaText={
            documentToDelete.uploadedBy?.name
              ? `Created By: ${documentToDelete.uploadedBy.name}`
              : undefined
          }
        />
      )}
    </div>
  );
}

export default DeploymentDocument;
