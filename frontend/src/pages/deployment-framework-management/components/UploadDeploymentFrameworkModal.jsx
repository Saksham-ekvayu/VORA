/* eslint-disable react/prop-types */

import { useState } from "react";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import { useAssignedFrameworks } from "@/hooks/useAssignedFrameworks";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { ChevronDown } from "lucide-react";
import FileTypeCard from "@/components/custom/FileTypeCard";
import { uploadDeploymentFramework } from "@/services/deploymentFrameworkService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

import { useModalState } from "@/hooks/useModalState";
import { validateDeploymentFrameworkFile } from "@/utils/frameworkUtils";
import { useNavigate } from "react-router-dom";

// Helper function to generate framework label
const generateFrameworkLabel = (framework) => {
  if (framework.frameworkVersion) {
    const name = framework.frameworkName || framework.frameworkCode;
    return `${name} (${framework.frameworkCode}) - ${framework.frameworkVersion}`;
  }

  if (framework.frameworkName) {
    return `${framework.frameworkName} (${framework.frameworkCode})`;
  }

  return framework.frameworkCode;
};

// Helper function to transform assigned frameworks
const transformAssignedFrameworks = (assignedFrameworks) => {
  return assignedFrameworks
    .filter((f) => f.status === "assigned" && f.finalization.isFinalized)
    .map((f) => ({
      assignedFrameworkId: f.id || f._id,
      frameworkId: f.frameworkId,
      label: generateFrameworkLabel(f),
      frameworkCode: f.frameworkCode,
      frameworkName: f.frameworkName,
      frameworkVersion: f.frameworkVersion,
      frameworkCategoryId: f.frameworkCategoryId,
    }));
};

// Helper function to check if there are assigned but not finalized frameworks
const hasNonFinalizedFrameworks = (assignedFrameworks) => {
  return assignedFrameworks.some(
    (f) => f.status === "assigned" && !f.finalization.isFinalized
  );
};

// Helper function to render content based on loading/empty state
const renderContent = (
  loadingFrameworks,
  assignedFrameworksList,
  allAssignedFrameworks,
  navigate
) => {
  if (loadingFrameworks) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-muted-foreground">
            Loading assigned frameworks...
          </span>
        </div>
      </div>
    );
  }

  if (assignedFrameworksList.length === 0) {
    // Check if there are assigned frameworks but not finalized
    if (hasNonFinalizedFrameworks(allAssignedFrameworks)) {
      return (
        <div className="text-center py-2">
          <Icon
            name="info"
            size="48px"
            className="text-amber-500 mb-4 mx-auto"
          />
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Frameworks Pending Finalization
          </h3>
          <p className="text-muted-foreground mb-2 text-sm">
            You have frameworks assigned, but they are pending finalization by
            the framework manager.
          </p>
          <p className="text-sm text-muted-foreground mb-4">
            Please wait for the framework manager to finalize the frameworks
            before uploading.
          </p>
          <Button
            size="xs"
            variant="link"
            onClick={() => navigate("/assigned-frameworks")}
          >
            View assigned framework
          </Button>
        </div>
      );
    }

    // No assigned frameworks at all
    return (
      <div className="text-center py-12">
        <Icon
          name="warning"
          size="48px"
          className="text-muted-foreground mb-4 mx-auto"
        />
        <h3 className="text-lg font-semibold text-foreground mb-2">
          No Assigned Frameworks
        </h3>
        <p className="text-muted-foreground mb-4">
          You don&apos;t have any frameworks assigned by admin.
        </p>
        <p className="text-sm text-muted-foreground">
          Contact your administrator to get frameworks assigned to you.
        </p>
      </div>
    );
  }

  return null; // Form will be rendered separately
};

