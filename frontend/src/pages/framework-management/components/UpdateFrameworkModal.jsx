/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { useModalState } from "@/hooks/useModalState";
import Icon from "@/components/custom/Icon";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import { useExpertCategoryAccess } from "@/hooks/useExpertCategoryAccess";
import FileTypeCard from "@/components/custom/FileTypeCard";
import { updateFramework } from "@/services/frameworkService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useErrorHandler } from "@/hooks/useErrorHandler";

import { validateFrameworkFile } from "@/utils/frameworkUtils";
import CategoryAccessCheck from "./custom/CategoryAccessCheck";

/**
 * Update Framework Modal Component
 * Allows experts to update existing frameworks for categories they have approved access to
 */

export default function UpdateFrameworkModal({
  isOpen,
  onClose,
  onSuccess,
  framework,
}) {
  const { loading: saving, setLoading: setSaving } = useModalState();
  const { handleError, handleSuccess } = useErrorHandler();
  const { accessibleCategories, loading: loadingCategories } =
    useExpertCategoryAccess();

  // Form state
  const [formData, setFormData] = useState({
    frameworkCategoryId: "",
    frameworkName: "",
    frameworkCode: "",
    frameworkVersion: "",
    file: null,
  });

  const [errors, setErrors] = useState({});

  // Initialize form data when framework prop changes
  useEffect(() => {
    if (framework && isOpen && accessibleCategories.length > 0) {
      // Find the matching category based on framework code
      const matchingCategory = accessibleCategories.find(
        (cat) => cat.code === framework.frameworkCode
      );

      setFormData({
        frameworkCategoryId:
          matchingCategory?.id ||
          matchingCategory?._id ||
          framework.frameworkCategory?.id ||
          "",
        frameworkName: framework.frameworkName || "",
        frameworkCode: framework.frameworkCode || "",
        frameworkVersion: framework.frameworkVersion || "", // Set the version from framework
        file: null, // File will be optional for updates
      });
    }
  }, [framework, isOpen, accessibleCategories]);

  // Transform accessible categories to dropdown format (memoized to prevent re-creation)
  const approvedCategories = accessibleCategories.map((cat) => ({
    value: cat.id || cat._id,
    label: `${cat.frameworkCategoryName} (${cat.code})`,
    code: cat.code,
    name: cat.frameworkCategoryName,
  }));

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!validateFrameworkFile(file, handleError)) return;
      setFormData((prev) => ({
        ...prev,
        file,
      }));
      if (errors.file) {
        setErrors((prev) => ({ ...prev, file: "" }));
      }
    }
  };

  // Handle file removal
  const handleFileRemove = () => {
    setFormData((prev) => ({ ...prev, file: null }));
    // Reset the file input
    const fileInput = document.getElementById("update-framework-file");
    if (fileInput) {
      fileInput.value = "";
    }
  };

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    if (!formData.frameworkCategoryId) {
      newErrors.frameworkCategoryId = "Framework category is required";
    }
    if (!formData.frameworkVersion.trim()) {
      newErrors.frameworkVersion = "Framework version is required";
    }

    // Show errors in toast instead of inline
    if (Object.keys(newErrors).length > 0) {
      const firstError = Object.values(newErrors)[0];
      handleError(new Error(firstError), firstError);
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle modal close
  const handleClose = () => {
    setFormData({
      frameworkCategoryId: "",
      frameworkName: "",
      frameworkCode: "",
      frameworkVersion: "",
      file: null,
    });
    setErrors({});
    onClose();
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setSaving(true);

      // Prepare form data for update
      const updateFormData = new FormData();

      // Only append file if a new file is selected
      if (formData.file) {
        updateFormData.append("file", formData.file);
      }

      const metadata = {
        frameworkCode: formData.frameworkCode,
        frameworkCategoryId: formData.frameworkCategoryId,
        frameworkName: formData.frameworkName,
        frameworkVersion: formData.frameworkVersion,
      };

      updateFormData.append("metadata", JSON.stringify(metadata));

      // Update framework using the service
      const result = await updateFramework(framework.id, updateFormData);

      handleSuccess(result.message);
      onSuccess?.(result.data);
      handleClose();
    } catch (error) {
      console.error("Error updating framework:", error);
      handleError(error, "Failed to update framework");
    } finally {
      setSaving(false);
    }
  };

  const currentFileVersionData = framework?.fileVersions?.find(
    (version) => version.fileVersion === framework?.currentFileVersion
  );

  const fileInfo = framework?.fileInfo ?? currentFileVersionData;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-150">
        <ModalHeader
          icon="edit"
          title="Update Framework"
          description="Update existing framework with new version or information"
        />

        <div className="p-3 overflow-y-auto max-h-[calc(90vh-160px)]">
          <CategoryAccessCheck
            loading={loadingCategories}
            approvedCategories={approvedCategories}
          />
          {!loadingCategories && approvedCategories.length > 0 && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {/* Framework Category */}
              <div className="space-y-1.5">
                <Label htmlFor="framework-category">
                  Framework Category <span className="required">*</span>
                </Label>
                <Input
                  id="framework-category"
                  type="text"
                  value={(() => {
                    if (
                      formData.frameworkCategoryId &&
                      approvedCategories.length > 0
                    ) {
                      const selectedCategory = approvedCategories.find(
                        (cat) => cat.value === formData.frameworkCategoryId
                      );
                      return selectedCategory ? selectedCategory.label : "";
                    }
                    return "";
                  })()}
                  disabled
                  placeholder="Framework category (auto-selected)"
                />
              </div>

              {/* Framework Version */}
              <div className="space-y-1.5">
                <Label htmlFor="framework-version">
                  Framework Version <span className="required">*</span>
                </Label>
                <Input
                  type="text"
                  value={formData.frameworkVersion}
                  disabled
                  placeholder="Framework version cannot be changed"
                />
              </div>

              {/* File Management Section - 2 Column Layout */}
              <div className="space-y-1.5">
                <Label htmlFor="file-management" className="mb-2">
                  File Management
                </Label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Current File Column */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium text-foreground">
                        Current File
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium">
                        v{framework?.currentFileVersion || "1.0.0"}
                      </span>
                    </div>
                    {fileInfo ? (
                      <div className="flex min-h-17.5 w-full items-center rounded border-2 border-blue-200 bg-blue-50 px-3 py-2.5 dark:bg-blue-900/20">
                        <FileTypeCard
                          fileName={fileInfo.originalFileName}
                          fileSize={fileInfo.fileSize}
                        />
                      </div>
                    ) : (
                      <div className="flex min-h-17.5 w-full items-center justify-center rounded border-2 border-dashed border-border px-3 py-2.5">
                        <p className="text-xs text-muted-foreground">
                          No file information available
                        </p>
                      </div>
                    )}
                  </div>

                  {/* New File Column */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium text-foreground">
                        New File
                      </span>
                    </div>
                    <div className="relative">
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx"
                        onChange={handleFileChange}
                        className="hidden"
                        id="update-framework-file"
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
                              htmlFor="update-framework-file"
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
                          htmlFor="update-framework-file"
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
            </form>
          )}
        </div>

        {!loadingCategories && approvedCategories.length > 0 && (
          <ModalFooter
            onCancel={handleClose}
            onSubmit={handleSubmit}
            isSaving={saving}
            savingLabel="Updating..."
            actionLabel="Update Framework"
            actionIcon="upload"
            actionType="button"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
