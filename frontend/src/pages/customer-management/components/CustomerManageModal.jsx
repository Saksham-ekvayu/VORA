/* eslint-disable react/prop-types */

import { useEffect, useState } from "react";
import Icon from "@/components/custom/Icon";
import PhoneInputField from "@/components/custom/PhoneInputField";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import AddressFields from "@/components/custom/AddressFields";
import { Country, State } from "country-state-city";
import { useModalState } from "@/hooks/useModalState";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import {
  validateEmail,
  validateName,
  validateOptionalPhone,
  validateSecondaryPhone,
  validateAddressFields,
} from "@/utils/formValidation";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

// Helper to find country and state codes from names
const findGeographicCodes = (countryName, stateName) => {
  if (!countryName) return { countryCode: "", stateCode: "" };

  const country = Country.getAllCountries().find((c) => c.name === countryName);
  if (!country) return { countryCode: "", stateCode: "" };

  let stateCode = "";
  if (stateName) {
    const state = State.getStatesOfCountry(country.isoCode).find(
      (s) => s.name === stateName
    );
    if (state) stateCode = state.isoCode;
  }

  return { countryCode: country.isoCode, stateCode };
};

/**
 * CustomerManageModal Component - Handles Create and Update modes for Customer organizations
 *
 * @param {boolean} open - Dialog open state
 * @param {Function} onOpenChange - Dialog open state change handler
 * @param {string} mode - 'create' | 'update'
 * @param {Object} customer - Customer data (for update mode)
 * @param {Function} onSave - Save handler for create/update
 */
