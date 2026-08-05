/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";

const getCompareButtonContent = (flags, ver) => {
  if (flags.isComparisonProcessing) {
    return (
      <>
        <Icon name="loader" className="animate-spin" />
        {ver.comparison?.status === "comparison_started"
          ? "Starting..."
          : "Comparing..."}
      </>
    );
  }
  return (
    <>
      <Icon name="git-merge" />
      {flags.isComparisonRetry ? "Retry Compare" : "Compare"}
    </>
  );
};

const getGapButtonContent = (flags, ver) => {
  if (flags.isGapProcessing) {
    return (
      <>
        <Icon name="loader" className="animate-spin" />
        {ver.deploymentGap?.status === "deployment_gap_started"
          ? "Starting..."
          : "Analyzing..."}
      </>
    );
  }
  return (
    <>
      <Icon name="shield" />
      {flags.isGapRetry ? "Retry Gap Analysis" : "Deployment Gap"}
    </>
  );
};

const getUploadButtonContent = (uploadingToAi, ver) => {
  const isUploading =
    uploadingToAi.has(ver.fileId) ||
    ["uploaded", "processing"].includes(ver.aiUpload?.status);
  if (isUploading) {
    return (
      <>
        <Icon name="loader" className="animate-spin" />
        {ver.aiUpload?.status === "processing"
          ? "Processing..."
          : "Uploading..."}
      </>
    );
  }
  return (
    <>
      <Icon name="upload-cloud" />
      {["failed", "skipped"].includes(ver.aiUpload?.status)
        ? "Retry AI Upload"
        : "Upload to AI"}
    </>
  );
};

const VersionActions = ({
  ver,
  flags,
  framework,
  setSelectedVersionForCompare,
  setCompareModalOpen,
  setSelectedVersionForDeploymentGap,
  setDeploymentGapModalOpen,
  handleDeleteVersion,
  handleUploadToAi,
  uploadingToAi,
  toggleVersion,
  isExpanded,
}) => {
  const canDelete =
    !flags.isRestrictedUser && framework.fileVersions.length > 1;
  const isUploadDisabled =
    uploadingToAi.has(ver.fileId) ||
    ["uploaded", "processing"].includes(ver.aiUpload?.status);

  return (
    <div className="flex items-center gap-2">
      {flags.canCompare && (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            setSelectedVersionForCompare(ver);
            setCompareModalOpen(true);
          }}
          disabled={flags.isComparisonProcessing}
        >
          {getCompareButtonContent(flags, ver)}
        </Button>
      )}

      {flags.canRunGap && (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            setSelectedVersionForDeploymentGap(ver);
            setDeploymentGapModalOpen(true);
          }}
          disabled={flags.isGapProcessing}
        >
          {getGapButtonContent(flags, ver)}
        </Button>
      )}

      {canDelete && (
        <Button
          size="sm"
          variant="destructive"
          onClick={() => handleDeleteVersion(ver)}
        >
          <Icon name="trash" size="15px" /> Delete
        </Button>
      )}

      {flags.canUpload && (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => handleUploadToAi(ver.fileId)}
          disabled={isUploadDisabled}
        >
          {getUploadButtonContent(uploadingToAi, ver)}
        </Button>
      )}

      <Button
        variant="ghost"
        size="icon"
        onClick={() => toggleVersion(ver.fileVersion)}
      >
        {isExpanded ? <Icon name="chevron-up" /> : <Icon name="chevron-down" />}
      </Button>
    </div>
  );
};

export default VersionActions;
