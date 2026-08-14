/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import FileTypeCard from "@/components/custom/FileTypeCard";
import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";
import {
  downloadDeploymentFrameworkFile,
  extractDeploymentFramework,
} from "@/services/deploymentFrameworkService";
import { toast } from "sonner";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import {
  aiExtractionConfig,
  STATUS_EXTRACTED,
  STATUS_PENDING,
} from "@/utils/commonUtils";
import { ScrollArea } from "@/components/ui/scroll-area";
import DocumentControlsModal from "./DocumentControlsModal";

export default function DeploymentFrameworkPackageTable({
  preReleasePackage,
  frameworkId,
  documentWidth = "max-w-62",
  showAllColumns = false,
  showActions = true,
  showViewAction = true,
  onExtractionTriggered,
  onSuccess,
}) {
  const [uploadingFileId, setUploadingFileId] = useState(null);
  const [viewingDocument, setViewingDocument] = useState(null);
  const hasActionsColumn = showActions || showViewAction;

  useEffect(() => {
    if (viewingDocument && preReleasePackage?.documents) {
      const updatedDoc = preReleasePackage.documents.find(
        (d) => d.fileId === viewingDocument.fileId
      );
      if (updatedDoc) {
        setViewingDocument(updatedDoc);
      }
    }
  }, [preReleasePackage, viewingDocument?.fileId, viewingDocument]);

  const handleDownload = async (fileId, fileName) => {
    try {
      await downloadDeploymentFrameworkFile(frameworkId, fileId, fileName);
    } catch (error) {
      toast.error(error.message || "Failed to download file");
    }
  };

  const handleAiExtraction = async (fileId) => {
    if (!preReleasePackage?.packageVersion) {
      toast.error("Package version is missing");
      return;
    }
    try {
      setUploadingFileId(fileId);
      if (onExtractionTriggered) {
        onExtractionTriggered(fileId);
      }
      const response = await extractDeploymentFramework(
        frameworkId,
        preReleasePackage.packageVersion,
        fileId
      );
      if (response.success) {
        toast.success(response.message);
        if (onSuccess) {
          await onSuccess();
        }
      } else {
        toast.error(response.message);
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setUploadingFileId(null);
    }
  };

  return (
    <div className="border border-border rounded">
      <ScrollArea className="max-h-145">
        <table className="w-full text-xs border-collapse">
          <thead className="sticky top-0 bg-background z-10">
            <tr className="border-b border-border">
              <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
                #
              </th>

              <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
                Document
              </th>

              <th className="text-center text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
                Replicated
              </th>

              <th className="text-center text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
                File Version
              </th>

              {showAllColumns && (
                <th className="text-center text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
                  Uploaded At
                </th>
              )}

              <th className="text-center text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
                Ai Extraction
              </th>

              {hasActionsColumn && (
                <th className="text-right text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2.5 py-3 whitespace-nowrap">
                  Actions
                </th>
              )}
            </tr>
          </thead>

          <tbody>
            {preReleasePackage?.documents?.map((doc, index) => {
              const status =
                aiExtractionConfig[doc.aiExtraction?.status || STATUS_PENDING];
              return (
                <tr
                  key={doc.originalFileName}
                  className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
                >
                  <td className="px-1 py-2">
                    <span className="w-6 h-6 rounded bg-muted flex items-center justify-center text-[11px] font-semibold text-muted-foreground">
                      {index + 1}
                    </span>
                  </td>
                  <td className="px-2.5 py-2">
                    <div className={documentWidth}>
                      <FileTypeCard
                        fileName={doc.originalFileName}
                        fileType={doc.fileType}
                        fileSize={doc.fileSize}
                        fileId={doc.fileId}
                        onDownload={() =>
                          handleDownload(doc.fileId, doc.originalFileName)
                        }
                        serviceType="deployment-framework"
                        frameworkId={frameworkId}
                        size="sm"
                      />
                    </div>
                  </td>
                  <td className="px-2.5 py-2">
                    <div className="flex items-center justify-center gap-1.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${doc.replicated ? "bg-blue-500" : "bg-green-500"
                          }`}
                      />
                      <span
                        className={`text-[11px] font-medium ${doc.replicated
                            ? "text-blue-600 dark:text-blue-400"
                            : "text-green-600 dark:text-green-400"
                          }`}
                      >
                        {doc.replicated ? "Yes" : "No"}
                      </span>
                    </div>
                  </td>
                  <td className="px-2.5 py-2">
                    <div className="flex items-center justify-center gap-1.5">
                      <span className="text-[11px] font-semibold text-blue-600 dark:text-blue-400">
                        {doc.fileVersion}
                      </span>
                    </div>
                  </td>

                  {showAllColumns && (
                    <td className="px-2.5 py-2 text-center text-muted-foreground whitespace-nowrap">
                      {doc.uploadedAt
                        ? formatDateWithMonthNameAndTime(doc.uploadedAt)
                        : "N/A"}
                    </td>
                  )}

                  <td className="px-2.5 py-2">
                    <span
                      className={`flex items-center justify-center gap-1 text-[11px] font-medium ${uploadingFileId === doc.fileId
                          ? "text-blue-600 dark:text-blue-400"
                          : status.textClass
                        }`}
                    >
                      <Icon
                        name={
                          uploadingFileId === doc.fileId
                            ? "loader"
                            : status.icon
                        }
                        size={12}
                        className={
                          uploadingFileId === doc.fileId ||
                            doc.aiExtraction?.status === "processing"
                            ? "animate-spin"
                            : ""
                        }
                      />
                      {uploadingFileId === doc.fileId
                        ? "Extracting..."
                        : status.label}
                    </span>
                  </td>
                  {hasActionsColumn && (
                    <td className="px-2.5 py-2 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {showViewAction && (
                          <Button
                            size="xs"
                            variant="outline"
                            disabled={
                              doc.aiExtraction?.status !== STATUS_EXTRACTED
                            }
                            className="text-primary border-primary/30 hover:bg-primary/10 hover:text-primary/90"
                            onClick={() => setViewingDocument(doc)}
                          >
                            <Icon name="eye" size={11} className="mr-1" />
                            View
                          </Button>
                        )}
                        {showActions && (
                          <Button
                            size="xs"
                            disabled={
                              status.buttonDisabled ||
                              uploadingFileId === doc.fileId
                            }
                            className={status.buttonClass}
                            onClick={() => handleAiExtraction(doc.fileId)}
                          >
                            <Icon name={status.buttonIcon} size={11} />
                            {status.buttonText}
                          </Button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </ScrollArea>
      {viewingDocument && (
        <DocumentControlsModal
          isOpen={!!viewingDocument}
          onClose={() => setViewingDocument(null)}
          document={viewingDocument}
          frameworkId={frameworkId}
          packageVersion={preReleasePackage?.packageVersion}
          onSuccess={onSuccess}
        />
      )}
    </div>
  );
}
