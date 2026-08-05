/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { useModalState } from "@/hooks/useModalState";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import categories from "./category.json";

import { ModalFooter, ModalHeader } from "@/components/custom/modal";

/**
 * CategoryModal Component - Handles Create and Edit modes
 *
 * @param {string} mode - 'create' | 'edit'
 * @param {Object} category - Category data (for edit mode)
 * @param {Function} onSave - Save handler for create/edit
 * @param {Function} onClose - Close handler
 */
export default function CategoryModal({
  mode = "create",
  category = null,
  onSave,
  onClose,
}) {
  const { handleError, handleValidationError } = useErrorHandler();
  const [formData, setFormData] = useState({
    code: "",
    frameworkCategoryName: "",
    description: "",
    isActive: true,
  });
  const { loading: saving, setLoading: setSaving } = useModalState();

  const categoryOptions = categories || [];

  useEffect(() => {
    if (category && mode === "edit") {
      setFormData({
        code: category.code || "",
        frameworkCategoryName: category.frameworkCategoryName || "",
        description: category.description || "",
        isActive: category.isActive === undefined ? true : category.isActive,
      });
    } else if (mode === "create") {
      // Set default values for create mode
      setFormData({
        code: "",
        frameworkCategoryName: "",
        description: "",
        isActive: true,
      });
    }
  }, [category, mode]);

  const handleChange = (field, value) => {
    if (field === "code") {
      const matchingCategory = categoryOptions.find(
        (item) => item.code === value
      );
      if (matchingCategory) {
        setFormData((prev) => ({
          ...prev,
          code: matchingCategory.code,
          frameworkCategoryName: matchingCategory.frameworkCategoryName,
          description: matchingCategory.description,
        }));
        return;
      }
    }

    if (field === "frameworkCategoryName") {
      const matchingCategory = categoryOptions.find(
        (item) => item.frameworkCategoryName === value
      );
      if (matchingCategory) {
        setFormData((prev) => ({
          ...prev,
          code: matchingCategory.code,
          frameworkCategoryName: matchingCategory.frameworkCategoryName,
          description: matchingCategory.description,
        }));
        return;
      }
    }

    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.code.trim()) {
      newErrors.code = "Code is required";
    }

    if (!formData.frameworkCategoryName.trim()) {
      newErrors.frameworkCategoryName = "Framework category name is required";
    }

    if (Object.keys(newErrors).length > 0) {
      handleValidationError(newErrors);
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setSaving(true);
    try {
      await onSave(formData);
    } catch (error) {
      handleError(error, "Failed to save category");
    } finally {
      setSaving(false);
    }
  };

  const getTitle = () => {
    return mode === "create" ? "Create New Category" : "Edit Category";
  };

  const getIcon = () => {
    return mode === "create" ? "plus" : "edit";
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent>
        <ModalHeader
          icon={getIcon()}
          title={getTitle()}
          description={
            mode === "create"
              ? "Fill in the form below to create a new framework category"
              : "Update the framework category information in the form below"
          }
        />

        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-4 p-3">
            {/* Code Field */}
            <div className="space-y-1.5">
              <Label htmlFor="category-code">
                Code <span className="required">*</span>
              </Label>
              {mode === "create" ? (
                <Input
                  id="category-code"
                  type="text"
                  list="category-code-list"
                  value={formData.code}
                  onChange={(e) => handleChange("code", e.target.value)}
                  placeholder="Enter category code (e.g., custom-category)"
                  autoComplete="off"
                />
              ) : (
                <Input
                  id="category-code"
                  type="text"
                  list="category-code-list"
                  value={formData.code}
                  onChange={(e) => handleChange("code", e.target.value)}
                  placeholder="Enter category code (e.g., iso27002)"
                  autoComplete="off"
                />
              )}
              <datalist id="category-code-list">
                {categoryOptions.map((item) => (
                  <option
                    key={item.code}
                    value={item.code}
                    label={item.frameworkCategoryName}
                  />
                ))}
              </datalist>
            </div>

            {/* Framework Category Name Field */}
            <div className="space-y-1.5">
              <Label htmlFor="category-name">
                Framework Category Name <span className="required">*</span>
              </Label>
              <Input
                id="category-name"
                type="text"
                list="category-name-list"
                value={formData.frameworkCategoryName}
                onChange={(e) =>
                  handleChange("frameworkCategoryName", e.target.value)
                }
                placeholder="Enter framework category name"
                autoComplete="off"
              />
              <datalist id="category-name-list">
                {categoryOptions.map((item) => (
                  <option
                    key={item.code}
                    value={item.frameworkCategoryName}
                    label={item.code}
                  />
                ))}
              </datalist>
            </div>

            {/* Description Field */}
            <div className="space-y-1.5">
              <Label htmlFor="category-description">Description</Label>
              <Textarea
                id="category-description"
                className="min-h-25"
                value={formData.description}
                onChange={(e) => handleChange("description", e.target.value)}
                placeholder="Enter category description"
                rows={4}
              />
            </div>

            {/* Status Field - Only show in edit mode */}
            {mode === "edit" && (
              <div className="space-y-1.5">
                <Label htmlFor="category-status">Status</Label>
                <div className="flex items-center gap-4">
                  <Label className="flex items-center gap-2 cursor-pointer">
                    <Input
                      type="radio"
                      name="isActive"
                      checked={formData.isActive === true}
                      onChange={() => handleChange("isActive", true)}
                      className="w-4 h-4 text-primary focus:ring-primary border-gray-300"
                    />
                    <span className="text-sm font-medium">Active</span>
                  </Label>
                  <Label className="flex items-center gap-2 cursor-pointer">
                    <Input
                      type="radio"
                      name="isActive"
                      checked={formData.isActive === false}
                      onChange={() => handleChange("isActive", false)}
                      className="w-4 h-4 text-primary focus:ring-primary border-gray-300"
                    />
                    <span className="text-sm font-medium">Inactive</span>
                  </Label>
                </div>
              </div>
            )}
          </div>

          <ModalFooter
            onCancel={onClose}
            isSaving={saving}
            actionLabel={mode === "create" ? "Create Category" : "Save Changes"}
            actionIcon="check"
            actionType="submit"
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
