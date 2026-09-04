/* eslint-disable react/prop-types */

import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import DeleteVersionModal from "./components/DeleteVersionModal";
import ApproveFrameworkModal from "./components/ApproveFrameworkModal";
import RejectFrameworkModal from "./components/RejectFrameworkModal";
import UpdateFrameworkModal from "./components/UpdateFrameworkModal";
import { ControlModal, DeleteFrameworkModal } from "@/components/custom/modal";
import {
  downloadFrameworkFile,
  getFrameworkById,
  extractFramework,
  deleteFrameworkVersion,
  approveFramework,
  rejectFramework,
  deleteFrameworkControl,
  updateFrameworkControl,
  updateFrameworkControlWeightage,
  addFrameworkControl,
  deleteFramework,
  downloadFrameworkReportPdf,
} from "@/services/frameworkService";

import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/authContext/useAuth";
import {
  getAiExtractionStatusClass,
  getAiExtractionStatusFilterLabel,
  getApprovalStatusClass,
  getApprovalStatusLabel,
  isExpert as isExpertRole,
  STATUS_APPROVED,
  STATUS_EXTRACTED,
  STATUS_FAILED,
  STATUS_PENDING,
  STATUS_PROCESSING,
  STATUS_REJECTED,
  STATUS_UPLOADED,
} from "@/utils/commonUtils";
import { useExpertCategoryAccess } from "@/hooks/useExpertCategoryAccess";
import ControlsPanel from "@/components/custom/ControlsPanel";
import { usePageTitle } from "@/hooks/usePageTitle";
import StatsItemCard from "@/components/custom/StatsItemCard";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { useStatusPolling } from "@/hooks/useStatusPolling";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import UserAvatar from "@/components/custom/UserAvatar";
import FileTypeCard from "@/components/custom/FileTypeCard";
import SearchInput from "@/components/custom/SearchInput";

