/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import FileTypeCard from "@/components/custom/FileTypeCard";
import { uploadDeploymentDocument } from "@/services/deploymentDocumentService";
import { getDeploymentFrameworkClientControls } from "@/services/deploymentFrameworkService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { ChevronDown } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

import { useModalState } from "@/hooks/useModalState";
import { validateDeploymentDocumentFile } from "@/utils/frameworkUtils";

export default function UploadDeploymentDocumentModal({
  isOpen,
  onClose,
  onSuccess,
}) {
  const { loading: saving, setLoading: setSaving } = useModalState();
  const [frameworks, setFrameworks] = useState([]);
  const [loadingFrameworks, setLoadingFrameworks] = useState(false);

  const [formData, setFormData] = useState({
    deploymentFrameworkId: "",
    controlId: "",
    deploymentPoint: "",
    documentName: "",
    file: null,
  });

  const [errors, setErrors] = useState({});

  const fetchApprovedFrameworks = async () => {
    try {
      setLoadingFrameworks(true);
      const response = await getDeploymentFrameworkClientControls();
      if (response.success) setFrameworks(response.data || []);
    } catch (error) {
      console.error("Error fetching frameworks:", error);
    } finally {
      setLoadingFrameworks(false);
    }
  };

  useEffect(() => {
    if (isOpen) fetchApprovedFrameworks();
  }, [isOpen]);

  // Build label same as deployment framework pattern:
  // frameworkName (frameworkCode) - frameworkVersion
  const getFrameworkLabel = (fw) => {
    if (!fw) return "Select a deployment framework";
    return fw.frameworkVersion
      ? `${fw.frameworkName} (${fw.frameworkCode}) - ${fw.frameworkVersion}`
      : `${fw.frameworkName} (${fw.frameworkCode})`;
  };

  const getSelectedLabel = () => {
    if (!formData.deploymentFrameworkId) return "Select a deployment framework";
    const selected = frameworks.find(
      (f) => f.id === formData.deploymentFrameworkId
    );
    return selected
      ? getFrameworkLabel(selected)
      : "Select a deployment framework";
  };

  const availableControls = [];
  const selectedFramework = frameworks.find(
    (f) => f.id === formData.deploymentFrameworkId
  );
  if (selectedFramework?.groups) {
    selectedFramework.groups.forEach((group) => {
      if (group.controls) {
        group.controls.forEach((control) => {
          availableControls.push(control);
        });
      }
    });
  }

  const selectedControl = availableControls.find(
    (c) => c.controlId === formData.controlId
  );
  const availableDPs = selectedControl
    ? selectedControl.deploymentPoints.filter((dp) => dp.status === "approved")
    : [];

  const handleChange = (field, value) => {
    setFormData((prev) => {
      const newData = { ...prev, [field]: value };
      if (field === "deploymentFrameworkId") {
        newData.controlId = "";
        newData.deploymentPoint = "";
      } else if (field === "controlId") {
        newData.deploymentPoint = "";
      }
      return newData;
    });
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: "" }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!validateDeploymentDocumentFile(file, toast)) return;

    setFormData((prev) => ({ ...prev, file }));
    if (errors.file) setErrors((prev) => ({ ...prev, file: "" }));
  };

  const handleFileRemove = () => {
    setFormData((prev) => ({ ...prev, file: null }));
    const fileInput = document.getElementById("deployment-document-file");
    if (fileInput) fileInput.value = "";
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.deploymentFrameworkId) {
      newErrors.deploymentFrameworkId = "Please select a deployment framework";
    }
    if (!formData.controlId) {
      newErrors.controlId = "Please select a control";
    }
    if (!formData.deploymentPoint) {
      newErrors.deploymentPoint = "Please select a deployment point";
    }
    if (!formData.documentName.trim()) {
      newErrors.documentName = "Document name is required";
    }
    if (!formData.file) {
      newErrors.file = "Document file is required";
    }

    if (Object.keys(newErrors).length > 0) {
      toast.error(Object.values(newErrors)[0]);
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleClose = () => {
    setFormData({
      deploymentFrameworkId: "",
      controlId: "",
      deploymentPoint: "",
      documentName: "",
      file: null,
    });
    setErrors({});
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      setSaving(true);

      const uploadFormData = new FormData();
      uploadFormData.append("file", formData.file);
      uploadFormData.append("documentName", formData.documentName);
      uploadFormData.append(
        "deploymentFrameworkId",
        formData.deploymentFrameworkId
      );
      uploadFormData.append("controlId", formData.controlId);
      if (selectedControl) {
        uploadFormData.append("controlName", selectedControl.controlName);
      }
      uploadFormData.append("deploymentPoint", formData.deploymentPoint);

      const result = await uploadDeploymentDocument(uploadFormData);

      toast.success(result.message || "Document uploaded successfully!");
      onSuccess?.(result.data);
      handleClose();
    } catch (error) {
      console.error("Error uploading document:", error);
      toast.error(error.message || "Failed to upload document");
    } finally {
      setSaving(false);
    }
  };

  const renderContent = () => {
    if (loadingFrameworks) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
            <span className="text-muted-foreground">
              Loading approved frameworks...
            </span>
          </div>
        </div>
      );
    }

    if (frameworks.length === 0) {
      return (
        <div className="text-center py-12">
          <Icon
            name="warning"
            size="48px"
            className="text-muted-foreground mb-4 mx-auto"
          />
          <h3 className="text-lg font-semibold text-foreground mb-2">
            No Approved Frameworks
          </h3>
          <p className="text-muted-foreground mb-4">
            There are no approved deployment frameworks available.
          </p>
          <p className="text-sm text-muted-foreground">
            A framework must be approved by an expert before you can upload
            documents.
          </p>
        </div>
      );
    }

    return null; // Form will be rendered separately
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-150">
        <ModalHeader
          icon="upload"
          title="Upload Deployment Document"
          description="Upload a deployment document linked to an approved framework"
        />

        <div className="p-3 overflow-y-auto max-h-[calc(90vh-160px)]">
          {renderContent()}
          {!loadingFrameworks && frameworks.length > 0 && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {/* Deployment Framework Dropdown */}
              <div className="space-y-1.5">
                <Label>
                  Deployment Framework <span className="required">*</span>
                </Label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-between font-normal bg-background hover:bg-background",
                        errors.deploymentFrameworkId
                          ? "border-red-500 dark:border-red-500"
                          : "border-border dark:border-gray-600",
                        "dark:hover:border-gray-500"
                      )}
                    >
                      <span className="truncate">{getSelectedLabel()}</span>
                      <ChevronDown className="h-4 w-4 opacity-50 shrink-0" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    className="w-(--radix-dropdown-menu-trigger-width) border-border dark:border-gray-600 dark:bg-gray-800 z-10001"
                    align="start"
                    sideOffset={4}
                  >
                    <DropdownMenuItem
                      onClick={() => handleChange("deploymentFrameworkId", "")}
                      className="cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white"
                    >
                      Select a deployment framework
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {frameworks.map((fw) => (
                      <DropdownMenuItem
                        key={fw.id}
                        onClick={() =>
                          handleChange("deploymentFrameworkId", fw.id)
                        }
                        className={cn(
                          "cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white",
                          formData.deploymentFrameworkId === fw.id &&
                            "bg-primary/10 text-primary font-medium"
                        )}
                      >
                        {getFrameworkLabel(fw)}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Control Dropdown */}
              <div className="space-y-1.5">
                <Label>
                  Control <span className="required">*</span>
                </Label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-between font-normal bg-background hover:bg-background h-auto min-h-10 text-left",
                        errors.controlId
                          ? "border-red-500 dark:border-red-500"
                          : "border-border dark:border-gray-600",
                        "dark:hover:border-gray-500"
                      )}
                    >
                      <span className="truncate whitespace-normal line-clamp-2">
                        {formData.controlId
                          ? `${formData.controlId} - ${availableControls.find((c) => c.controlId === formData.controlId)?.controlName || ""}`
                          : "Select a control"}
                      </span>
                      <ChevronDown className="h-4 w-4 opacity-50 shrink-0 mt-0.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    className="w-(--radix-dropdown-menu-trigger-width) max-h-75 overflow-y-auto border-border dark:border-gray-600 dark:bg-gray-800 z-10001"
                    align="start"
                    sideOffset={4}
                  >
                    <DropdownMenuItem
                      onClick={() => handleChange("controlId", "")}
                      className="cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white"
                    >
                      Select a control
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {availableControls.map((control) => (
                      <DropdownMenuItem
                        key={control.controlId}
                        onClick={() =>
                          handleChange("controlId", control.controlId)
                        }
                        className={cn(
                          "cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white whitespace-normal py-2",
                          formData.controlId === control.controlId &&
                            "bg-primary/10 text-primary font-medium"
                        )}
                      >
                        {control.controlId} - {control.controlName}
                      </DropdownMenuItem>
                    ))}
                    {availableControls.length === 0 && (
                      <div className="p-2 text-sm text-muted-foreground text-center">
                        No approved controls found
                      </div>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* DP Dropdown */}
              <div className="space-y-1.5">
                <Label>
                  Deployment Point <span className="required">*</span>
                </Label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-between font-normal bg-background hover:bg-background h-auto min-h-10 text-left",
                        errors.deploymentPoint
                          ? "border-red-500 dark:border-red-500"
                          : "border-border dark:border-gray-600",
                        "dark:hover:border-gray-500"
                      )}
                    >
                      <span className="truncate whitespace-normal line-clamp-2">
                        {formData.deploymentPoint ||
                          "Select an approved deployment point"}
                      </span>
                      <ChevronDown className="h-4 w-4 opacity-50 shrink-0 mt-0.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    className="w-(--radix-dropdown-menu-trigger-width) max-h-75 overflow-y-auto border-border dark:border-gray-600 dark:bg-gray-800 z-10001"
                    align="start"
                    sideOffset={4}
                  >
                    <DropdownMenuItem
                      onClick={() => handleChange("deploymentPoint", "")}
                      className="cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white"
                    >
                      Select an approved deployment point
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {availableDPs.map((dp) => (
                      <DropdownMenuItem
                        key={dp.dp}
                        onClick={() => handleChange("deploymentPoint", dp.dp)}
                        className={cn(
                          "cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white whitespace-normal py-2",
                          formData.deploymentPoint === dp.dp &&
                            "bg-primary/10 text-primary font-medium"
                        )}
                      >
                        {dp.dp}
                      </DropdownMenuItem>
                    ))}
                    {availableDPs.length === 0 && (
                      <div className="p-2 text-sm text-muted-foreground text-center">
                        No approved deployment points found
                      </div>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Document Name */}
              <div className="space-y-1.5">
                <Label htmlFor="document-name">
                  Document Name <span className="required">*</span>
                </Label>
                <Input
                  id="document-name"
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

              {/* File Upload */}
              <div className="space-y-1.5">
                <Label htmlFor="deployment-document-file">
                  Document File <span className="required">*</span>
                </Label>
                <div className="relative">
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.xls,.xlsx"
                    onChange={handleFileChange}
                    className="hidden"
                    id="deployment-document-file"
                  />

                  {formData.file ? (
                    <div
                      className={cn(
                        "flex items-center justify-between w-full px-4 py-4 border-2 rounded",
                        errors.file
                          ? "border-red-500"
                          : "border-green-200 bg-green-50 dark:bg-green-900/20"
                      )}
                    >
                      <FileTypeCard
                        fileName={formData.file.name}
                        fileSize={formData.file.size}
                      />
                      <div className="flex items-center gap-2">
                        <Label
                          htmlFor="deployment-document-file"
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
                      htmlFor="deployment-document-file"
                      className={cn(
                        "flex items-center justify-center w-full px-4 py-2 border-2 border-dashed rounded cursor-pointer transition-colors hover:bg-accent/50",
                        errors.file ? "border-red-500" : "border-border"
                      )}
                    >
                      <div className="text-center">
                        <Icon
                          name="upload"
                          size="32px"
                          className="text-muted-foreground mb-2 mx-auto"
                        />
                        <p className="text-sm font-medium text-foreground">
                          Click to upload document file
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Supports: PDF, DOC, DOCX
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Maximum file size: 50MB
                        </p>
                      </div>
                    </Label>
                  )}
                </div>
              </div>
            </form>
          )}
        </div>

        {!loadingFrameworks && frameworks.length > 0 && (
          <ModalFooter
            onCancel={handleClose}
            onSubmit={handleSubmit}
            isSaving={saving}
            actionLabel="Upload Document"
            savingLabel="Uploading..."
            actionIcon="upload"
            actionType="button"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