export default function UploadDeploymentFrameworkModal({
  isOpen,
  onClose,
  onSuccess,
}) {
  const navigate = useNavigate();
  const { loading: saving, setLoading: setSaving } = useModalState();
  const { assignedFrameworks, loading: loadingFrameworks } =
    useAssignedFrameworks();

  // Transform assigned frameworks to dropdown format
  const assignedFrameworksList =
    transformAssignedFrameworks(assignedFrameworks);

  const [formData, setFormData] = useState({
    assignedFrameworkId: "",
    frameworkId: "",
    frameworkName: "",
    frameworkCode: "",
    frameworkVersion: "",
    frameworkCategoryId: "",
    files: [],
  });

  const [errors, setErrors] = useState({});

  const handleChange = (field, value) => {
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }

    if (field === "assignedFrameworkId") {
      const selected = assignedFrameworksList.find(
        (f) => f.assignedFrameworkId === value
      );
      setFormData((prev) => ({
        ...prev,
        assignedFrameworkId: value,
        frameworkId: selected?.frameworkId || "",
        frameworkCode: selected?.frameworkCode || "",
        frameworkName: selected?.frameworkName || "",
        frameworkVersion: selected?.frameworkVersion || "",
        frameworkCategoryId: selected?.frameworkCategoryId || "",
      }));
      return;
    }

    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const getSelectedLabel = () => {
    if (!formData.assignedFrameworkId) return "Select an assigned framework";
    const selected = assignedFrameworksList.find(
      (f) => f.assignedFrameworkId === formData.assignedFrameworkId
    );
    return selected ? selected.label : "Select an assigned framework";
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (!selectedFiles.length) return;

    const validFiles = [];

    selectedFiles.forEach((file) => {
      if (validateDeploymentFrameworkFile(file, toast)) {
        validFiles.push(file);
      }
    });

    if (validFiles.length > 0) {
      setFormData((prev) => ({
        ...prev,
        files: [...prev.files, ...validFiles],
      }));
      if (errors.files) {
        setErrors((prev) => ({ ...prev, files: "" }));
      }
    }
  };

  const handleFileRemove = (indexToRemove) => {
    setFormData((prev) => {
      const newFiles = [...prev.files];
      newFiles.splice(indexToRemove, 1);
      return { ...prev, files: newFiles };
    });
    const fileInput = document.getElementById("deployment-framework-file");
    if (fileInput) fileInput.value = "";
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.assignedFrameworkId) {
      newErrors.assignedFrameworkId = "Please select an assigned framework";
    }

    if (!formData.files || formData.files.length === 0) {
      newErrors.files = "At least one framework file is required";
    }

    if (Object.keys(newErrors).length > 0) {
      toast.error(Object.values(newErrors)[0]);
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleClose = () => {
    setFormData({
      assignedFrameworkId: "",
      frameworkId: "",
      frameworkName: "",
      frameworkCode: "",
      frameworkVersion: "",
      frameworkCategoryId: "",
      files: [],
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
      formData.files.forEach((file) => {
        uploadFormData.append("files", file);
      });

      const metadata = {
        frameworkName: formData.frameworkName,
        frameworkCode: formData.frameworkCode,
        frameworkId: formData.frameworkId,
        assignedFrameworkId: formData.assignedFrameworkId,
        frameworkVersion: formData.frameworkVersion,
        frameworkCategoryId: formData.frameworkCategoryId,
      };
      uploadFormData.append("metadata", JSON.stringify(metadata));

      const result = await uploadDeploymentFramework(uploadFormData);

      toast.success(result.message || "Framework uploaded successfully!");
      onSuccess?.(result.data);
      handleClose();
    } catch (error) {
      console.error("Error uploading framework:", error);
      toast.error(error.message || "Failed to upload framework");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-150">
        <ModalHeader
          icon="upload"
          title="Upload Deployment Framework"
          description="Upload a deployment framework for an assigned official framework"
        />

        <div className="p-3 overflow-y-auto max-h-[calc(90vh-160px)]">
          {renderContent(
            loadingFrameworks,
            assignedFrameworksList,
            assignedFrameworks,
            navigate
          )}
          {!loadingFrameworks && assignedFrameworksList.length > 0 && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {/* Assigned Framework Dropdown */}
              <div className="space-y-1.5">
                <Label>
                  Assigned Framework <span className="required">*</span>
                </Label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-between font-normal bg-background hover:bg-background",
                        errors.assignedFrameworkId
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
                      onClick={() => handleChange("assignedFrameworkId", "")}
                      className="cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white"
                    >
                      Select an assigned framework
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {assignedFrameworksList.map((fw) => (
                      <DropdownMenuItem
                        key={fw.assignedFrameworkId}
                        onClick={() =>
                          handleChange(
                            "assignedFrameworkId",
                            fw.assignedFrameworkId
                          )
                        }
                        className={cn(
                          "cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white",
                          formData.assignedFrameworkId ===
                            fw.assignedFrameworkId &&
                            "bg-primary/10 text-primary font-medium"
                        )}
                      >
                        {fw.label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* File Upload */}
              <div className="space-y-1.5">
                <Label htmlFor="deployment-framework-file">
                  Framework Files <span className="required">*</span>
                </Label>
                <div className="relative">
                  <Input
                    type="file"
                    accept=".pdf,.doc,.docx"
                    multiple
                    onChange={handleFileChange}
                    className="hidden"
                    id="deployment-framework-file"
                  />

                  {formData.files.length === 0 ? (
                    <Label
                      htmlFor="deployment-framework-file"
                      className={cn(
                        "flex items-center justify-center w-full px-4 py-2 border-2 border-dashed rounded cursor-pointer transition-colors hover:bg-accent/50",
                        errors.files ? "border-red-500" : "border-border"
                      )}
                    >
                      <div className="text-center">
                        <Icon
                          name="upload"
                          size="32px"
                          className="text-muted-foreground mb-2 mx-auto"
                        />
                        <p className="text-sm font-medium text-foreground">
                          Click to upload framework files
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Supports: PDF, DOC, DOCX
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Maximum file size: 50MB per file
                        </p>
                      </div>
                    </Label>
                  ) : (
                    <div className="space-y-2">
                      <Label
                        htmlFor="deployment-framework-file"
                        className="flex items-center justify-center w-full px-4 py-2 border-2 border-dashed rounded cursor-pointer transition-colors hover:bg-accent/50 border-border"
                      >
                        <div className="flex items-center gap-2">
                          <Icon name="plus" size="18px" />
                          <span className="text-sm font-medium text-foreground">
                            Add more files
                          </span>
                        </div>
                      </Label>
                      <div className="max-h-40 overflow-y-auto space-y-1">
                        {formData.files.map((file, index) => (
                          <div
                            key={`${file.name}-${index}`}
                            className="flex items-center justify-between w-full px-4 py-3 border-2 rounded border-green-200 bg-green-50 dark:bg-green-900/20"
                          >
                            <FileTypeCard
                              fileName={file.name}
                              fileSize={file.size}
                              size="sm"
                            />
                            <div className="flex items-center gap-2">
                              <Button
                                type="button"
                                size="icon"
                                variant="ghost"
                                onClick={() => handleFileRemove(index)}
                                className="flex items-center justify-center w-8 h-8 text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                                title="Remove file"
                              >
                                <Icon name="close" size="18px" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </form>
          )}
        </div>

        {!loadingFrameworks && assignedFrameworksList.length > 0 && (
          <ModalFooter
            onCancel={handleClose}
            onSubmit={handleSubmit}
            isSaving={saving}
            actionLabel="Upload Framework"
            savingLabel="Uploading..."
            actionIcon="upload"
            actionType="button"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
