/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import FileTypeCard from "@/components/custom/FileTypeCard";
import { updateDeploymentDocument } from "@/services/deploymentDocumentService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

import { useModalState } from "@/hooks/useModalState";
import { validateDeploymentDocumentFile } from "@/utils/frameworkUtils";

export default function UpdateDeploymentDocumentModal({
  isOpen,
  onClose,
  onSuccess,
  document,
}) {
  const { loading: saving, setLoading: setSaving } = useModalState();

  const [formData, setFormData] = useState({
    documentName: "",
    currentVersion: "",
    file: null,
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (document && isOpen) {
      setFormData({
        documentName: document.documentName || "",
        currentVersion: document.currentFileVersion || "1.0.0",
        file: null,
      });
      setErrors({});
    }
  }, [document, isOpen]);

  // Build read-only label from the deploymentFramework object already in the API response
  const getLinkedFrameworkLabel = () => {
    const fw = document?.deploymentFramework;
    if (!fw) return "";
    return fw.frameworkVersion
      ? `${fw.frameworkName} (${fw.frameworkCode}) - ${fw.frameworkVersion}`
      : `${fw.frameworkName} (${fw.frameworkCode})`;
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: "" }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!validateDeploymentDocumentFile(file, toast)) return;

    const currentVersion = document?.currentFileVersion || "1.0.0";
    const parts = currentVersion.split(".");
    const suggested = `${parts[0]}.${parts[1]}.${Number.parseInt(parts[2] || 0) + 1}`;

    setFormData((prev) => ({ ...prev, file, currentVersion: suggested }));
    if (errors.file) setErrors((prev) => ({ ...prev, file: "" }));
  };

  const handleFileRemove = () => {
    setFormData((prev) => ({
      ...prev,
      file: null,
      currentVersion: document?.currentFileVersion || "1.0.0",
    }));
    const fileInput = globalThis.document.getElementById(
      "update-deployment-document-file"
    );
    if (fileInput) fileInput.value = "";
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.documentName.trim()) {
      newErrors.documentName = "Document name is required";
    }
    if (formData.file) {
      if (!formData.currentVersion) {
        newErrors.currentVersion =
          "Version is required when uploading a new file";
      } else if (!/^\d+\.\d+\.\d+$/.test(formData.currentVersion)) {
        newErrors.currentVersion =
          "Version must be in format X.Y.Z (e.g., 1.0.0)";
      }
    }

    if (Object.keys(newErrors).length > 0) {
      toast.error(Object.values(newErrors)[0]);
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleClose = () => {
    setFormData({ documentName: "", currentVersion: "", file: null });
    setErrors({});
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      setSaving(true);

      let result;
      if (formData.file) {
        const updateFormData = new FormData();
        updateFormData.append("file", formData.file);
        updateFormData.append("documentName", formData.documentName);
        if (formData.currentVersion) {
          updateFormData.append("currentFileVersion", formData.currentVersion);
        }
        // documentId is added by the service if missing

        result = await updateDeploymentDocument(document.id, updateFormData);
      } else {
        // Metadata only update
        const updateData = {
          documentName: formData.documentName,
        };
        result = await updateDeploymentDocument(document.id, updateData);
      }

      toast.success(result.message || "Document updated successfully!");
      onSuccess?.(result.data);
      handleClose();
    } catch (error) {
      console.error("Error updating document:", error);
      toast.error(error.message || "Failed to update document");
    } finally {
      setSaving(false);
    }
  };

  const currentVersion = document?.currentFileVersion || "1.0.0";

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-150">
        <ModalHeader
          icon="edit"
          title="Update Deployment Document"
          description="Update deployment document details and upload new version"
        />

        <div className="p-3 overflow-y-auto max-h-[calc(90vh-160px)]">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Linked Framework (read-only) */}
            <div className="space-y-1.5">
              <Label>Deployment Framework</Label>
              <Input
                type="text"
                className="bg-muted/50 cursor-not-allowed opacity-90"
                value={getLinkedFrameworkLabel()}
                disabled
                placeholder="No framework linked"
              />
            </div>

            {/* Control (read-only) */}
            <div className="space-y-1.5">
              <Label>Control</Label>
              <Input
                type="text"
                className="bg-muted/50 cursor-not-allowed opacity-90"
                value={document?.controlName || "No control linked"}
                disabled
              />
            </div>

            {/* DP (read-only) */}
            <div className="space-y-1.5">
              <Label>Deployment Point</Label>
              <Input
                type="text"
                className="bg-muted/50 cursor-not-allowed opacity-90 text-ellipsis whitespace-nowrap overflow-hidden"
                value={
                  document?.deploymentPoint || "No deployment point linked"
                }
                disabled
                title={
                  document?.deploymentPoint || "No deployment point linked"
                }
              />
            </div>

            {/* Document Name */}
            <div className="space-y-1.5">
              <Label htmlFor="update-document-name">
                Document Name <span className="required">*</span>
              </Label>
              <Input
                id="update-document-name"
                type="text"
                className={
                  errors.documentName &&
                  "border-red-500 focus-visible:ring-red-500/20"
                }
                value={formData.documentName}
                onChange={(e) => handleChange("documentName", e.target.value)}
                placeholder="e.g., Deployment Policy Document"
              />
            </div>

            {/* File Management - 2 Column Layout */}
            <div className="space-y-1.5">
              <Label className="mb-2">File Management</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Current File */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-foreground">
                      Current File
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium">
                      v{currentVersion}
                    </span>
                  </div>
                  {(() => {
                    const currentVersionData = document?.fileVersions?.find(
                      (v) => v.fileVersion === currentVersion
                    );
                    const fileInfo = document?.fileInfo || currentVersionData;

                    return fileInfo ? (
                      <div className="flex items-center w-full px-3 py-2.5 border-2 rounded border-blue-200 bg-blue-50 dark:bg-blue-900/20 min-h-17.5">
                        <FileTypeCard
                          fileName={fileInfo.originalFileName}
                          fileSize={fileInfo.fileSize}
                        />
                      </div>
                    ) : (
                      <div className="flex items-center justify-center w-full px-3 py-2.5 border-2 border-dashed rounded border-border min-h-17.5">
                        <p className="text-xs text-muted-foreground">
                          No file information available
                        </p>
                      </div>
                    );
                  })()}
                </div>

                {/* New File */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-foreground">
                      New File
                    </span>
                    <span className="text-xs text-muted-foreground">
                      (Optional)
                    </span>
                  </div>
                  <div className="relative">
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx,.xls,.xlsx"
                      onChange={handleFileChange}
                      className="hidden"
                      id="update-deployment-document-file"
                    />

                    {formData.file ? (
                      <div
                        className={cn(
                          "flex items-center justify-between w-full px-3 py-2.5 border-2 rounded min-h-17.5",
                          errors.file
                            ? "border-red-500"
                            : "border-green-200 bg-green-50 dark:bg-green-900/20"
                        )}
                      >
                        <FileTypeCard
                          fileName={formData.file.name}
                          fileSize={formData.file.size}
                        />
                        <div className="flex items-center gap-2 ml-2">
                          <Label
                            htmlFor="update-deployment-document-file"
                            className="flex items-center justify-center w-8 h-8 text-primary bg-primary/10 border border-primary/20 rounded hover:bg-primary/20 transition-colors cursor-pointer"
                            title="Change file"
                          >
                            <Icon name="refresh" size="18px" />
                          </Label>
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            onClick={handleFileRemove}
                            className="flex items-center justify-center w-8 h-8 text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                            title="Remove file"
                          >
                            <Icon name="close" size="18px" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Label
                        htmlFor="update-deployment-document-file"
                        className={cn(
                          "flex items-center justify-center w-full px-3 py-1 border-2 border-dashed rounded cursor-pointer transition-colors hover:bg-accent/50 min-h-17.5",
                          errors.file ? "border-red-500" : "border-border"
                        )}
                      >
                        <div className="text-center">
                          <Icon
                            name="upload"
                            size="20px"
                            className="text-muted-foreground mb-1 mx-auto"
                          />
                          <p className="text-xs font-medium text-foreground">
                            Upload new file
                          </p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">
                            PDF, DOC (Max 50MB)
                          </p>
                        </div>
                      </Label>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Version - only shown when uploading new file */}
          </form>
        </div>

        <ModalFooter
          onCancel={handleClose}
          onSubmit={handleSubmit}
          isSaving={saving}
          actionLabel="Update Document"
          savingLabel="Updating..."
          actionIcon="check"
          actionType="button"
        />
      </DialogContent>
    </Dialog>
  );
}
