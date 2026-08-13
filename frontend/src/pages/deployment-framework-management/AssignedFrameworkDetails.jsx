/* eslint-disable react/prop-types */

import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import { downloadFrameworkFile } from "@/services/frameworkService";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { Button } from "@/components/ui/button";
import { usePageTitle } from "@/hooks/usePageTitle";
import { useAuth } from "@/context/authContext/useAuth";
import {
  getAssignedFrameworkApprovalStatusClass,
  getAssignedFrameworkApprovalStatusLabel,
  ROLE_AUDITOR,
} from "@/utils/commonUtils";

import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import UserAvatar from "@/components/custom/UserAvatar";
import FileTypeCard from "@/components/custom/FileTypeCard";
import ControlsPanel from "@/components/custom/ControlsPanel";
import { ControlModal } from "@/components/custom/modal";
import AssignmentHistoryModal from "./components/AssignmentHistoryModal";
import FinalizeFrameworkVersionModal from "./components/FinalizeFrameworkVersionModal";
import {
  addAssignmentFrameworkControl,
  deleteAssignmentFrameworkControl,
  getAssignedFrameworksById,
  updateAssignmentFrameworkControl,
  updateAssignmentFrameworkControlApplicability,
  updateAssignmentFrameworkControlWeightage,
  finalizeAssignmentFramework,
  downloadAssignedFrameworkReport,
} from "@/services/deploymentFrameworkService";

const FRAMEWORK_ID_NOT_FOUND = "Framework ID not found";
const CANNOT_MODIFY_FINALIZED =
  "Cannot modify controls on a finalized version.";

const OverviewActions = ({
  framework,
  setShowHistoryModal,
  navigate,
  canFinalize,
  onFinalize,
  onDownloadReport,
  isDownloadingReport,
}) => (
  <div className="flex flex-wrap items-center justify-end gap-2">
    <Button
      size="sm"
      variant="outline"
      className={`${getAssignedFrameworkApprovalStatusClass(framework?.status)}`}
    >
      {getAssignedFrameworkApprovalStatusLabel(framework?.status)}
    </Button>

    {canFinalize && (
      <Button
        size="sm"
        className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-1"
        onClick={onFinalize}
        title="Finalize Framework Version"
      >
        <Icon name="lock" size="12px" /> Finalize Framework
      </Button>
    )}

    <Button
      size="sm"
      onClick={onDownloadReport}
      disabled={isDownloadingReport}
      title="Download assigned framework report"
    >
      <Icon
        name={isDownloadingReport ? "loader" : "download"}
        size="12px"
        className={isDownloadingReport ? "animate-spin" : ""}
      />
      {isDownloadingReport ? " Generating..." : " Report"}
    </Button>

    <Button
      size="sm"
      variant="outline"
      onClick={() => setShowHistoryModal(true)}
      title="View assignment history"
    >
      <Icon name="history" size="12px" />
      Assignment History
    </Button>

    <Button
      size="sm"
      onClick={() => navigate("/assigned-frameworks")}
      title="Go back"
    >
      <Icon name="arrow-left" size="12px" /> Back
    </Button>
  </div>
);

const PersonSummary = ({ user, date, emptyLabel = "System / Unknown" }) => (
  <div className="min-w-0">
    {user ? (
      <div className="flex items-center gap-3">
        <UserAvatar user={user} size="lg" className="shrink-0" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">
            {user.name}
          </p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          {date && (
            <p className="mt-1 text-[11px] font-medium text-muted-foreground">
              {formatDateWithMonthNameAndTime(date)}
            </p>
          )}
        </div>
      </div>
    ) : (
      <p className="text-xs italic text-muted-foreground">{emptyLabel}</p>
    )}
  </div>
);

const showToast = (silent, type, message, id) => {
  if (silent) return null;
  if (type === "loading") return toast.loading(message);
  if (type === "success") {
    return toast.success(message, { id });
  }
  return toast.error(message, { id });
};

