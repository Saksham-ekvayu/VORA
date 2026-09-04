import { useEffect, useState, useMemo, useCallback } from "react";
import { Helmet } from "react-helmet-async";
import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useAuth } from "@/context/authContext/useAuth";
import {
  getDeploymentFrameworkPackageByVersion,
  downloadDeploymentFrameworkReport,
} from "@/services/deploymentFrameworkService";
import { toast } from "sonner";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import DeploymentFrameworkPackageTable from "./components/custom/DeploymentFrameworkPackageTable";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import GapsTable from "./components/custom/GapTable";
import ComparisonsTable from "./components/custom/ComparisionTable";
import {
  getStatusBadgeProps,
  transformAssignedFrameworks,
} from "./components/helper/deploymentFrameworkHelpers";
import {
  isAuditor,
  STATUS_EXTRACTED,
  STATUS_FAILED,
  STATUS_REVOKED,
  statusVariantMap,
  typeVariantMap,
  STATUS_UPLOADED,
  STATUS_PROCESSING,
} from "@/utils/commonUtils";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ControlsPanel from "@/components/custom/ControlsPanel";
import AnalysisActions from "./components/AnalysisActions";
import { useAssignedFrameworks } from "@/hooks/useAssignedFrameworks";
import { useStatusPolling } from "@/hooks/useStatusPolling";
import SearchInput from "@/components/custom/SearchInput";

const StatusPlaceholder = ({ status, message, type }) => {
  const getStatusConfig = (status) => {
    const normalized = status?.toLowerCase() || "pending";
    switch (normalized) {
      case "completed":
        return {
          icon: "check-circle",
          bgClass: "bg-green-100",
          iconClass: "text-green-600",
        };
      case "processing":
      case "in-progress":
        return {
          icon: "loader",
          bgClass: "bg-blue-100",
          iconClass: "text-blue-600",
        };
      case "failed":
        return {
          icon: "alert-circle",
          bgClass: "bg-rose-100",
          iconClass: "text-rose-600",
        };
      default:
        return {
          icon: "clock",
          bgClass: "bg-amber-100",
          iconClass: "text-amber-600",
        };
    }
  };

  const normalized = status?.toLowerCase() || "pending";
  const config = getStatusConfig(status);
  const displayTitle = `${type?.charAt(0).toUpperCase()}${type?.slice(1)} - ${normalized}`;

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center min-h-60 border border-dashed border-border/80 rounded bg-muted/5 m-1">
      <div
        className={`w-12 h-12 rounded-full ${config.bgClass} flex items-center justify-center mb-3 shadow-xs`}
      >
        <Icon name={config.icon} className={config.iconClass} size="20px" />
      </div>
      <h3 className="font-semibold text-sm text-foreground mb-1">
        {displayTitle}
      </h3>
      {message && normalized === "failed" && (
        <div className="mt-3 px-3 py-1.5 bg-rose-500/5 border border-rose-500/20 rounded text-[11px] font-mono text-rose-600 dark:text-rose-400 max-w-sm break-all leading-normal">
          {message}
        </div>
      )}
    </div>
  );
};

// Helper to extract and set weightage at control level from deployment points
const enrichControlsWithWeightage = (sections) => {
  if (!sections) return sections;
  return sections.map((section) => ({
    ...section,
    controls: (section.controls || []).map((control) => {
      // If control has weightage, return as is
      if (control.weightage !== undefined) {
        return control;
      }
      // Otherwise, calculate from deployment points (use first deployment point's weightage or average)
      const deploymentPoints = control.deployment_points || [];
      const weightage =
        deploymentPoints.length > 0 ? deploymentPoints[0].weightage || 0 : 0;
      return { ...control, weightage };
    }),
  }));
};

