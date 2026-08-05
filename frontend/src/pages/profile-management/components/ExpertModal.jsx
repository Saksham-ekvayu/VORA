/* eslint-disable react/prop-types */

import { useEffect, useState } from "react";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import PhoneInputField from "@/components/custom/PhoneInputField";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { useModalState } from "@/hooks/useModalState";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import {
  validateEmail,
  validateName,
  validatePhone,
} from "@/utils/formValidation";
import { ROLE_EXPERT } from "@/utils/commonUtils";

/**
 * ExpertModal Component - Handles Create and Update modes for Expert users
 *
 * @param {boolean} open - Dialog open state
 * @param {Function} onOpenChange - Dialog open state change handler
 * @param {string} mode - 'create' | 'update'
 * @param {Object} expert - Expert data (for update mode)
 * @param {Function} onSave - Save handler for create/update
 */
export default function ExpertModal({
  open,
  onOpenChange,
  mode = "create",
  expert = null,
  onSave,
}) {
  const { handleError, handleValidationError } = useErrorHandler();
  const modalState = useModalState(mode);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
  });

  useEffect(() => {
    if (expert && mode === "update") {
      // Normalize to E.164 format for react-phone-number-input
      let phone = expert.phone || "";
      if (phone && !phone.startsWith("+")) phone = `+${phone}`;

      setFormData({
        name: expert.name || "",
        email: expert.email || "",
        phone,
      });
    } else if (mode === "create") {
      setFormData({
        name: "",
        email: "",
        phone: "",
      });
    }
  }, [expert, mode]);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    modalState.setErrors((prev) => ({ ...prev, [field]: null }));
  };

  const validateForm = () => {
    const newErrors = {};

    const emailError = validateEmail(formData.email);
    if (emailError) newErrors.email = emailError;

    const nameError = validateName(formData.name);
    if (nameError) newErrors.name = nameError;

    const phoneError = validatePhone(formData.phone);
    if (phoneError) newErrors.phone = phoneError;

    if (!handleValidationError(newErrors)) {
      modalState.setErrors(newErrors);
      return false;
    }

    modalState.setErrors(newErrors);
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    modalState.setLoading(true);
    try {
      // Strip + prefix before sending to backend (backend stores without +)
      const payload = {
        ...formData,
        phone: formData.phone.replace(/^\+/, ""),
        role: ROLE_EXPERT, // Always set role to expert
      };
      await onSave(payload);
      onOpenChange(false);
    } catch (error) {
      handleError(error, "Error saving expert");
    } finally {
      modalState.setLoading(false);
    }
  };

  const getTitle = () => {
    return mode === "create" ? "Create New Expert" : "Update Expert";
  };

  const getIcon = () => {
    return mode === "create" ? "plus" : "edit";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <ModalHeader
          icon={getIcon()}
          title={getTitle()}
          description={
            mode === "create"
              ? "Fill in the form below to create a new expert"
              : "Update the expert information in the form below"
          }
        />
        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-4 p-3">
            {/* Email Field */}
            <div className="space-y-1.5">
              <Label htmlFor="expert-email">
                Email Address <span className="required">*</span>
              </Label>
              <Input
                id="expert-email"
                type="email"
                className={cn(
                  modalState.errors.email &&
                    "border-red-500 focus-visible:ring-red-500/20",
                  mode === "update" &&
                    "bg-muted/50 opacity-60 cursor-not-allowed"
                )}
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="Enter email address"
                disabled={mode === "update"}
              />
            </div>

            {/* Name Field */}
            <div className="space-y-1.5">
              <Label htmlFor="expert-name">
                Full Name <span className="required">*</span>
              </Label>
              <Input
                id="expert-name"
                type="text"
                className={
                  modalState.errors.name &&
                  "border-red-500 focus-visible:ring-red-500/20"
                }
                value={formData.name}
                onChange={(e) => handleChange("name", e.target.value)}
                placeholder="Enter full name"
                required
              />
            </div>

            {/* Phone Field */}
            <div className="space-y-1.5">
              <Label htmlFor="expert-phone">
                Phone Number <span className="required">*</span>
              </Label>
              <PhoneInputField
                id="expert-phone"
                value={formData.phone}
                onChange={(val) => handleChange("phone", val)}
              />
            </div>
          </div>

          <ModalFooter
            onCancel={() => onOpenChange(false)}
            isSaving={modalState.loading}
            actionLabel={mode === "create" ? "Create Expert" : "Save Changes"}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
