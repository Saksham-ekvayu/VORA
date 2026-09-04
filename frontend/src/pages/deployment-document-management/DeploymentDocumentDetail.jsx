/* eslint-disable react/prop-types */

import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import DeleteVersionModal from "./components/DeleteVersionModal";
import UpdateDeploymentDocumentModal from "./components/UpdateDeploymentDocumentModal";
import {
  downloadDeploymentDocumentFile,
  getDeploymentDocumentById,
  deleteDeploymentDocumentVersion,
  uploadDeploymentDocumentToAi,
} from "@/services/deploymentDocumentService";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/authContext/useAuth";
import { isCustomerAdmin, isUser } from "@/utils/commonUtils";
import { usePageTitle } from "@/hooks/usePageTitle";
import StatsItemCard from "@/components/custom/StatsItemCard";
import { useStatusPolling } from "@/hooks/useStatusPolling";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import DeploymentDocumentControlsPanel from "./components/custom/DeploymentDocumentControlsPanel";
import FileTypeCard from "@/components/custom/FileTypeCard";

// ========== MAIN COMPONENT ==========
function DeploymentDocumentDetail() {
  const { user } = useAuth();
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [versionToDelete, setVersionToDelete] = useState(null);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [expandedVersions, setExpandedVersions] = useState(new Set());
  const [activeAction, setActiveAction] = useState(null); // 'ai'

  // Reusable hook to handle the dynamic breadcrumb/header title
  usePageTitle(id, document?.documentName);

  // Fetch document details
  const fetchDocumentDetails = useCallback(
    async (isBackground = false) => {
      try {
        if (!isBackground) setLoading(true);
        const response = await getDeploymentDocumentById(id);

        if (response.success) {
          setDocument(response.data.document);
        }
      } catch (error) {
        if (!isBackground) {
          toast.error(error.message || "Failed to fetch document details");
          navigate("/deployment-documents");
        }
      } finally {
        if (!isBackground) setLoading(false);
      }
    },
    [id, navigate]
  );

  useEffect(() => {
    fetchDocumentDetails(false);
  }, [fetchDocumentDetails]);

  // Use status polling hook for automatic background updates
  const { isTimedOut } = useStatusPolling({
    id,
    pathPattern: "/deployment-documents/",
    shouldPoll:
      activeAction ||
      document?.fileVersions?.some((v) =>
        ["uploaded", "processing"].includes(v.aiUpload?.status)
      ),
    onPoll: async () => {
      await fetchDocumentDetails(true);
      if (activeAction) setActiveAction(null);
    },
    refreshTrigger: activeAction,
  });

  useEffect(() => {
    if (document?.fileVersions?.length && document?.currentFileVersion) {
      // Only expand the current version by default
      setExpandedVersions(new Set([document.currentFileVersion]));
    }
  }, [document?.fileVersions, document?.currentFileVersion]);

  // ========== HANDLERS ==========
  const handleDownload = async (fileId, fileName) => {
    try {
      await downloadDeploymentDocumentFile(document.id, fileId, fileName);
      toast.success("Download completed successfully");
    } catch (error) {
      toast.error(error.message || "Failed to download file");
    }
  };

  const handleDeleteVersion = (version) => {
    setVersionToDelete(version);
  };

  const handleDeleteConfirm = async () => {
    if (!versionToDelete) return;
    try {
      const response = await deleteDeploymentDocumentVersion(
        document.id,
        versionToDelete.fileId
      );
      if (response.success) {
        toast.success(response.message || "Version deleted successfully");
        await fetchDocumentDetails();
        setVersionToDelete(null);
      }
    } catch (error) {
      toast.error(error.message || "Failed to delete version");
      throw error;
    }
  };

  const toggleVersion = (version) => {
    setExpandedVersions((prev) => {
      const next = new Set(prev);
      next.has(version) ? next.delete(version) : next.add(version);
      return next;
    });
  };

  const handleUploadToAi = async (fileId) => {
    try {
      setActiveAction("ai");
      await uploadDeploymentDocumentToAi(document.id, fileId);
      fetchDocumentDetails(true);
    } catch (error) {
      toast.error(error.message || "Failed to upload to AI");
      setActiveAction(null);
      fetchDocumentDetails(true);
    }
  };

  if (loading) {
    return <LoadingSpinner className={"min-h-[calc(100vh-100px)]"} />;
  }

  if (!document) return null;

  const getAiStatusClass = (status) => {
    if (status === "completed") return "bg-green-500/15 text-green-600";
    if (status === "uploaded" || status === "processing")
      return "bg-blue-500/15 text-blue-600";
    if (status === "failed") return "bg-red-500/15 text-red-600";
    return "bg-yellow-500/15 text-yellow-600";
  };

  return (
    <div className="min-h-screen bg-background text-foreground my-5">
      <Helmet>
        <title>VORA - Deployment Document Details</title>
      </Helmet>
      <div className="space-y-6">
        {/* Document Overview Card */}
        <div className="rounded overflow-hidden bg-card border border-border">
          <div className="h-1 bg-linear-to-r from-primary to-secondary" />
          <div className="p-2">
            <div className="flex items-center justify-between gap-3 mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded bg-primary/12 text-primary">
                  <Icon name="file" size="22px" />
                </div>
                <div>
                  <h2 className="text-lg font-bold">{document.documentName}</h2>
                  <p className="text-xs text-muted-foreground">
                    Document Overview
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button onClick={() => setUpdateModalOpen(true)}>
                  <Icon name="edit" size="16px" /> Update Document
                </Button>
                <Button
                  onClick={() => navigate(-1)}
                  className="flex items-center gap-2"
                >
                  <Icon name="arrow-left" size="20px" /> Back
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatsItemCard
                icon={<Icon name="tag" size="15px" />}
                label="Current Version"
                value={
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-primary/15 text-primary">
                    v{document.currentFileVersion}
                  </span>
                }
              />
              <StatsItemCard
                icon={<Icon name="calendar" size="15px" />}
                label="Created On"
                value={
                  <span className="text-sm font-medium">
                    {formatDateWithMonthNameAndTime(document.createdAt)}
                  </span>
                }
              />
              <StatsItemCard
                icon={<Icon name="clock" size="15px" />}
                label="Last Updated On"
                value={
                  <span className="text-sm font-medium">
                    {formatDateWithMonthNameAndTime(document.updatedAt)}
                  </span>
                }
              />
              <StatsItemCard
                icon={<Icon name="upload-cloud" size="15px" />}
                label="AI Extraction"
                value={
                  document.fileVersions?.[0]?.aiUpload ? (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold ${getAiStatusClass(document.fileVersions[0].aiUpload.status)}`}
                    >
                      {document.fileVersions[0].aiUpload.status}
                    </span>
                  ) : (
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-gray-500/15 text-gray-600">
                      Not Uploaded
                    </span>
                  )
                }
              />
            </div>
          </div>
        </div>

        {/* File Versions */}
        <div>
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="text-xl font-bold">File Versions</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-primary/15 text-primary">
              {document.fileVersions?.length || 0} files
            </span>
          </div>

          <div className="space-y-3">
            {document.fileVersions?.map((ver) => {
              const isCurrent = ver.fileVersion === document.currentFileVersion;
              const isExpanded = expandedVersions.has(ver.fileVersion);
              const isAiUploadProcessing =
                ver.aiUpload?.status === "uploaded" ||
                ver.aiUpload?.status === "processing";
              const isAiActive =
                (activeAction === "ai" || isAiUploadProcessing) && !isTimedOut;

              return (
                <div
                  key={ver.fileVersion}
                  className={`rounded overflow-hidden transition-all duration-300 hover:shadow-lg bg-card ${
                    isCurrent ? "border border-primary" : "border border-border"
                  }`}
                >
                  {/* Header */}
                  <div className="w-full flex items-center justify-between p-2">
                    <button
                      onClick={() => toggleVersion(ver.fileVersion)}
                      className="flex-1 flex items-center gap-3 flex-wrap cursor-pointer"
                    >
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-bold ${
                          isCurrent
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        v{ver.fileVersion}
                        {isCurrent && " • Current"}
                      </span>
                      <div className="">
                        <FileTypeCard
                          fileType={ver.documentType}
                          fileSize={ver.fileSize}
                          fileName={ver.originalFileName}
                          fileId={ver.fileId}
                          onDownload={() =>
                            handleDownload(ver.fileId, ver.originalFileName)
                          }
                          serviceType="deployment-document"
                        />
                      </div>
                    </button>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {/* AI Upload Button */}
                      {(isCustomerAdmin(user.role) || isUser(user.role)) &&
                        (!ver.aiUpload ||
                          !["completed"].includes(ver.aiUpload?.status)) && (
                          <Button
                            variant="secondary"
                            onClick={() => handleUploadToAi(ver.fileId)}
                            disabled={isAiActive}
                          >
                            {isAiActive ? (
                              <>
                                <Icon
                                  name="loader"
                                  size="13px"
                                  className="animate-spin"
                                />
                                {ver.aiUpload?.status === "processing"
                                  ? "Processing..."
                                  : "Uploading..."}
                              </>
                            ) : (
                              <>
                                <Icon name="upload-cloud" size="13px" />
                                {ver.aiUpload?.status === "failed" ||
                                ver.aiUpload?.status === "skipped"
                                  ? "Retry AI Upload"
                                  : "Upload to AI"}
                              </>
                            )}
                          </Button>
                        )}

                      {document.fileVersions.length > 1 && (
                        <Button
                          variant="destructive"
                          onClick={() => handleDeleteVersion(ver)}
                        >
                          <Icon name="trash" size="15px" /> Delete
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => toggleVersion(ver.fileVersion)}
                      >
                        {isExpanded ? (
                          <Icon name="chevron-up" size="18px" />
                        ) : (
                          <Icon name="chevron-down" size="18px" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && ver.aiUpload && (
                    <div className="p-2 max-h-100 overflow-y-auto border-t border-border">
                      {ver.aiUpload?.status === "completed" &&
                        ver.aiUpload?.controls?.controls_data?.length > 0 && (
                          <DeploymentDocumentControlsPanel
                            controls={
                              ver.aiUpload?.controls?.controls_data || []
                            }
                            totalControls={
                              ver.aiUpload?.controls?.total_controls || 0
                            }
                            onEdit={null} // Documents don't support editing controls yet
                            onDelete={null} // Documents don't support deleting controls yet
                            canEdit={false} // Disable editing for documents
                          />
                        )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Modals */}
      {versionToDelete && (
        <DeleteVersionModal
          version={versionToDelete}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setVersionToDelete(null)}
        />
      )}

      {updateModalOpen && (
        <UpdateDeploymentDocumentModal
          isOpen={updateModalOpen}
          onClose={() => setUpdateModalOpen(false)}
          onSuccess={() => {
            fetchDocumentDetails();
            setUpdateModalOpen(false);
          }}
          document={document}
        />
      )}
    </div>
  );
}

export default DeploymentDocumentDetail;