export default function ComparisonGapAnalysis() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const packageVersion = searchParams.get("package-version");
  const activeTab = searchParams.get("tab") || "package";
  const navigate = useNavigate();
  const { user } = useAuth();
  const showAuditorActions = isAuditor(user?.role);
  const [globalSearch, setGlobalSearch] = useState("");

  const [activelyExtractingFileIds, setActivelyExtractingFileIds] = useState(
    new Map()
  );

  const handleExtractionTriggered = useCallback((fileId) => {
    setActivelyExtractingFileIds((prev) => {
      const next = new Map(prev);
      next.set(fileId, Date.now());
      return next;
    });
  }, []);

  const handleTabChange = (value) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("tab", value);
        return next;
      },
      { replace: true }
    );
  };

  const { assignedFrameworks } = useAssignedFrameworks();

  const [framework, setFramework] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  const fetchDetails = useCallback(
    async (showSpinner = true) => {
      try {
        if (showSpinner) {
          setLoading(true);
        }
        const response = await getDeploymentFrameworkPackageByVersion(
          id,
          packageVersion
        );
        if (response.success) {
          setFramework(response.data);
        }
      } catch (error) {
        toast.error(error?.message || "Failed to fetch framework details");
      } finally {
        if (showSpinner) {
          setLoading(false);
        }
      }
    },
    [id, packageVersion]
  );

  useEffect(() => {
    fetchDetails(true);
  }, [fetchDetails]);

  useEffect(() => {
    if (!framework) return;
    const docs =
      framework.packages?.find((pkg) => pkg.packageVersion === packageVersion)
        ?.documents || [];
    setActivelyExtractingFileIds((prev) => {
      let changed = false;
      const next = new Map(prev);
      const now = Date.now();

      for (const [fileId, timestamp] of prev.entries()) {
        const doc = docs.find((d) => d.fileId === fileId);
        if (doc) {
          if (
            doc.aiExtraction?.status === STATUS_PROCESSING ||
            doc.aiExtraction?.status === STATUS_UPLOADED ||
            ((doc.aiExtraction?.status === STATUS_EXTRACTED ||
              doc.aiExtraction?.status === STATUS_FAILED) &&
              now - timestamp > 15000)
          ) {
            next.delete(fileId);
            changed = true;
          }
        }
      }
      return changed ? next : prev;
    });
  }, [framework, packageVersion]);

  // Resolve the package matching the query param version, fallback to first package
  const activePackage = useMemo(() => {
    if (!framework?.packages?.length) return null;
    return framework.packages.find(
      (pkg) => pkg.packageVersion === packageVersion
    );
  }, [framework, packageVersion]);

  const comparisonData = activePackage?.comparison || null;
  const gapAnalysisData = activePackage?.gapAnalysis || null;

  const isComparisonCompleted =
    comparisonData?.status?.toLowerCase() === "completed";
  const isGapAnalysisCompleted =
    gapAnalysisData?.status?.toLowerCase() === "completed";
  const isReportReady = isComparisonCompleted && isGapAnalysisCompleted;

  const hasDocumentsProcessing = useMemo(() => {
    const docs = activePackage?.documents || [];
    return docs.some(
      (doc) =>
        [STATUS_UPLOADED, STATUS_PROCESSING].includes(
          doc.aiExtraction?.status
        ) || activelyExtractingFileIds.has(doc.fileId)
    );
  }, [activePackage, activelyExtractingFileIds]);

  const isMergeProcessing =
    activePackage?.mergeDocument?.status === STATUS_PROCESSING;
  const isComparisonProcessing = comparisonData?.status === STATUS_PROCESSING;
  const isGapAnalysisProcessing = gapAnalysisData?.status === STATUS_PROCESSING;

  const shouldPoll =
    hasDocumentsProcessing ||
    isMergeProcessing ||
    isComparisonProcessing ||
    isGapAnalysisProcessing;

  useStatusPolling({
    id,
    pathPattern: "/deployment-frameworks/",
    shouldPoll,
    onPoll: () => fetchDetails(false),
    refreshTrigger: null,
  });

  const assignedFramework = useMemo(() => {
    return transformAssignedFrameworks(assignedFrameworks, framework);
  }, [assignedFrameworks, framework]);

  const isAssignedFrameworkRevoked =
    assignedFramework?.status === STATUS_REVOKED;
  const isAssignedFrameworkFinalized =
    assignedFramework?.finalization?.isFinalized === true;

  const comparisonBadge = getStatusBadgeProps(
    comparisonData?.status,
    "comparison"
  );
  const gapBadge = getStatusBadgeProps(gapAnalysisData?.status, "gap");
  const mergeBadge = getStatusBadgeProps(
    activePackage?.mergeDocument?.status,
    "merge"
  );
  const status = activePackage?.mergeDocument?.status;

  const handleDownloadReport = async () => {
    if (!framework || !activePackage || !isReportReady) return;
    try {
      setDownloading(true);
      await downloadDeploymentFrameworkReport(
        framework.id || id,
        activePackage.packageVersion,
        `${framework?.frameworkVersion.replace(/[^a-zA-Z0-9]/g, "_")}_report.pdf`
      );
    } catch (error) {
      toast.error(error?.message || "Failed to download report");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner className="min-h-[calc(100vh-100px)]" />;
  }

  return (
    <div className="space-y-4 mt-2">
      <Helmet>
        <title>VORA - Comparison & Gap Analysis</title>
      </Helmet>
      {/* Header */}
      <div className="border border-border rounded bg-card p-3 flex items-center justify-between gap-4">
        {/* LEFT */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="w-10 h-10 rounded bg-primary/10 flex items-center justify-center">
            <Icon name="git" size="28px" className="text-primary" />
          </div>

          <div className="flex flex-col">
            <h2 className="text-sm font-semibold text-foreground">
              {framework?.frameworkName} — Comparison &amp; Gap Analysis
            </h2>

            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1 flex-wrap">
              {/* Official framework version */}
              <Link
                to={`/assigned-frameworks/${framework?.assignedFramework?.id}`}
                className="px-2 py-1 rounded bg-primary/10 text-primary font-medium capitalize hover:underline"
              >
                {framework?.frameworkVersion}
              </Link>

              <span className="px-2 py-1 rounded bg-muted text-muted-foreground font-medium text-[11px]">
                VS
              </span>

              {/* Deployment package version */}
              <span className="px-2 py-1 rounded bg-emerald-100 text-emerald-700 font-medium">
                Deployment Package v{activePackage?.packageVersion}
              </span>

              {/* Package type badge */}
              {activePackage?.type && (
                <Badge
                  variant={typeVariantMap[activePackage.type] || "amber"}
                  className="capitalize"
                >
                  {activePackage.type}
                </Badge>
              )}

              {/* Package status badge */}
              {activePackage?.status && (
                <Badge
                  variant={statusVariantMap[activePackage.status] || "default"}
                  className="capitalize"
                >
                  ● {activePackage.status}
                </Badge>
              )}

              {/* Trigger info */}
              {activePackage?.trigger && (
                <Badge variant={"amber"} className="capitalize">
                  ● {activePackage.trigger}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleDownloadReport}
            disabled={downloading || !isReportReady}
            title={
              isReportReady
                ? "Download deployment framework report"
                : "Report can only be downloaded after both comparison and gap analysis are completed"
            }
          >
            <Icon
              name={downloading ? "loader" : "download"}
              size="12px"
              className={downloading ? "animate-spin" : ""}
            />
            {downloading ? " Generating..." : " Report"}
          </Button>
          <Button
            size="sm"
            className="shrink-0"
            onClick={() => navigate(`/deployment-frameworks/${id}`)}
          >
            <Icon name="arrow-left" size="14px" />
            Back
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="">
        <TabsList className="w-full max-w-xl">
          <TabsTrigger value="package">Package</TabsTrigger>
          <TabsTrigger value="controls">Controls</TabsTrigger>
          <TabsTrigger value="comparison">Comparison</TabsTrigger>
          <TabsTrigger value="gap-analysis">Gap Analysis</TabsTrigger>
        </TabsList>
        <TabsContent value="package">
          <div className="bg-card border border-border rounded p-2">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <Icon name="folder" size="16px" className="text-primary" />
                  Deployment Package
                </h2>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  {activePackage?.documents?.length} documents · Package
                  version: <strong>v{activePackage?.packageVersion}</strong>
                </p>
              </div>
              <div className="flex flex-col gap-0">
                <p className="text-xs text-muted-foreground text-right">
                  Last updated:{" "}
                  {formatDateWithMonthNameAndTime(activePackage?.updatedAt)}
                </p>
              </div>
            </div>

            <DeploymentFrameworkPackageTable
              preReleasePackage={activePackage}
              frameworkId={framework?.id}
              documentWidth="max-w-full"
              showAllColumns={true}
              showActions={showAuditorActions}
              onExtractionTriggered={handleExtractionTriggered}
              onSuccess={() => fetchDetails(false)}
            />
          </div>
        </TabsContent>
        <TabsContent value="controls">
          <div className="flex flex-col mt-2 border border-border rounded overflow-hidden">
            {/* Top Bar */}
            <div className="bg-card border-b border-border px-5 h-12 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <Icon name="folder" size="15px" />
                <span className="text-base font-semibold">Merged Controls</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="shrink-0">
                  <SearchInput
                    value={globalSearch}
                    onChange={setGlobalSearch}
                    onClear={() => setGlobalSearch("")}
                    placeholder="Search Sections, Controls & DPs..."
                    className="w-72 bg-background h-8 text-xs"
                  />
                </div>
                <AnalysisActions
                  frameworkId={id}
                  currentPackage={activePackage}
                  isAssignedFrameworkRevoked={isAssignedFrameworkRevoked}
                  isAssignedFrameworkFinalized={isAssignedFrameworkFinalized}
                  viewContext="controls-tab"
                  onRefresh={() => fetchDetails(false)}
                />
                <span className={mergeBadge.className}>{mergeBadge.label}</span>
              </div>
            </div>

            <div className="p-2">
              {status === "merged" ? (
                <ControlsPanel
                  sections={enrichControlsWithWeightage(
                    activePackage.mergeDocument.controls_data || []
                  )}
                  totalSections={
                    activePackage.mergeDocument.controls_data?.length || 0
                  }
                  totalControls={
                    activePackage.mergeDocument.controls_data?.reduce(
                      (acc, s) => acc + (s.controls?.length || 0),
                      0
                    ) || 0
                  }
                  canModify={false}
                  showApplicability={false}
                  globalSearch={globalSearch}
                />
              ) : (
                <StatusPlaceholder
                  status={status}
                  message={activePackage?.mergeDocument?.message}
                  type="merge"
                />
              )}
            </div>
          </div>
        </TabsContent>
        <TabsContent value="comparison">
          <div className="flex flex-col max-h-[80vh] mt-2 border border-border rounded overflow-hidden">
            {/* Top Bar */}
            <div className="bg-card border-b border-border px-5 h-12 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <Icon name="list" size="15px" />
                <span className="text-base font-semibold">
                  Comparison Information
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="shrink-0">
                  <SearchInput
                    value={globalSearch}
                    onChange={setGlobalSearch}
                    onClear={() => setGlobalSearch("")}
                    placeholder="Search Sections, Controls & DPs..."
                    className="w-72 bg-background h-8 text-xs"
                  />
                </div>
                <AnalysisActions
                  frameworkId={id}
                  currentPackage={activePackage}
                  isAssignedFrameworkRevoked={isAssignedFrameworkRevoked}
                  isAssignedFrameworkFinalized={isAssignedFrameworkFinalized}
                  viewContext="comparison-tab"
                  onRefresh={() => fetchDetails(false)}
                />
                <span className={comparisonBadge.className}>
                  {comparisonBadge.label}
                </span>
              </div>
            </div>
            <div className="p-2">
              {comparisonData?.status?.toLowerCase() === "completed" ? (
                <ComparisonsTable
                  comparisonDataSource={comparisonData}
                  packageStatus={activePackage?.status}
                  onRefresh={() => fetchDetails(false)}
                  globalSearch={globalSearch}
                />
              ) : (
                <StatusPlaceholder
                  status={comparisonData?.status}
                  message={comparisonData?.message}
                  type="comparison"
                />
              )}
            </div>
          </div>
        </TabsContent>
        <TabsContent value="gap-analysis">
          <div className="flex flex-col mt-2 border border-border rounded overflow-hidden">
            {/* Top Bar */}
            <div className="bg-card border-b border-border px-5 h-12 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <Icon name="list" size="15px" />
                <span className="text-base font-semibold">Gap Analysis</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="shrink-0">
                  <SearchInput
                    value={globalSearch}
                    onChange={setGlobalSearch}
                    onClear={() => setGlobalSearch("")}
                    placeholder="Search Sections, Controls & DPs..."
                    className="w-72 bg-background h-8 text-xs"
                  />
                </div>
                <AnalysisActions
                  frameworkId={id}
                  currentPackage={activePackage}
                  isAssignedFrameworkRevoked={isAssignedFrameworkRevoked}
                  isAssignedFrameworkFinalized={isAssignedFrameworkFinalized}
                  viewContext="gap-tab"
                  onRefresh={() => fetchDetails(false)}
                />
                <span className={gapBadge.className}>{gapBadge.label}</span>
              </div>
            </div>

            <div className="p-2">
              {gapAnalysisData?.status?.toLowerCase() === "completed" ? (
                <GapsTable
                  deploymentGaps={gapAnalysisData}
                  packageStatus={activePackage?.status}
                  onRefresh={() => fetchDetails(false)}
                  globalSearch={globalSearch}
                />
              ) : (
                <StatusPlaceholder
                  status={gapAnalysisData?.status}
                  message={gapAnalysisData?.message}
                  type="gap"
                />
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