const updateControlApplicabilityWithToasts = async ({
  frameworkId,
  currentFileVersion,
  controlIds,
  isApplicable,
  silent,
  onRefresh,
}) => {
  if (!frameworkId) {
    showToast(silent, "error", FRAMEWORK_ID_NOT_FOUND);
    return;
  }

  const ids = Array.isArray(controlIds) ? controlIds : [controlIds];
  const loadingMsg = isApplicable
    ? "Marking control(s) as applicable..."
    : "Marking control(s) as not applicable...";
  const toastId = showToast(silent, "loading", loadingMsg);

  try {
    const response = await updateAssignmentFrameworkControlApplicability(
      frameworkId,
      currentFileVersion,
      ids,
      isApplicable
    );
    if (response.success) {
      showToast(
        silent,
        "success",
        response.message || "Control applicability updated",
        toastId
      );
      await onRefresh();
    } else {
      showToast(
        silent,
        "error",
        response.message || "Failed to update control applicability",
        toastId
      );
    }
  } catch (error) {
    showToast(
      silent,
      "error",
      error.message || "Failed to update control applicability",
      toastId
    );
  }
};

const statusBanner = (framework) => {
  const status = framework.status;

  if (status === "revoked") {
    return (
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-4 py-2 rounded border bg-red-500/10 border-red-500/15 text-red-700 dark:text-red-300 text-xs">
        <div className="flex items-center gap-2">
          <Icon
            name="x-circle"
            size="14px"
            className="text-red-600 dark:text-red-400 shrink-0"
          />
          <span className="font-semibold">
            This framework assignment has been revoked.
          </span>
        </div>
        {framework.revocation?.revokedBy && (
          <div className="flex items-center gap-1 text-red-700/80 dark:text-red-400/80">
            <span>Revoked by</span>
            <span className="font-semibold text-red-900 dark:text-red-200">
              {framework.revocation.revokedBy.name}
            </span>
            <span>on</span>
            <span className="font-semibold text-red-900 dark:text-red-200">
              {formatDateWithMonthNameAndTime(framework.revocation.revokedAt)}
            </span>
          </div>
        )}
      </div>
    );
  } else if (framework.finalization?.isFinalized ?? false) {
    return (
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-4 py-2 rounded border bg-emerald-500/5 border-emerald-500/15 dark:border-emerald-500/10 text-emerald-800 dark:text-emerald-300 text-xs">
        <div className="flex items-center gap-2">
          <Icon
            name="lock"
            size="14px"
            className="text-emerald-600 dark:text-emerald-400 shrink-0"
          />
          <span className="font-semibold">
            This framework version is finalized and locked.
          </span>
        </div>
        {framework.finalization?.finalizedBy && (
          <div className="flex items-center gap-1 text-emerald-700/80 dark:text-emerald-400/80">
            <span>Finalized by</span>
            <span className="font-semibold text-emerald-900 dark:text-emerald-200">
              {framework.finalization.finalizedBy.name}
            </span>
            <span>on</span>
            <span className="font-semibold text-emerald-900 dark:text-emerald-200">
              {formatDateWithMonthNameAndTime(
                framework.finalization.finalizedAt
              )}
            </span>
          </div>
        )}
      </div>
    );
  } else {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded border bg-amber-500/5 border-amber-500/15 dark:border-amber-500/10 text-amber-800 dark:text-amber-300 text-xs">
        <Icon
          name="hourglass"
          size="14px"
          className="text-amber-600 dark:text-amber-400 shrink-0"
        />
        <div className="flex flex-col sm:flex-row sm:items-center gap-1">
          <span className="font-semibold">Finalization Pending:</span>
          <span className="text-amber-700/80 dark:text-amber-400/80">
            Controls, weightages, and applicability can still be customized for
            this version.
          </span>
        </div>
      </div>
    );
  }
};

function AssignedFrameworkDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isUserAuditor = user?.role === ROLE_AUDITOR;
  const [framework, setFramework] = useState(null);
  const [loading, setLoading] = useState(true);
  const [controlToEdit, setControlToEdit] = useState(null);
  const [controlToDelete, setControlToDelete] = useState(null);

  const [expandedVersions, setExpandedVersions] = useState(new Set());
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showFinalizeModal, setShowFinalizeModal] = useState(false);
  const [isDownloadingReport, setIsDownloadingReport] = useState(false);

  // Reusable hook to handle the dynamic breadcrumb/header title
  usePageTitle(id, "Assigned Framework Details");

  // Define fetchFrameworkDetails for manual/initial loads
  const fetchFrameworkDetails = useCallback(
    async (isBackgroundRefresh = false) => {
      try {
        if (!isBackgroundRefresh) {
          setLoading(true);
        }
        const response = await getAssignedFrameworksById(id);
        if (response.success) {
          setFramework(response.data);
        }
      } catch (error) {
        if (!isBackgroundRefresh) {
          toast.error(error.message || "Failed to fetch framework details");
          navigate("/assigned-frameworks");
        }
      } finally {
        setLoading(false);
      }
    },
    [id, navigate]
  );

  useEffect(() => {
    fetchFrameworkDetails(false);
  }, [fetchFrameworkDetails]);

  const isCurrentVersionFinalized =
    framework?.finalization?.isFinalized ?? false;

  const canFinalize =
    user?.role === ROLE_AUDITOR &&
    !isCurrentVersionFinalized &&
    framework?.status !== "revoked";

  const handleFinalize = () => {
    setShowFinalizeModal(true);
  };

  const handleFinalizeConfirm = async () => {
    const toastId = toast.loading("Finalizing framework version...");
    try {
      const response = await finalizeAssignmentFramework(framework.id);
      if (response.success) {
        toast.success(
          response.message || "Framework version finalized successfully.",
          { id: toastId }
        );
        await fetchFrameworkDetails();
        setShowFinalizeModal(false);
      } else {
        toast.error(
          response.message || "Failed to finalize framework version.",
          { id: toastId }
        );
      }
    } catch (error) {
      toast.error(error.message || "Failed to finalize framework version.", {
        id: toastId,
      });
    }
  };

  // Set all versions as expanded by default when framework loads
  useEffect(() => {
    if (framework?.fileVersions?.length && framework?.currentFileVersion) {
      // Only expand the current version by default
      setExpandedVersions(new Set([framework.currentFileVersion]));
    }
  }, [framework?.fileVersions, framework?.currentFileVersion]);

  const handleDownload = async (fileId, fileName) => {
    try {
      await downloadFrameworkFile(framework.frameworkId, fileId, fileName);
    } catch (error) {
      toast.error(error.message || "Failed to download file");
    }
  };

  const handleDownloadReport = async () => {
    if (!framework?.id) return;

    setIsDownloadingReport(true);
    try {
      await downloadAssignedFrameworkReport(
        framework.id,
        framework.currentFileVersion,
        `${framework?.frameworkVersion.replace(/[^a-zA-Z0-9]/g, "_")}_report.pdf`
      );
    } catch (error) {
      toast.error(
        error.message || "Failed to download assigned framework report"
      );
    } finally {
      setIsDownloadingReport(false);
    }
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
    if (!framework?.id) {
      throw new Error(FRAMEWORK_ID_NOT_FOUND);
    }

    if (isCurrentVersionFinalized) {
      toast.error(CANNOT_MODIFY_FINALIZED);
      return;
    }

    try {
      const response = await updateAssignmentFrameworkControl(
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
        toast.success(response.message || "Control updated successfully");
        fetchFrameworkDetails();
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

    if (isCurrentVersionFinalized) {
      toast.error(CANNOT_MODIFY_FINALIZED);
      return;
    }

    try {
      if (!framework?.id) {
        toast.error(FRAMEWORK_ID_NOT_FOUND);
        return;
      }

      const response = await deleteAssignmentFrameworkControl(
        framework.id,
        framework.currentFileVersion,
        controlToDelete.id
      );

      if (response.success) {
        toast.success(response.message || "Control deleted successfully");
        fetchFrameworkDetails();
        setControlToDelete(null);
      }
    } catch (error) {
      toast.error(error.message || "Failed to delete control");
    }
  };

  const handleAddControl = async (newControl) => {
    if (!framework?.id) {
      throw new Error(FRAMEWORK_ID_NOT_FOUND);
    }

    if (isCurrentVersionFinalized) {
      toast.error(CANNOT_MODIFY_FINALIZED);
      throw new Error(CANNOT_MODIFY_FINALIZED);
    }

    try {
      const response = await addAssignmentFrameworkControl(
        framework.id,
        framework.currentFileVersion,
        newControl
      );

      if (response.success) {
        toast.success(response.message || "Control added successfully");
        await fetchFrameworkDetails();
        return response;
      }
    } catch (error) {
      console.error("Add control error:", error);
      throw error;
    }
  };

  const handleUpdateControlApplicability = async (
    controlIds,
    isApplicable,
    silent = false
  ) => {
    if (isCurrentVersionFinalized) {
      toast.error(CANNOT_MODIFY_FINALIZED);
      return;
    }

    await updateControlApplicabilityWithToasts({
      frameworkId: framework?.id,
      currentFileVersion: framework?.currentFileVersion,
      controlIds,
      isApplicable,
      silent,
      onRefresh: () => fetchFrameworkDetails(true),
    });
  };

  const handleUpdateControlWeightage = async (control, value) => {
    if (!framework?.id) {
      toast.error(FRAMEWORK_ID_NOT_FOUND);
      return;
    }

    if (isCurrentVersionFinalized) {
      toast.error(CANNOT_MODIFY_FINALIZED);
      return;
    }

    const toastId = toast.loading(
      `Updating weightage for control ${control.id}...`
    );

    try {
      const response = await updateAssignmentFrameworkControlWeightage(
        framework.id,
        framework.currentFileVersion,
        control.id,
        { customer_weightage: value }
      );

      if (response.success) {
        toast.success(
          response.message || "Control weightage updated successfully",
          { id: toastId }
        );
        await fetchFrameworkDetails(true);
      } else {
        toast.error(response.message || "Failed to update control weightage", {
          id: toastId,
        });
      }
    } catch (error) {
      toast.error(error.message || "Failed to update control weightage", {
        id: toastId,
      });
    }
  };

  const handleDeleteControlCancel = () => {
    setControlToDelete(null);
  };

  if (loading) {
    return <LoadingSpinner className={"min-h-[calc(100vh-100px)]"} />;
  }

  if (!framework) return null;

  // Determine which event is latest for assignment/revocation card
  const assignedAt = new Date(framework.assignment?.assignedAt);
  const revokedAt = framework.revocation?.revokedAt
    ? new Date(framework.revocation.revokedAt)
    : null;
  const isRevokedLatest = revokedAt && revokedAt > assignedAt;

  return (
    <div className="min-h-screen bg-background text-foreground my-5">
      <div className="space-y-4">
        {/* ===== ASSIGNMENT OVERVIEW ===== */}
        <section className="">
          <div className="flex flex-col gap-4 border-b border-border pb-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <h1 className="truncate text-lg font-bold text-foreground sm:text-xl">
                {framework.frameworkName}
              </h1>
            </div>
            <OverviewActions
              framework={framework}
              setShowHistoryModal={setShowHistoryModal}
              navigate={navigate}
              canFinalize={canFinalize}
              onFinalize={handleFinalize}
              onDownloadReport={handleDownloadReport}
              isDownloadingReport={isDownloadingReport}
            />
          </div>

          <div className="grid grid-cols-1 divide-y divide-border md:grid-cols-[0.8fr_1.25fr_1.25fr] md:divide-x md:divide-y-0">
            <div className="px-4 py-4">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Version
              </p>
              <div className="flex flex-wrap gap-x-6 gap-y-2">
                <div>
                  <p className="text-[11px] text-muted-foreground">Framework</p>
                  <p className="text-sm font-semibold text-foreground">
                    {framework.frameworkVersion}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground">
                    Current file
                  </p>
                  <p className="text-sm font-semibold text-foreground">
                    v{framework.currentFileVersion}
                  </p>
                </div>
              </div>
            </div>

            {framework.customer && (
              <div className="px-4 py-4">
                <div className="mb-3 flex items-center gap-2">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    Customer
                  </p>
                  {framework.customer.isActive !== null && (
                    <span
                      className={`rounded-full px-2 py-0.5 text-[9px] font-extrabold uppercase ${
                        framework.customer.isActive
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                          : "bg-red-500/15 text-red-600 dark:text-red-400"
                      }`}
                    >
                      {framework.customer.isActive ? "Active" : "Inactive"}
                    </span>
                  )}
                </div>
                <PersonSummary user={framework.customer} />
                {framework.customer.phone && (
                  <p className="mt-2 pl-11 text-xs text-muted-foreground">
                    {framework.customer.phone}
                  </p>
                )}
              </div>
            )}

            <div className="px-4 py-4">
              <p
                className={`mb-3 text-[10px] font-bold uppercase tracking-wider ${
                  isRevokedLatest
                    ? "text-red-500 dark:text-red-400"
                    : "text-muted-foreground"
                }`}
              >
                {isRevokedLatest ? "Revoked by" : "Assigned by"}
              </p>
              <PersonSummary
                user={
                  isRevokedLatest
                    ? framework.revocation?.revokedBy
                    : framework.assignment?.assignedBy
                }
                date={
                  isRevokedLatest
                    ? framework.revocation?.revokedAt
                    : framework.assignment?.assignedAt
                }
              />
            </div>
          </div>
        </section>

        {/* ===== STATUS BANNER ===== */}
        {statusBanner(framework)}

        {/* ===== FILE VERSIONS ===== */}
        <div>
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="text-xl font-bold">File Versions</h2>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-primary/15 text-primary">
              Total: {framework.fileVersions?.length || 0} Version
            </span>
          </div>

          <div className="space-y-3">
            {framework.fileVersions?.map((ver) => {
              const isCurrent =
                ver.fileVersion === framework.currentFileVersion;
              const isExpanded = expandedVersions.has(ver.fileVersion);

              return (
                <div
                  key={ver.fileVersion}
                  className={`rounded overflow-hidden transition-all duration-300 hover:shadow-lg bg-card ${
                    isCurrent ? "border border-primary" : "border border-border"
                  }`}
                >
                  <div className="w-full flex items-center justify-between p-2 transition-colors duration-200 text-foreground ">
                    <div className="flex-1 flex items-center gap-3 flex-wrap cursor-pointer">
                      <span
                        className={`px-3 py-1 rounded text-xs font-bold ${
                          isCurrent
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        v{ver.fileVersion}
                        {isCurrent && " • Current"}
                      </span>
                      {isCurrent && isCurrentVersionFinalized && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-1.5 rounded text-xs font-bold uppercase bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                          <Icon name="lock" size="14px" /> Finalized
                        </span>
                      )}
                      <div className="">
                        <FileTypeCard
                          fileType={ver.fileType}
                          fileSize={ver.fileSize}
                          fileName={ver.originalFileName}
                          fileId={ver.fileId}
                          onDownload={() =>
                            handleDownload(ver.fileId, ver.originalFileName)
                          }
                          serviceType="framework"
                          frameworkId={framework.frameworkId}
                        />
                      </div>
                      <div className="flex items-center gap-1">
                        <UserAvatar user={framework.uploadedBy} />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold truncate text-left">
                            {framework.uploadedBy?.name}
                          </p>
                          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                            <Icon name="mail" size="10px" />
                            <span className="truncate">
                              {framework.uploadedBy?.email}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
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

                  {isExpanded && ver.aiExtraction?.length > 0 && (
                    <div className="p-2 border-t border-border">
                      <ControlsPanel
                        sections={ver.aiExtraction}
                        totalSections={ver.aiExtraction.length}
                        totalControls={ver.aiExtraction.reduce(
                          (acc, sec) => acc + (sec.controls?.length || 0),
                          0
                        )}
                        canModify={
                          isUserAuditor &&
                          ver.fileVersion === framework.currentFileVersion &&
                          !isCurrentVersionFinalized &&
                          framework?.status === "assigned"
                        }
                        onEdit={handleEditControl}
                        onDelete={handleDeleteControl}
                        onAdd={handleAddControl}
                        onUpdateControlApplicability={
                          handleUpdateControlApplicability
                        }
                        onUpdateWeightage={handleUpdateControlWeightage}
                        showApplicability={true}
                        showOrgSpecificBadge={true}
                        isDeploymentFramework={true}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
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

      {/* Assignment History Modal */}
      {showHistoryModal && (
        <AssignmentHistoryModal
          framework={framework}
          onClose={() => setShowHistoryModal(false)}
        />
      )}

      {/* Finalize Version Modal */}
      {showFinalizeModal && (
        <FinalizeFrameworkVersionModal
          framework={framework}
          onConfirm={handleFinalizeConfirm}
          onCancel={() => setShowFinalizeModal(false)}
        />
      )}
    </div>
  );
}

export default AssignedFrameworkDetails;
