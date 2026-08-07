/* eslint-disable react/prop-types */

import { useState } from "react";
import { useModalState } from "@/hooks/useModalState";
import Icon from "@/components/custom/Icon";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import { useExpertCategoryAccess } from "@/hooks/useExpertCategoryAccess";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ChevronDown, Check } from "lucide-react";
import FileTypeCard from "@/components/custom/FileTypeCard";
import { uploadFramework } from "@/services/frameworkService";
import {
  generateFrameworkVersionPrefix,
  validateFrameworkVersion,
  validateFrameworkFile,
} from "@/utils/frameworkUtils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useErrorHandler } from "@/hooks/useErrorHandler";

import CategoryAccessCheck from "./custom/CategoryAccessCheck";

// Helper to enforce version prefix on a value
const enforceVersionPrefix = (value, expectedPrefix) => {
  if (!expectedPrefix || value.startsWith(expectedPrefix)) return value;
  if (!value.trim() || !expectedPrefix.startsWith(value)) return expectedPrefix;
  if (value.length >= expectedPrefix.length) {
    return expectedPrefix + value.replace(expectedPrefix, "");
  }
  return value;
};

/**
 * Upload Framework Modal Component
 * Allows experts to upload frameworks for categories they have approved access to
 */
export default function UploadFrameworkModal({ isOpen, onClose, onSuccess }) {
  const { loading: saving, setLoading: setSaving } = useModalState();
  const { handleError, handleSuccess } = useErrorHandler();
  const { accessibleCategories, loading: loadingCategories } =
    useExpertCategoryAccess();

  // Transform accessible categories to dropdown format
  const approvedCategories = accessibleCategories.map((cat) => ({
    value: cat.id || cat._id,
    label: `${cat.frameworkCategoryName} (${cat.code?.toUpperCase()})`,
    code: cat.code,
    name: cat.frameworkCategoryName,
  }));

  // Form state
  const [formData, setFormData] = useState({
    frameworkCategoryId: "",
    frameworkName: "",
    frameworkCode: "",
    frameworkVersion: "",
    file: null,
  });

  const [errors, setErrors] = useState({});
  const [open, setOpen] = useState(false);

  // Initialize form data when framework prop changes (removed fetchApprovedCategories function)

  // Handle form input changes
  const handleChange = (field, value) => {
    if (field === "frameworkVersion" && formData.frameworkCode) {
      const expectedPrefix = generateFrameworkVersionPrefix(
        formData.frameworkCode
      );
      value = enforceVersionPrefix(value, expectedPrefix);
    }

    setFormData((prev) => ({ ...prev, [field]: value }));

    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }

    if (field === "frameworkVersion" && formData.frameworkCode) {
      const versionValidation = validateFrameworkVersion(
        value,
        formData.frameworkCode
      );
      if (!versionValidation.isValid && value.trim()) {
        setErrors((prev) => ({
          ...prev,
          frameworkVersion: versionValidation.message,
        }));
      }
    }

    if (field === "frameworkCategoryId") {
      const selectedCategory = approvedCategories.find(
        (cat) => cat.value === value
      );
      if (selectedCategory) {
        const versionPrefix = generateFrameworkVersionPrefix(
          selectedCategory.code
        );
        setFormData((prev) => ({
          ...prev,
          frameworkCode: selectedCategory.code,
          frameworkName: selectedCategory.name,
          frameworkVersion: versionPrefix,
          [field]: value,
        }));
      }
    }
  };

  // Handle framework version input to prevent prefix deletion
  const handleVersionInputChange = (e) => {
    const value = e.target.value;
    handleChange("frameworkVersion", value);
  };

  // Handle key events to prevent prefix deletion
  const handleVersionKeyDown = (e) => {
    if (!formData.frameworkCode) return;

    const expectedPrefix = generateFrameworkVersionPrefix(
      formData.frameworkCode
    );
    const cursorPosition = e.target.selectionStart;

    // Prevent deletion of prefix characters
    if (
      (e.key === "Backspace" || e.key === "Delete") &&
      cursorPosition <= expectedPrefix.length
    ) {
      e.preventDefault();
    }
  };

  // Handle blur to ensure prefix is always present
  const handleVersionBlur = (e) => {
    if (!formData.frameworkCode) return;

    const expectedPrefix = generateFrameworkVersionPrefix(
      formData.frameworkCode
    );
    const currentValue = e.target.value;

    if (!currentValue.startsWith(expectedPrefix)) {
      handleChange("frameworkVersion", expectedPrefix);
    }
  };
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!validateFrameworkFile(file, handleError)) return;
    setFormData((prev) => ({ ...prev, file }));
    if (errors.file) {
      setErrors((prev) => ({ ...prev, file: "" }));
    }
  };

  // Handle file removal
  const handleFileRemove = () => {
    setFormData((prev) => ({ ...prev, file: null }));
    // Reset the file input
    const fileInput = document.getElementById("framework-file");
    if (fileInput) {
      fileInput.value = "";
    }
  };

  // Get selected category label
  const getSelectedCategoryLabel = () => {
    if (!formData.frameworkCategoryId) return "Select a category";
    const selected = approvedCategories.find(
      (cat) => cat.value === formData.frameworkCategoryId
    );
    return selected ? selected.label : "Select a category";
  };

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    if (!formData.frameworkCategoryId) {
      newErrors.frameworkCategoryId = "Framework category is required";
    }

    if (!formData.frameworkName.trim()) {
      newErrors.frameworkName = "Framework name is required";
    }

    // Validate framework version with year requirement
    const versionValidation = validateFrameworkVersion(
      formData.frameworkVersion,
      formData.frameworkCode
    );
    if (!versionValidation.isValid) {
      newErrors.frameworkVersion = versionValidation.message;
    }

    if (!formData.file) {
      newErrors.file = "Framework file is required";
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

      // Prepare form data for upload
      const uploadFormData = new FormData();
      uploadFormData.append("file", formData.file);

      const metadata = {
        frameworkCode: formData.frameworkCode,
        frameworkCategoryId: formData.frameworkCategoryId,
        frameworkName: formData.frameworkName,
        frameworkVersion: formData.frameworkVersion,
      };
      uploadFormData.append("metadata", JSON.stringify(metadata));

      // Upload framework using the service
      const result = await uploadFramework(uploadFormData);

      handleSuccess(result.message);
      onSuccess?.(result.data);
      handleClose();
    } catch (error) {
      console.error("Error uploading framework:", error);
      handleError(error, "Failed to upload framework");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-150">
        <ModalHeader
          icon="upload"
          title="Upload Framework"
          description="Upload a new framework file for approved categories"
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
                <Popover open={open} onOpenChange={setOpen} modal={true}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={open}
                      className={cn(
                        "w-full justify-between font-normal bg-background hover:bg-background",
                        errors.frameworkCategoryId
                          ? "border-red-500 dark:border-red-500"
                          : "border-border dark:border-gray-600",
                        "dark:hover:border-gray-500"
                      )}
                    >
                      <span className="truncate">
                        {getSelectedCategoryLabel()}
                      </span>
                      <ChevronDown className="h-4 w-4 opacity-50 shrink-0" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent
                    className="w-[--radix-popover-trigger-width] p-0 border-border dark:border-gray-600 dark:bg-gray-800 z-[10001]"
                    align="start"
                  >
                    <Command>
                      <CommandInput placeholder="Search category..." />
                      <CommandList className="max-h-[250px] overflow-y-auto">
                        <CommandEmpty>No category found.</CommandEmpty>
                        <CommandGroup>
                          {approvedCategories.map((category) => (
                            <CommandItem
                              key={category.value}
                              value={category.label}
                              onSelect={() => {
                                handleChange(
                                  "frameworkCategoryId",
                                  category.value
                                );
                                setOpen(false);
                              }}
                              className={cn(
                                "cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white",
                                formData.frameworkCategoryId ===
                                  category.value &&
                                  "bg-primary/10 text-primary font-medium"
                              )}
                            >
                              <Check
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  formData.frameworkCategoryId ===
                                    category.value
                                    ? "opacity-100"
                                    : "opacity-0"
                                )}
                              />
                              {category.label}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>

              {/* Framework Version */}
              <div className="space-y-1.5">
                <Label htmlFor="framework-version">
                  Framework Version <span className="required">*</span>
                </Label>
                <Input
                  type="text"
                  className={
                    errors.frameworkVersion &&
                    "border-red-500 focus-visible:ring-red-500/20"
                  }
                  value={formData.frameworkVersion}
                  onChange={handleVersionInputChange}
                  onKeyDown={handleVersionKeyDown}
                  onBlur={handleVersionBlur}
                  placeholder="e.g., 2022, 2023, 2024 (year required)"
                />
              </div>

              {/* File Upload */}
              <div className="space-y-1.5">
                <Label htmlFor="framework-file">
                  Framework File <span className="required">*</span>
                </Label>
                <div className="relative">
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx"
                    onChange={handleFileChange}
                    className="hidden"
                    id="framework-file"
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
                          htmlFor="framework-file"
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
                      htmlFor="framework-file"
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
                          Click to upload framework file
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

        {!loadingCategories && approvedCategories.length > 0 && (
          <ModalFooter
            onCancel={handleClose}
            onSubmit={handleSubmit}
            isSaving={saving}
            savingLabel="Uploading..."
            actionLabel="Upload Framework"
            actionIcon="upload"
            actionType="button"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