export default function CustomerManageModal({
  open,
  onOpenChange,
  mode = "create",
  customer = null,
  onSave,
}) {
  const { handleError, handleValidationError } = useErrorHandler();
  const modalState = useModalState(mode);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    secondaryPhone: "",
    // Permanent Address
    permanentCountry: "",
    permanentState: "",
    permanentCity: "",
    permanentLocality: "",
    // Temporary Address
    temporaryCountry: "",
    temporaryState: "",
    temporaryCity: "",
    temporaryLocality: "",
  });

  const [isSameAddress, setIsSameAddress] = useState(false);

  // Geographic codes for permanent address
  const [permanentCountryCode, setPermanentCountryCode] = useState("");
  const [permanentStateCode, setPermanentStateCode] = useState("");

  // Geographic codes for temporary address
  const [temporaryCountryCode, setTemporaryCountryCode] = useState("");
  const [temporaryStateCode, setTemporaryStateCode] = useState("");

  useEffect(() => {
    if (customer && mode === "update") {
      // Normalize to E.164 format for react-phone-number-input
      let phone = customer.phone || "";
      if (phone && !phone.startsWith("+")) phone = `+${phone}`;

      let secondaryPhone = customer.secondaryPhone || "";
      if (secondaryPhone && !secondaryPhone.startsWith("+"))
        secondaryPhone = `+${secondaryPhone}`;

      // Extract address from nested structure
      const permanentAddr = customer.address?.permanentAddress || {};
      const temporaryAddr = customer.address?.temporaryAddress || {};

      setFormData({
        name: customer.name || "",
        email: customer.email || "",
        phone,
        secondaryPhone,
        permanentCountry: permanentAddr.country || "",
        permanentState: permanentAddr.state || "",
        permanentCity: permanentAddr.city || "",
        permanentLocality: permanentAddr.locality || "",
        temporaryCountry: temporaryAddr.country || "",
        temporaryState: temporaryAddr.state || "",
        temporaryCity: temporaryAddr.city || "",
        temporaryLocality: temporaryAddr.locality || "",
      });

      // Find country/state codes from names
      const permanent = findGeographicCodes(
        permanentAddr.country,
        permanentAddr.state
      );
      setPermanentCountryCode(permanent.countryCode);
      setPermanentStateCode(permanent.stateCode);

      const temporary = findGeographicCodes(
        temporaryAddr.country,
        temporaryAddr.state
      );
      setTemporaryCountryCode(temporary.countryCode);
      setTemporaryStateCode(temporary.stateCode);

      // Check if addresses are same
      const addressSame =
        permanentAddr.country === temporaryAddr.country &&
        permanentAddr.state === temporaryAddr.state &&
        permanentAddr.city === temporaryAddr.city &&
        permanentAddr.locality === temporaryAddr.locality;
      setIsSameAddress(addressSame);
    } else if (mode === "create") {
      setFormData({
        name: "",
        email: "",
        phone: "",
        secondaryPhone: "",
        permanentCountry: "",
        permanentState: "",
        permanentCity: "",
        permanentLocality: "",
        temporaryCountry: "",
        temporaryState: "",
        temporaryCity: "",
        temporaryLocality: "",
      });
      setPermanentCountryCode("");
      setPermanentStateCode("");
      setTemporaryCountryCode("");
      setTemporaryStateCode("");
      setIsSameAddress(false);
    }
  }, [customer, mode]);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    modalState.setErrors((prev) => ({ ...prev, [field]: null }));
  };

  const handleSameAddressChange = (checked) => {
    setIsSameAddress(checked);
    if (checked) {
      // Copy permanent address to temporary
      setFormData((prev) => ({
        ...prev,
        temporaryCountry: prev.permanentCountry,
        temporaryState: prev.permanentState,
        temporaryCity: prev.permanentCity,
        temporaryLocality: prev.permanentLocality,
      }));
      setTemporaryCountryCode(permanentCountryCode);
      setTemporaryStateCode(permanentStateCode);
    }
  };

  const handlePermanentCountrySelect = (item) => {
    setPermanentCountryCode(item.code);
    setFormData((prev) => ({
      ...prev,
      permanentCountry: item.value,
      permanentState: "",
      permanentCity: "",
    }));
    setPermanentStateCode("");

    if (isSameAddress) {
      setTemporaryCountryCode(item.code);
      setFormData((prev) => ({
        ...prev,
        temporaryCountry: item.value,
        temporaryState: "",
        temporaryCity: "",
      }));
      setTemporaryStateCode("");
    }
  };

  const handlePermanentStateSelect = (item) => {
    setPermanentStateCode(item.code);
    setFormData((prev) => ({
      ...prev,
      permanentState: item.value,
      permanentCity: "",
    }));

    if (isSameAddress) {
      setTemporaryStateCode(item.code);
      setFormData((prev) => ({
        ...prev,
        temporaryState: item.value,
        temporaryCity: "",
      }));
    }
  };

  const handlePermanentCitySelect = (item) => {
    setFormData((prev) => ({
      ...prev,
      permanentCity: item.value,
    }));

    if (isSameAddress) {
      setFormData((prev) => ({
        ...prev,
        temporaryCity: item.value,
      }));
    }
  };

  const handlePermanentLocalityChange = (value) => {
    setFormData((prev) => ({
      ...prev,
      permanentLocality: value,
    }));

    if (isSameAddress) {
      setFormData((prev) => ({
        ...prev,
        temporaryLocality: value,
      }));
    }
  };

  const handleTemporaryCountrySelect = (item) => {
    setTemporaryCountryCode(item.code);
    setFormData((prev) => ({
      ...prev,
      temporaryCountry: item.value,
      temporaryState: "",
      temporaryCity: "",
    }));
    setTemporaryStateCode("");
  };

  const handleTemporaryStateSelect = (item) => {
    setTemporaryStateCode(item.code);
    setFormData((prev) => ({
      ...prev,
      temporaryState: item.value,
      temporaryCity: "",
    }));
  };

  const validateForm = () => {
    const newErrors = {};

    const emailError = validateEmail(formData.email);
    if (emailError) newErrors.email = emailError;

    const nameError = validateName(formData.name);
    if (nameError) newErrors.name = nameError;

    const phoneError = validateOptionalPhone(formData.phone);
    if (phoneError) newErrors.phone = phoneError;

    const secondaryPhoneError = validateSecondaryPhone(formData.secondaryPhone);
    if (secondaryPhoneError) newErrors.secondaryPhone = secondaryPhoneError;

    // Validate permanent address
    Object.assign(
      newErrors,
      validateAddressFields(
        "Permanent",
        formData.permanentCountry,
        formData.permanentState,
        formData.permanentCity,
        formData.permanentLocality
      )
    );

    // Validate temporary address (only if different from permanent)
    if (!isSameAddress) {
      Object.assign(
        newErrors,
        validateAddressFields(
          "Temporary",
          formData.temporaryCountry,
          formData.temporaryState,
          formData.temporaryCity,
          formData.temporaryLocality
        )
      );
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
        name: formData.name,
        email: formData.email,
        phone: formData.phone.replace(/^\+/, ""),
        secondaryPhone: formData.secondaryPhone
          ? formData.secondaryPhone.replace(/^\+/, "")
          : "",
        address: {
          permanentAddress: {
            country: formData.permanentCountry,
            state: formData.permanentState,
            city: formData.permanentCity,
            locality: formData.permanentLocality,
          },
          temporaryAddress: {
            country: formData.temporaryCountry,
            state: formData.temporaryState,
            city: formData.temporaryCity,
            locality: formData.temporaryLocality,
          },
        },
      };
      await onSave(payload);
      onOpenChange(false);
    } catch (error) {
      handleError(error, "Error saving customer");
    } finally {
      modalState.setLoading(false);
    }
  };

  const getTitle = () => {
    return mode === "create" ? "Create New Customer" : "Update Customer";
  };

  const getIcon = () => {
    return mode === "create" ? "plus" : "edit";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[60vw]">
        <ModalHeader
          icon={getIcon()}
          title={getTitle()}
          description={
            mode === "create"
              ? "Fill in the form below to create a new customer organization"
              : "Update the customer organization details in the form below"
          }
        />
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-2 p-2 overflow-y-auto max-h-[75vh] bg-slate-50/40 dark:bg-slate-900/40">
            {/* Customer Basics */}
            <div className="space-y-2">
              <div className="bg-card shadow-xs border border-border flex flex-col gap-5 p-5 rounded">
                <h3 className="text-sm font-bold flex items-center gap-2 text-primary border-b pb-2">
                  <Icon name="building" size="16px" /> Organization Details
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="customer-name">
                      Organization Name <span className="required">*</span>
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
                      placeholder="Enter organization name"
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="customer-email">
                      Contact Email <span className="required">*</span>
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
                      placeholder="Enter contact email"
                      disabled={mode === "update"}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label
                      htmlFor="customer-phone"
                      className="text-sm font-medium"
                    >
                      Phone Number
                    </Label>
                    <PhoneInputField
                      id="customer-phone"
                      value={formData.phone}
                      onChange={(val) => handleChange("phone", val)}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="customer-secondary-phone">
                      Secondary Phone Number
                    </Label>
                    <PhoneInputField
                      id="customer-secondary-phone"
                      value={formData.secondaryPhone}
                      onChange={(val) => handleChange("secondaryPhone", val)}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Address Modules */}
            <div className="space-y-2">
              {/* Permanent Address */}
              <div className="bg-card shadow-xs border border-border flex flex-col gap-5 p-5 rounded">
                <h3 className="text-sm font-bold flex items-center gap-2 text-primary border-b pb-2">
                  <Icon name="map-pin" size="16px" /> Permanent Address
                </h3>

                <AddressFields
                  prefix="permanent"
                  countryValue={formData.permanentCountry}
                  stateValue={formData.permanentState}
                  cityValue={formData.permanentCity}
                  localityValue={formData.permanentLocality}
                  countryCode={permanentCountryCode}
                  stateCode={permanentStateCode}
                  onCountrySelect={handlePermanentCountrySelect}
                  onStateSelect={handlePermanentStateSelect}
                  onCitySelect={handlePermanentCitySelect}
                  onLocalityChange={handlePermanentLocalityChange}
                />
              </div>

              {/* Temporary Address */}
              <div className="bg-card shadow-xs border border-border flex flex-col gap-4 p-5 rounded transition-all duration-300">
                <div className="flex items-center justify-between border-b pb-2">
                  <h3 className="text-sm font-bold flex items-center gap-2 text-primary">
                    <Icon name="home" size="16px" /> Temporary Address
                  </h3>
                  <div className="flex items-center space-x-2 bg-muted/60 px-2 py-1 rounded-md border border-border/50">
                    <Checkbox
                      id="same-address"
                      checked={isSameAddress}
                      onCheckedChange={handleSameAddressChange}
                      className="cursor-pointer"
                    />
                    <label
                      htmlFor="same-address"
                      className="text-xs font-semibold leading-none cursor-pointer text-muted-foreground select-none"
                    >
                      Same as Permanent
                    </label>
                  </div>
                </div>

                <div
                  className={cn(
                    "transition-opacity duration-300",
                    isSameAddress && "opacity-80 pointer-events-none"
                  )}
                >
                  <AddressFields
                    prefix="temporary"
                    countryValue={formData.temporaryCountry}
                    stateValue={formData.temporaryState}
                    cityValue={formData.temporaryCity}
                    localityValue={formData.temporaryLocality}
                    countryCode={temporaryCountryCode}
                    stateCode={temporaryStateCode}
                    onCountrySelect={handleTemporaryCountrySelect}
                    onStateSelect={handleTemporaryStateSelect}
                    onCitySelect={(item) =>
                      handleChange("temporaryCity", item.value)
                    }
                    onLocalityChange={(val) =>
                      handleChange("temporaryLocality", val)
                    }
                    disabled={isSameAddress}
                  />
                </div>
              </div>
            </div>
          </div>

          <ModalFooter
            onCancel={() => onOpenChange(false)}
            isSaving={modalState.loading}
            actionLabel={mode === "create" ? "Create Customer" : "Save Changes"}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
