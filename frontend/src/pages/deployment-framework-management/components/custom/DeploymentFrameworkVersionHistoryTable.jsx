/* eslint-disable react/prop-types */

import { useState } from "react";
import Icon from "@/components/custom/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { useNavigate, useParams } from "react-router-dom";
import { downloadDeploymentFrameworkReport } from "@/services/deploymentFrameworkService";
import { toast } from "sonner";
import { useAuth } from "@/context/authContext/useAuth";
import {
  isAuditor,
  statusVariantMap,
  typeVariantMap,
} from "@/utils/commonUtils";

export default function DeploymentFrameworkVersionHistoryTable({
  framework,
  setPackageToDelete,
  currentPackage,
}) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [downloadingVersion, setDownloadingVersion] = useState(null);
  const showAuditorActions = isAuditor(user?.role);

  const handleDownloadReport = async (row) => {
    try {
      setDownloadingVersion(row.packageVersion);
      await downloadDeploymentFrameworkReport(
        framework.id || id,
        row.packageVersion,
        `${framework?.frameworkVersion.replace(/[^a-zA-Z0-9]/g, "_")}_report.pdf`
      );
    } catch (error) {
      toast.error(error?.message || "Failed to download report");
    } finally {
      setDownloadingVersion(null);
    }
  };

  return (
    <div className="w-full overflow-auto max-h-96 rounded border border-border">
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0 bg-card z-10">
          <tr className="border-b border-border">
            <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
              Version
            </th>
            <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
              Type
            </th>
            <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
              Triggered By
            </th>
            <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
              Docs
            </th>
            <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
              Status
            </th>
            <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
              Created On
            </th>
            <th className="text-right text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
              Actions
            </th>
          </tr>
        </thead>

        <tbody>
          {framework?.packages?.map((row) => {
            const isComparisonCompleted =
              row?.comparison?.status?.toLowerCase() === "completed";
            const isGapAnalysisCompleted =
              row?.gapAnalysis?.status?.toLowerCase() === "completed";
            const isReportReady =
              isComparisonCompleted && isGapAnalysisCompleted;
            let reportButtonTitle;
            if (downloadingVersion === row.packageVersion) {
              reportButtonTitle = "Generating...";
            } else if (isReportReady) {
              reportButtonTitle = "Report";
            } else {
              reportButtonTitle =
                "Report can only be downloaded after both comparison and gap analysis are completed";
            }

            return (
              <tr
                key={row.packageVersion}
                className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
              >
                <td className="px-2.5 py-3">
                  <span className="text-primary font-semibold cursor-pointer hover:underline text-[12px]">
                    v{row.packageVersion}{" "}
                    {currentPackage?.packageVersion === row.packageVersion &&
                      "(current)"}
                  </span>
                </td>

                <td className="px-2.5 py-3">
                  <Badge
                    variant={typeVariantMap[row.type]}
                    className="capitalize"
                  >
                    {row.type}
                  </Badge>
                </td>

                <td className="px-2.5 py-3 text-muted-foreground max-w-45">
                  {row.trigger}
                </td>

                <td className="px-2.5 py-3 text-muted-foreground">
                  {row.documents.length} file
                </td>

                <td className="px-2.5 py-3">
                  <Badge
                    variant={statusVariantMap[row.status] || "default"}
                    className="capitalize"
                  >
                    ● {row.status}
                  </Badge>
                </td>

                <td className="px-2.5 py-3 text-muted-foreground whitespace-nowrap">
                  {formatDateWithMonthNameAndTime(row.createdAt)}
                </td>
                <td className="px-2.5 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="outline"
                      size="xs"
                      className="text-primary border-primary/30 hover:bg-primary/10 hover:text-primary/90"
                      onClick={() => {
                        navigate(
                          `/deployment-frameworks/${id}/comparison-and-gap-analysis?package-version=${row.packageVersion}`
                        );
                      }}
                      title="View Analysis"
                    >
                      <Icon name="eye" size={12} />
                    </Button>

                    <Button
                      variant="outline"
                      size="xs"
                      className="text-emerald-600 border-emerald-500/30 hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-50"
                      onClick={() => handleDownloadReport(row)}
                      disabled={downloadingVersion !== null || !isReportReady}
                      title={reportButtonTitle}
                    >
                      <Icon
                        name={
                          downloadingVersion === row.packageVersion
                            ? "loader"
                            : "download"
                        }
                        size={12}
                        className={
                          downloadingVersion === row.packageVersion
                            ? "animate-spin"
                            : ""
                        }
                      />
                    </Button>

                    {showAuditorActions &&
                      row.status !== "live" &&
                      row.status !== "superseded" && (
                        <Button
                          variant="outline"
                          size="xs"
                          className="text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive/90"
                          onClick={() => {
                            setPackageToDelete(row);
                          }}
                          title="Delete Package"
                        >
                          <Icon name="trash" size={12} />
                        </Button>
                      )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
