/* eslint-disable react/prop-types */

import { useEffect, useState } from "react";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import PhoneInputField from "@/components/custom/PhoneInputField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown } from "lucide-react";
import { useAuth } from "@/context/authContext/useAuth";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { useModalState } from "@/hooks/useModalState";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import {
  validateEmail,
  validateName,
  validatePhone,
} from "@/utils/formValidation";
import {
  isCustomerAdmin,
  isUser,
  isAuditor,
  isInternalExpert,
  ROLE_USER,
  ROLE_AUDITOR,
  ROLE_INTERNAL_EXPERT,
} from "@/utils/commonUtils";

const getRoleDisplayLabel = (role) => {
  if (isUser(role)) return "User";
  if (isInternalExpert(role)) return "Internal Expert";
  if (isAuditor(role)) return "Auditor";
  if (role === "other") return "Other";
  return "Select a role";
};

/**
 * UserModal Component - Handles Create and Edit modes
 *
 * @param {boolean} open - Dialog open state
 * @param {Function} onOpenChange - Dialog open state change handler
 * @param {string} mode - 'create' | 'edit'
 * @param {Object} user - User data (for edit mode)
 * @param {Function} onSave - Save handler for create/edit
 */
export default function UserModal({
  open,
  onOpenChange,
  mode = "create",
  user = null,
  onSave,
}) {
  const { user: authUser } = useAuth();
  const { handleError, handleValidationError } = useErrorHandler();
  const modalState = useModalState(mode);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    role: ROLE_USER,
    designation: "",
  });

  useEffect(() => {
    if (user && mode === "edit") {
      // Normalize to E.164 format for react-phone-number-input
      let phone = user.phone || "";
      if (phone && !phone.startsWith("+")) phone = `+${phone}`;

      const standardRoles = [ROLE_USER, ROLE_INTERNAL_EXPERT, ROLE_AUDITOR];

      setFormData({
        name: user.name || "",
        email: user.email || "",
        phone,
        role: standardRoles.includes(user.role) ? user.role : ROLE_USER,
        designation: user.designation || "",
      });
    } else if (mode === "create") {
      setFormData({
        name: "",
        email: "",
        phone: "",
        role: ROLE_USER,
        designation: "",
      });
    }
  }, [user, mode]);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    modalState.setErrors((prev) => ({ ...prev, [field]: null }));
  };

  const validateForm = () => {
    const newErrors = {};

    const nameError = validateName(formData.name);
    if (nameError) newErrors.name = nameError;

    const emailError = validateEmail(formData.email);
    if (emailError) newErrors.email = emailError;

    const phoneError = validatePhone(formData.phone);
    if (phoneError) newErrors.phone = phoneError;

    if (formData.phone) {
      const phoneError = validatePhone(formData.phone);
      if (phoneError) newErrors.phone = phoneError;
    }

    if (isCustomerAdmin(authUser?.role) && !formData.role) {
      newErrors.role = "Role is required";
    }

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
      const payload = {
        ...formData,
        phone: formData.phone.replace(/^\+/, ""),
        role: isCustomerAdmin(authUser?.role)
          ? formData.role
          : user?.role || ROLE_USER,
        designation: formData.designation ? formData.designation.trim() : null,
      };

      await onSave(payload);
      onOpenChange(false);
    } catch (error) {
      handleError(error, "Error saving user");
    } finally {
      modalState.setLoading(false);
    }
  };

  const getTitle = () => {
    return mode === "create" ? "Create Profile" : "Update Profile";
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
              ? "Fill in the form below to create a new user"
              : "Update the user information in the form below"
          }
        />
        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-4 p-3">
            {/* Name Field */}
            <div className="space-y-1.5">
              <Label htmlFor="user-name">
                Full Name <span className="required">*</span>
              </Label>
              <Input
                id="user-name"
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

            {/* Email Field */}
            <div className="space-y-1.5">
              <Label htmlFor="user-email">
                Email Address <span className="required">*</span>
              </Label>
              <Input
                id="user-email"
                type="email"
                className={cn(
                  modalState.errors.email &&
                    "border-red-500 focus-visible:ring-red-500/20",
                  mode === "edit" && "bg-muted/50 opacity-60 cursor-not-allowed"
                )}
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="Enter email address"
                disabled={mode === "edit"}
              />
            </div>

            {/* Phone Field */}
            <div className="space-y-1.5">
              <Label htmlFor="user-phone">Phone Number</Label>
              <PhoneInputField
                id="user-phone"
                value={formData.phone}
                onChange={(val) => handleChange("phone", val)}
              />
            </div>

            {/* Role Field (Only for Customer) */}
            {isCustomerAdmin(authUser?.role) && (
              <div className="space-y-1.5 flex flex-col">
                <Label htmlFor="user-role">
                  Role <span className="required">*</span>
                </Label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      id="user-role"
                      variant="outline"
                      className={cn(
                        "w-full justify-between font-normal",
                        modalState.errors.role
                          ? "border-red-500 focus:ring-red-500/20"
                          : ""
                      )}
                    >
                      {getRoleDisplayLabel(formData.role)}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="start"
                    style={{
                      width: "var(--radix-dropdown-menu-trigger-width)",
                    }}
                  >
                    <DropdownMenuCheckboxItem
                      checked={isUser(formData.role)}
                      onCheckedChange={() => handleChange("role", ROLE_USER)}
                    >
                      User
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={isAuditor(formData.role)}
                      onCheckedChange={() => handleChange("role", ROLE_AUDITOR)}
                    >
                      Auditor
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={isInternalExpert(formData.role)}
                      onCheckedChange={() =>
                        handleChange("role", ROLE_INTERNAL_EXPERT)
                      }
                    >
                      Internal Expert
                    </DropdownMenuCheckboxItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}

            {/* Designation Field (Only for Customer) */}
            {isCustomerAdmin(authUser?.role) && (
              <div className="space-y-1.5 animate-in fade-in slide-in-from-top-1 px-1">
                <Label htmlFor="user-designation">
                  Designation / Custom Role
                </Label>
                <Input
                  id="user-designation"
                  type="text"
                  value={formData.designation}
                  onChange={(e) => handleChange("designation", e.target.value)}
                  placeholder="E.g., HR Manager (Optional)"
                />
              </div>
            )}
          </div>

          <ModalFooter
            onCancel={() => onOpenChange(false)}
            isSaving={modalState.loading}
            actionLabel={mode === "create" ? "Create User" : "Save Changes"}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
