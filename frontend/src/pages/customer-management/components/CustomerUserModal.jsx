/* eslint-disable react/prop-types */

import { useEffect, useState } from "react";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import PhoneInputField from "@/components/custom/PhoneInputField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { useModalState } from "@/hooks/useModalState";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import {
  validateEmail,
  validateName,
  validateOptionalPhone,
} from "@/utils/formValidation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown } from "lucide-react";
import {
  ROLE_USER,
  ROLE_AUDITOR,
  ROLE_CUSTOMER_ADMIN,
  ROLE_INTERNAL_EXPERT,
  getRoleLabel,
} from "@/utils/commonUtils";

const ROLES = [
  { value: ROLE_CUSTOMER_ADMIN, label: getRoleLabel(ROLE_CUSTOMER_ADMIN) },
  { value: ROLE_AUDITOR, label: getRoleLabel(ROLE_AUDITOR) },
  { value: ROLE_INTERNAL_EXPERT, label: getRoleLabel(ROLE_INTERNAL_EXPERT) },
  { value: ROLE_USER, label: getRoleLabel(ROLE_USER) },
];

/**
 * CustomerUserModal Component - Handles Create and Update modes for Customer users
 *
 * @param {boolean} open - Dialog open state
 * @param {Function} onOpenChange - Dialog open state change handler
 * @param {string} mode - 'create' | 'update'
 * @param {Object} customer - Customer/User data (for update mode)
 * @param {Function} onSave - Save handler for create/update
 */
export default function CustomerUserModal({
  open,
  onOpenChange,
  mode = "create",
  customer,
  onSave,
}) {
  const { handleError, handleValidationError } = useErrorHandler();
  const modalState = useModalState(mode);
  const [formData, setFormData] = useState({
    tenantId: "",
    name: "",
    email: "",
    phone: "",
    role: ROLE_USER,
  });

  useEffect(() => {
    if (customer && mode === "update") {
      // Normalize to E.164 format for react-phone-number-input
      let phone = customer.phone || "";
      if (phone && !phone.startsWith("+")) phone = `+${phone}`;

      setFormData({
        tenantId: customer.tenantId || "",
        name: customer.name || "",
        email: customer.email || "",
        phone,
        role: customer.role || ROLE_USER,
      });
    } else if (mode === "create") {
      setFormData({
        tenantId: customer?.tenantId || "",
        name: "",
        email: "",
        phone: "",
        role: ROLE_USER,
      });
    }
  }, [customer, mode]);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    modalState.setErrors((prev) => ({ ...prev, [field]: null }));
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.tenantId) {
      newErrors.tenantId = "Customer is required";
    }

    const nameError = validateName(formData.name);
    if (nameError) newErrors.name = nameError;

    const emailError = validateEmail(formData.email);
    if (emailError) newErrors.email = emailError;

    const phoneError = validateOptionalPhone(formData.phone);
    if (phoneError) newErrors.phone = phoneError;

    if (!formData.role) {
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
      // Strip + prefix before sending to backend (backend stores without +)
      const payload = {
        tenantId: formData.tenantId,
        name: formData.name,
        email: formData.email,
        phone: formData.phone.replace(/^\+/, ""),
        role: formData.role,
      };
      await onSave(payload);
      onOpenChange(false);
    } catch (error) {
      handleError(error, "Error saving customer user");
    } finally {
      modalState.setLoading(false);
    }
  };

  const getTitle = () => {
    return mode === "create" ? "Create Customer User" : "Update Customer User";
  };

  const getIcon = () => {
    return mode === "create" ? "plus" : "edit";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-137.5">
        <ModalHeader
          icon={getIcon()}
          title={getTitle()}
          description={
            mode === "create"
              ? "Fill in the form below to create a new customer user"
              : "Update the customer user information in the form below"
          }
        />
        <form onSubmit={handleSubmit}>
          <div className="p-2 overflow-y-auto max-h-[75vh] bg-slate-50/40 dark:bg-slate-900/40 px-4">
            <div className="grid grid-cols-1 gap-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="customer-name">
                  Full Name <span className="required">*</span>
                </Label>
                <Input
                  id="customer-name"
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

              <div className="space-y-1.5">
                <Label htmlFor="customer-email">
                  Email <span className="required">*</span>
                </Label>
                <Input
                  id="customer-email"
                  type="email"
                  className={cn(
                    modalState.errors.email &&
                      "border-red-500 focus-visible:ring-red-500/20",
                    mode === "update" &&
                      "bg-muted/50 opacity-60 cursor-not-allowed"
                  )}
                  value={formData.email}
                  onChange={(e) => handleChange("email", e.target.value)}
                  placeholder="Enter email"
                  disabled={mode === "update"}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="customer-phone">Phone Number</Label>
                <PhoneInputField
                  id="customer-phone"
                  value={formData.phone}
                  onChange={(val) => handleChange("phone", val)}
                />
              </div>

              {/* Role Dropdown */}
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
                        "w-full justify-between font-normal bg-background border-input text-foreground hover:bg-accent hover:text-accent-foreground",
                        modalState.errors.role &&
                          "border-red-500 focus:ring-red-500/20"
                      )}
                    >
                      {formData.role
                        ? getRoleLabel(formData.role)
                        : "Select a role"}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="start"
                    style={{
                      width: "var(--radix-dropdown-menu-trigger-width)",
                    }}
                  >
                    {ROLES.map((r) => (
                      <DropdownMenuCheckboxItem
                        key={r.value}
                        checked={formData.role === r.value}
                        onCheckedChange={() => handleChange("role", r.value)}
                      >
                        {r.label}
                      </DropdownMenuCheckboxItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
                {modalState.errors.role && (
                  <span className="text-xs text-red-500">
                    {modalState.errors.role}
                  </span>
                )}
              </div>
            </div>
          </div>

          <ModalFooter
            onCancel={() => onOpenChange(false)}
            isSaving={modalState.loading}
            actionLabel={
              mode === "create" ? "Create Customer User" : "Save Changes"
            }
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