function FrameworkDetail() {
  const { user } = useAuth();
  const { hasAccessToCategory } = useExpertCategoryAccess();
  const { id } = useParams();
  const navigate = useNavigate();
  const [framework, setFramework] = useState(null);
  const [loading, setLoading] = useState(true);
  const [globalSearch, setGlobalSearch] = useState("");

  const [versionToDelete, setVersionToDelete] = useState(null);
  const [activeAction, setActiveAction] = useState(null); // 'ai'
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [expandedVersions, setExpandedVersions] = useState(new Set());
  const [controlToEdit, setControlToEdit] = useState(null);
  const [controlToDelete, setControlToDelete] = useState(null);
  const [frameworkToDelete, setFrameworkToDelete] = useState(null);
  const [downloading, setDownloading] = useState(false);

  // Reusable hook to handle the dynamic breadcrumb/header title
  usePageTitle(id, "Framework Details");

  // Define fetchFrameworkDetails for manual/initial loads
  const fetchFrameworkDetails = useCallback(
    async (isBackgroundRefresh = false) => {
      try {
        if (!isBackgroundRefresh) {
          setLoading(true);
        }
        const response = await getFrameworkById(id);
        if (response.success) {
          setFramework(response.data);
          return response.data;
        }
      } catch (error) {
        if (!isBackgroundRefresh) {
          toast.error(error.message);
          navigate("/frameworks");
        }
      } finally {
        setLoading(false);
      }
      return null;
    },
    [id, navigate]
  );

  useEffect(() => {
    fetchFrameworkDetails(false);
  }, [fetchFrameworkDetails]);

  // Set all versions as expanded by default when framework loads
  useEffect(() => {
    if (framework?.fileVersions?.length && framework?.currentFileVersion) {
      // Only expand the current version by default
      setExpandedVersions(new Set([framework.currentFileVersion]));
    }
  }, [framework?.fileVersions, framework?.currentFileVersion]);

  // Use custom polling hook for automatic background updates.
  // Polling starts when a version is in-progress (pending/uploaded/processing)
  // and stops automatically once all versions reach a terminal status (extracted/failed).
  const { isTimedOut } = useStatusPolling({
    id,
    pathPattern: "/frameworks/",
    shouldPoll:
      activeAction === "ai" ||
      framework?.fileVersions?.some((v) =>
        [STATUS_UPLOADED, STATUS_PROCESSING].includes(v.aiExtraction?.status)
      ),
    onPoll: async () => {
      const data = await fetchFrameworkDetails(true);
      if (activeAction) setActiveAction(null);
      return data; // hook uses this to detect terminal status
    },
    refreshTrigger: activeAction,
  });

  const handleDownload = async (fileId, fileName) => {
    try {
      await downloadFrameworkFile(framework.id, fileId, fileName);
      toast.success("Download completed successfully");
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleAiExtraction = async (fileId) => {
    try {
      setActiveAction("ai");
      await extractFramework(framework.id, fileId);
      fetchFrameworkDetails(true);
    } catch (error) {
      toast.error(error.message);
      setActiveAction(null);
      fetchFrameworkDetails(true);
    }
  };

  const handleDeleteVersion = (version) => {
    setVersionToDelete(version);
  };

  const handleDeleteConfirm = async () => {
    if (!versionToDelete) return;

    try {
      const response = await deleteFrameworkVersion(
        framework.id,
        versionToDelete.fileId
      );
      if (response.success) {
        toast.success(response.message);
        fetchFrameworkDetails(true);
        setVersionToDelete(null);
      }
    } catch (error) {
      toast.error(error.message);
      throw error; // Re-throw to let modal handle loading state
    }
  };

  const handleDeleteCancel = () => {
    setVersionToDelete(null);
  };

  const handleApprove = () => {
    setShowApproveModal(true);
  };

  const handleApproveConfirm = async () => {
    try {
      const response = await approveFramework(framework.id);
      if (response.success) {
        toast.success(response.message);
        fetchFrameworkDetails(true);
        setShowApproveModal(false);
      }
    } catch (error) {
      toast.error(error.message);
      throw error;
    }
  };

  const handleApproveCancel = () => {
    setShowApproveModal(false);
  };

  const handleRejectConfirm = async (rejectionReason) => {
    try {
      const response = await rejectFramework(framework.id, rejectionReason);
      if (response.success) {
        toast.success(response.message);
        fetchFrameworkDetails(true);
        setShowRejectModal(false);
      }
    } catch (error) {
      toast.error(error.message);
      throw error;
    }
  };

  const handleRejectCancel = () => {
    setShowRejectModal(false);
  };

  const handleUpdate = () => {
    setUpdateModalOpen(true);
  };

  const handleUpdateSuccess = () => {
    fetchFrameworkDetails();
    setUpdateModalOpen(false);
  };

  const handleUpdateCancel = () => {
    setUpdateModalOpen(false);
  };

  const handleDeleteFramework = () => {
    // Normalize framework data to match DeleteFrameworkModal's expected shape
    const currentVersion =
      framework.fileVersions?.find(
        (v) => v.fileVersion === framework.currentFileVersion
      ) || framework.fileVersions?.[0];

    setFrameworkToDelete({
      ...framework,
      frameworkType: currentVersion?.frameworkType,
      fileInfo: {
        fileSize: currentVersion?.fileSize,
      },
      uploadedBy: currentVersion?.uploadedBy || framework.uploadedBy,
    });
  };

  const handleDeleteFrameworkConfirm = async () => {
    if (!frameworkToDelete) return;
    try {
      const result = await deleteFramework(frameworkToDelete.id);
      toast.success(result.message);
      setFrameworkToDelete(null);
      navigate("/frameworks");
    } catch (error) {
      toast.error(error.message);
      throw error;
    }
  };

  const handleDeleteFrameworkCancel = () => {
    setFrameworkToDelete(null);
  };

  const toggleVersion = (version) => {
    setExpandedVersions((prev) => {
      const next = new Set(prev);
      next.has(version) ? next.delete(version) : next.add(version);
      return next;
    });
  };

  const handleEditControl = (control) => {
    setControlToEdit(control);
  };

  const handleEditControlSave = async (updatedControl) => {
    const currentFile = framework.fileVersions.some(
      (file) => file.fileVersion === framework.currentFileVersion
    );

    if (!currentFile) {
      toast.error("Current file version not found");
      return;
    }

    try {
      const response = await updateFrameworkControl(
        framework.id,
        framework.currentFileVersion,
        updatedControl.id,
        {
          name: updatedControl.name,
          description: updatedControl.description,
          deployment_points: updatedControl.deployment_points,
        }
      );

      if (response.success) {
        toast.success(response.message);
        fetchFrameworkDetails(true);
        setControlToEdit(null);
      }
    } catch (error) {
      console.error("Update control error:", error);
      throw error;
    }
  };

  const handleEditControlCancel = () => {
    setControlToEdit(null);
  };

  const handleDeleteControl = (control) => {
    setControlToDelete(control);
  };

  const handleDeleteControlConfirm = async () => {
    if (!controlToDelete) return;

    try {
      const response = await deleteFrameworkControl(
        framework.id,
        framework.currentFileVersion,
        controlToDelete.id
      );

      if (response.success) {
        toast.success(response.message);
        fetchFrameworkDetails(true);
        setControlToDelete(null);
      }
    } catch (error) {
      toast.error(error.message);
      throw error;
    }
  };

  const handleAddControl = async (newControl) => {
    try {
      const response = await addFrameworkControl(
        framework.id,
        framework.currentFileVersion,
        newControl
      );

      if (response.success) {
        toast.success(response.message);
        await fetchFrameworkDetails(true);
        return response;
      }
    } catch (error) {
      console.error("Add control error:", error);
      throw error;
    }
  };

  const handleUpdateWeightage = async (control, weightage) => {
    const toastId = toast.loading("Updating control weightage...");
    try {
      const response = await updateFrameworkControlWeightage(
        framework.id,
        framework.currentFileVersion,
        control.id,
        weightage
      );

      if (response.success) {
        toast.success(response.message, { id: toastId });
        fetchFrameworkDetails(true);
      } else {
        toast.error(response.message, { id: toastId });
      }
    } catch (error) {
      toast.error(error.message, { id: toastId });
    }
  };

  const handleDeleteControlCancel = () => {
    setControlToDelete(null);
  };

  const handleDownloadReport = async () => {
    try {
      setDownloading(true);
      const reportName = `${framework?.frameworkVersion.replace(/[^a-zA-Z0-9]/g, "_")}_report.pdf`;
      await downloadFrameworkReportPdf(framework.id, reportName);
    } catch (error) {
      toast.error(error.message || "Failed to download report");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner className={"min-h-[calc(100vh-100px)]"} />;
  }

  if (!framework) return null;

  // Check if expert has access to this framework's category
  const hasAccess = isExpertRole(user.role)
    ? hasAccessToCategory(framework.frameworkCategoryId)
    : true; // Admin has access to all

  const currentFileVersionData = framework.fileVersions?.find(
    (fv) => fv.fileVersion === framework.currentFileVersion
  );
  const isAiExtracted =
    currentFileVersionData?.aiExtraction?.status === STATUS_EXTRACTED;

  const isExpert = isExpertRole(user.role);
  const isApprovalPending = framework.approval.status === STATUS_PENDING;
  const isApprovalApproved = framework.approval.status === STATUS_APPROVED;
  const isApprovalRejected = framework.approval.status === STATUS_REJECTED;

  return (
    <div className="my-5">
      <Helmet>
        <title>VORA - Framework Details</title>
      </Helmet>
      <div className="space-y-2">
        {/* ===== FRAMEWORK OVERVIEW CARD ===== */}
        <div className="rounded overflow-hidden bg-card border border-border">
          <div className="h-1 bg-linear-to-r from-primary to-secondary" />
          <div className="p-4">
            <div className="flex items-center justify-between gap-3 mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded bg-primary/12 text-primary">
                  <Icon name="shield" size="22px" />
                </div>
                <div>
                  <h2 className="text-lg font-bold">
                    {framework.frameworkName}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Framework Version:{" "}
                    <span className="font-medium text-primary">
                      {framework.frameworkVersion}
                    </span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button
                  size="sm"
                  onClick={handleDownloadReport}
                  disabled={downloading || !isAiExtracted}
                  title={
                    isAiExtracted
                      ? "Download framework report"
                      : "Current file AI extraction must be completed before downloading the report"
                  }
                >
                  <Icon
                    name={downloading ? "loader" : "download"}
                    size="12px"
                    className={downloading ? "animate-spin" : ""}
                  />
                  {downloading ? " Generating..." : " Report"}
                </Button>
                {isExpert && hasAccess && (
                  <>
                    {isApprovalPending && isAiExtracted && hasAccess && (
                      <Button
                        onClick={handleApprove}
                        size="sm"
                        disabled={!hasAccess}
                        className="flex items-center gap-2"
                      >
                        <Icon name="check-circle" size="16px" />
                        Finalise
                      </Button>
                    )}
                    {isApprovalPending && hasAccess && (
                      <Button
                        size="sm"
                        onClick={handleUpdate}
                        disabled={!hasAccess}
                      >
                        <Icon name="edit" size="16px" />
                        Update
                      </Button>
                    )}
                    {framework.approval?.status !== "approved" && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={handleDeleteFramework}
                        disabled={!hasAccess}
                      >
                        <Icon name="trash" size="16px" />
                        Delete
                      </Button>
                    )}
                  </>
                )}
                <Button
                  onClick={() => navigate("/frameworks")}
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <Icon name="arrow-left" size="20px" /> Back
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <StatsItemCard
                icon={<Icon name="tag" size="15px" />}
                label="Current File Version"
                value={
                  <span className="px-3 py-1 rounded text-xs font-bold bg-primary/10 text-primary">
                    v{framework.currentFileVersion}
                  </span>
                }
              />
              <StatsItemCard
                icon={<Icon name="shield" size="15px" />}
                label="Finalize Status"
                value={
                  <span
                    className={`px-3 py-1 rounded text-xs font-bold ${getApprovalStatusClass(framework.approval.status)}`}
                  >
                    {getApprovalStatusLabel(framework.approval.status)}
                  </span>
                }
              />
              <StatsItemCard
                icon={<Icon name="calendar" size="15px" />}
                label="Created On"
                value={
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
                    {formatDateWithMonthNameAndTime(framework.createdAt)}
                  </span>
                }
              />
              <StatsItemCard
                icon={<Icon name="clock" size="15px" />}
                label="Last Updated On"
                value={
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
                    {formatDateWithMonthNameAndTime(framework.updatedAt)}
                  </span>
                }
              />
              <StatsItemCard
                icon={<Icon name="cloud-upload" size="15px" />}
                label="Uploaded By"
                value={
                  <div className="flex items-center gap-1">
                    <UserAvatar user={framework.uploadedBy} />
                    <div className="flex flex-col">
                      <span className="text-sm text-muted-foreground whitespace-nowrap font-medium">
                        {framework.uploadedBy?.name}
                      </span>
                      <span className="text-[12px] text-muted-foreground">
                        {framework.uploadedBy?.email}
                      </span>
                    </div>
                  </div>
                }
              />
            </div>

            {/* Show rejection reason if framework is rejected */}
            {isApprovalRejected && framework.approval.rejectionReason && (
              <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-4">
                <div className="flex gap-3">
                  <Icon
                    name="x-circle"
                    size="20px"
                    className="text-red-600 dark:text-red-400 mt-0.5 shrink-0"
                  />
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-red-800 dark:text-red-200 mb-1">
                      Rejection Reason
                    </h4>
                    <p className="text-sm text-red-700 dark:text-red-300 leading-relaxed">
                      {framework.approval.rejectionReason}
                    </p>
                    {framework.approval.approvedBy && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                        Rejected by: {framework.approval.approvedBy.name} .{" "}
                        {framework.approval.approvedBy.role} on{" "}
                        {formatDateWithMonthNameAndTime(
                          framework.approval.approvedAt
                        )}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Show approval info if framework is approved */}
            {isApprovalApproved && framework.approval.approvedBy && (
              <div className="mt-4 bg-primary/10 border border-primary/30 rounded p-4">
                <div className="flex gap-3">
                  <Icon
                    name="check-circle"
                    size="20px"
                    className="text-primary mt-0.5 shrink-0"
                  />
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-foreground mb-1">
                      Framework Approved
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Approved by: {framework.approval.approvedBy.name} .{" "}
                      <span className="capitalize">
                        {framework.approval.approvedBy.role}
                      </span>{" "}
                      .{" "}
                      {formatDateWithMonthNameAndTime(
                        framework.approval.approvedAt
                      )}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ===== FILE VERSIONS ===== */}
        <div>
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="text-xl font-bold">File Versions</h2>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-primary/15 text-primary">
              {framework.fileVersions?.length || 0} files
            </span>
          </div>

          <div className="space-y-3">
            {framework.fileVersions?.map((ver) => {
              const isCurrent =
                ver.fileVersion === framework.currentFileVersion;
              const isExpanded = expandedVersions.has(ver.fileVersion);
              const isAiExtracted =
                ver.aiExtraction.status === STATUS_EXTRACTED;
              const isAiUploaded = ver.aiExtraction.status === STATUS_UPLOADED;
              const isAiExtractionProcessing =
                ver.aiExtraction.status === STATUS_PROCESSING;
              const isAiFailed = ver.aiExtraction.status === STATUS_FAILED;
              const totaleControls = ver.aiExtraction?.controls?.total_controls;
              const isAiActive =
                (activeAction === "ai" ||
                  isAiUploaded ||
                  isAiExtractionProcessing) &&
                !isTimedOut;

              return (
                <div
                  key={ver.fileVersion}
                  className={`rounded overflow-hidden transition-all duration-300 hover:shadow-lg bg-card ${
                    isCurrent ? "border border-primary" : "border border-border"
                  }`}
                >
                  <div className="w-full flex items-center justify-between p-2 transition-colors duration-200 text-foreground ">
                    <div className="flex-1 flex items-center gap-5 flex-wrap">
                      <span
                        className={`px-3 py-2 rounded text-xs font-bold ${
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
                          fileType={ver.frameworkType}
                          fileSize={ver.fileSize}
                          fileName={ver.originalFileName}
                          fileId={ver.fileId}
                          onDownload={() =>
                            handleDownload(ver.fileId, ver.originalFileName)
                          }
                          serviceType="framework"
                          frameworkId={framework.id}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="border border-border rounded p-1.5 flex items-center justify-center">
                          <Icon
                            name="ai-bot"
                            size="16px"
                            className="text-primary"
                          />
                        </div>
                        <div className="flex flex-col gap-0">
                          <span className="text-sm font-medium text-foreground">
                            AI Extraction
                          </span>
                          <div className="flex items-center gap-1">
                            <span
                              className={`w-fit px-2 py-0.5 rounded text-[10px] font-bold ${getAiExtractionStatusClass(
                                ver.aiExtraction.status
                              )}`}
                            >
                              {getAiExtractionStatusFilterLabel(
                                ver.aiExtraction.status
                              )}
                            </span>
                            {ver.aiExtraction.status === STATUS_FAILED &&
                              ver.aiExtraction.message && (
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <span className="cursor-pointer flex items-center">
                                        <Icon
                                          name="info"
                                          size="13px"
                                          className="text-red-500"
                                        />
                                      </span>
                                    </TooltipTrigger>
                                    <TooltipContent
                                      side="top"
                                      className="max-w-[60vw] text-center"
                                    >
                                      {ver.aiExtraction.message}
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              )}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {framework.fileVersions.length > 1 && isExpert && (
                        <Button
                          variant="destructive"
                          size="xs"
                          onClick={() => handleDeleteVersion(ver)}
                          disabled={!hasAccess}
                          className="flex items-center gap-2"
                        >
                          <Icon name="trash" size="15px" />
                          Delete Version
                        </Button>
                      )}

                      {isExpert &&
                        isCurrent &&
                        (!isAiExtracted ||
                          isApprovalRejected ||
                          totaleControls === 0) && (
                          <Button
                            variant="secondary"
                            size="xs"
                            onClick={() => handleAiExtraction(ver.fileId)}
                            disabled={!hasAccess || isAiActive}
                          >
                            {isAiActive ? (
                              <>
                                <Icon
                                  name="loader"
                                  size="13px"
                                  className="animate-spin"
                                />
                                {isAiExtractionProcessing
                                  ? "Processing..."
                                  : "Uploading..."}
                              </>
                            ) : (
                              <>
                                <Icon name="upload-cloud" size="13px" />
                                {isAiFailed ||
                                isApprovalRejected ||
                                totaleControls === 0
                                  ? "Retry Extraction"
                                  : "Extract"}
                              </>
                            )}
                          </Button>
                        )}
                      {ver.aiExtraction?.controls?.controls_data?.length >
                        0 && (
                        <SearchInput
                          value={globalSearch}
                          onChange={setGlobalSearch}
                          onClear={() => setGlobalSearch("")}
                          placeholder="Search Sections, Controls & DPs..."
                          className="w-70 h-8 text-xs"
                        />
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleVersion(ver.fileVersion)}
                        className="ml-2"
                        aria-label={isExpanded ? "Collapse" : "Expand"}
                      >
                        {isExpanded ? (
                          <Icon name="chevron-up" size="18px" />
                        ) : (
                          <Icon name="chevron-down" size="18px" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {isExpanded &&
                    ver.aiExtraction?.controls?.controls_data?.length > 0 && (
                      <div className="p-2 border-t border-border">
                        <ControlsPanel
                          sections={ver.aiExtraction.controls.controls_data}
                          totalControls={
                            ver.aiExtraction.controls.total_controls
                          }
                          totalSections={
                            ver.aiExtraction.controls.total_sections
                          }
                          onEdit={handleEditControl}
                          onDelete={handleDeleteControl}
                          onAdd={handleAddControl}
                          onUpdateWeightage={handleUpdateWeightage}
                          canModify={
                            ver.fileVersion === framework.currentFileVersion &&
                            !isApprovalApproved
                          }
                          showApplicability={false}
                          globalSearch={globalSearch}
                        />
                      </div>
                    )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Delete Version Modal */}
      {versionToDelete && (
        <DeleteVersionModal
          version={versionToDelete}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
        />
      )}

      {/* Approve Framework Modal */}
      {showApproveModal && framework && (
        <ApproveFrameworkModal
          framework={framework}
          onConfirm={handleApproveConfirm}
          onCancel={handleApproveCancel}
        />
      )}

      {/* Reject Framework Modal */}
      {showRejectModal && framework && (
        <RejectFrameworkModal
          framework={framework}
          onConfirm={handleRejectConfirm}
          onCancel={handleRejectCancel}
        />
      )}

      {/* Update Framework Modal */}
      {updateModalOpen && (
        <UpdateFrameworkModal
          isOpen={updateModalOpen}
          onClose={handleUpdateCancel}
          onSuccess={handleUpdateSuccess}
          framework={framework}
        />
      )}

      {/* Edit Control Modal */}
      {controlToEdit && (
        <ControlModal
          type="edit"
          control={controlToEdit}
          onSave={handleEditControlSave}
          onCancel={handleEditControlCancel}
        />
      )}

      {/* Delete Control Modal */}
      {controlToDelete && (
        <ControlModal
          type="delete"
          control={controlToDelete}
          onConfirm={handleDeleteControlConfirm}
          onCancel={handleDeleteControlCancel}
        />
      )}

      {/* Delete Framework Modal */}
      {frameworkToDelete && (
        <DeleteFrameworkModal
          open={!!frameworkToDelete}
          onCancel={handleDeleteFrameworkCancel}
          onConfirm={handleDeleteFrameworkConfirm}
          framework={frameworkToDelete}
        />
      )}
    </div>
  );
}

export default FrameworkDetail;
