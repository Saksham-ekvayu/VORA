/* eslint-disable react/prop-types */

import { useState, useEffect, useContext } from "react";
import { updateUser } from "@/services/userService";
import PhoneInputField from "@/components/custom/PhoneInputField";
import { isValidPhoneNumber } from "@/lib/phone";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import AddressFields from "@/components/custom/AddressFields";
import { Country, State } from "country-state-city";
import { AuthContext } from "@/context/authContext/AuthContext";
import { useModalState } from "@/hooks/useModalState";
import { ROLE_ADMIN, ROLE_EXPERT } from "@/utils/commonUtils";

// Helper function to format phone numbers
const formatPhoneNumber = (phone) => {
  if (!phone) return "";
  return phone.startsWith("+") ? phone : `+${phone}`;
};

// Helper function to find country and state codes
const getCountryAndStateCodes = (countryName, stateName) => {
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

// Helper function to check if addresses are the same
const areAddressesSame = (addr1, addr2) => {
  return (
    addr1.country === addr2.country &&
    addr1.state === addr2.state &&
    addr1.city === addr2.city &&
    addr1.locality === addr2.locality
  );
};

// Helper function to initialize address codes
const initializeAddressCodes = (address, setCountryCode, setStateCode) => {
  if (!address.country) return;

  const { countryCode, stateCode } = getCountryAndStateCodes(
    address.country,
    address.state
  );

  setCountryCode(countryCode);
  if (address.state && stateCode) {
    setStateCode(stateCode);
  }
};

function EditProfileModal({ isOpen, onClose, profileData, onUpdate }) {
  const { updateUser: updateSessionUser } = useContext(AuthContext);
  const [formData, setFormData] = useState({
    name: "",
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

  const [isSameAddress, setIsSameAddress] = useState(false);
  const { loading, setLoading } = useModalState();
  const [permanentCountryCode, setPermanentCountryCode] = useState("");
  const [permanentStateCode, setPermanentStateCode] = useState("");
  const [temporaryCountryCode, setTemporaryCountryCode] = useState("");
  const [temporaryStateCode, setTemporaryStateCode] = useState("");

  useEffect(() => {
    if (!profileData) return;

    // Extract address data from profileData
    const addresses = {
      permanent: profileData?.address?.permanentAddress || {},
      temporary: profileData?.address?.temporaryAddress || {},
    };

    // Initialize form data from profile
    setFormData({
      name: profileData?.name || "",
      phone: formatPhoneNumber(profileData?.phone),
      secondaryPhone: formatPhoneNumber(profileData?.secondaryPhone),
      permanentCountry: addresses.permanent.country || "",
      permanentState: addresses.permanent.state || "",
      permanentCity: addresses.permanent.city || "",
      permanentLocality: addresses.permanent.locality || "",
      temporaryCountry: addresses.temporary.country || "",
      temporaryState: addresses.temporary.state || "",
      temporaryCity: addresses.temporary.city || "",
      temporaryLocality: addresses.temporary.locality || "",
    });

    initializeAddressCodes(
      addresses.permanent,
      setPermanentCountryCode,
      setPermanentStateCode
    );
    initializeAddressCodes(
      addresses.temporary,
      setTemporaryCountryCode,
      setTemporaryStateCode
    );

    setIsSameAddress(
      areAddressesSame(addresses.permanent, addresses.temporary)
    );
  }, [profileData]); // Only depend on profileData

  // Validation functions
  const validateForm = () => {
    const validations = [
      { condition: !formData.name.trim(), message: "Name is required" },
      { condition: !formData.phone, message: "Phone Number is required" },
      {
        condition: !isValidPhoneNumber(formData.phone),
        message: "Please enter a valid phone number",
      },
      {
        condition:
          formData.secondaryPhone &&
          !isValidPhoneNumber(formData.secondaryPhone),
        message: "Please enter a valid secondary phone number",
      },
    ];

    if ([ROLE_EXPERT, ROLE_ADMIN].includes(profileData?.role)) {
      validations.push(
        {
          condition: !formData.permanentCountry.trim(),
          message: "Permanent country is required",
        },
        {
          condition: !formData.permanentState.trim(),
          message: "Permanent state is required",
        },
        {
          condition: !formData.permanentCity.trim(),
          message: "Permanent city is required",
        },
        {
          condition: !formData.permanentLocality.trim(),
          message: "Permanent locality is required",
        }
      );

      if (!isSameAddress) {
        validations.push(
          {
            condition: !formData.temporaryCountry.trim(),
            message: "Temporary country is required",
          },
          {
            condition: !formData.temporaryState.trim(),
            message: "Temporary state is required",
          },
          {
            condition: !formData.temporaryCity.trim(),
            message: "Temporary city is required",
          },
          {
            condition: !formData.temporaryLocality.trim(),
            message: "Temporary locality is required",
          }
        );
      }
    }

    const failedValidation = validations.find((v) => v.condition);
    if (failedValidation) {
      toast.error(failedValidation.message);
      return false;
    }

    return true;
  };

  // Prepare payload for API
  const preparePayload = () => {
    const payload = {
      name: formData.name,
      phone: formData.phone.replace(/^\+/, ""),
      secondaryPhone: formData.secondaryPhone
        ? formData.secondaryPhone.replace(/^\+/, "")
        : "",
    };

    if ([ROLE_EXPERT, ROLE_ADMIN].includes(profileData?.role)) {
      payload.permanentAddress = {
        country: formData.permanentCountry,
        state: formData.permanentState,
        city: formData.permanentCity,
        locality: formData.permanentLocality,
      };
      payload.temporaryAddress = {
        country: formData.temporaryCountry,
        state: formData.temporaryState,
        city: formData.temporaryCity,
        locality: formData.temporaryLocality,
      };
    }

    return payload;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      setLoading(true);
      const payload = preparePayload();
      const response = await updateUser(payload);
      const successMessage =
        response?.message || "Profile updated successfully";
      toast.success(successMessage);
      updateSessionUser({ name: formData.name, phone: payload.phone });
      onUpdate();
      onClose();
    } catch (error) {
      console.error("Error updating profile:", error);
      const errorMessage =
        error?.message || error?.data?.message || "Failed to update profile";
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSameAddressChange = (checked) => {
    setIsSameAddress(checked);
    if (checked) {
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

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[60vw]">
        <ModalHeader
          icon="edit"
          title="Update Profile"
          description="Update your account identity."
        />

        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-3 p-3 overflow-y-auto max-h-[70vh]">
            <div className="grid grid-cols-12 gap-4">
              {/* Name */}
              <div className="space-y-1.5 col-span-6">
                <Label
                  htmlFor="profile-name"
                  className="text-xs font-bold text-muted-foreground/80"
                >
                  Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="profile-name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleChange("name", e.target.value)}
                  placeholder="Enter your name"
                  required
                />
              </div>

              {/* Email Field - Display only, not editable */}
              <div className="space-y-1.5 col-span-6">
                <Label
                  htmlFor="profile-email"
                  className="text-xs font-bold text-muted-foreground/80"
                >
                  Email Address
                </Label>
                <Input
                  id="profile-email"
                  type="email"
                  value={profileData?.email || ""}
                  disabled
                  className="bg-muted/50 opacity-60 cursor-not-allowed"
                />
              </div>

              {/* Phone */}
              <div className="space-y-1.5 col-span-6">
                <Label
                  htmlFor="profile-phone"
                  className="text-xs font-bold text-muted-foreground/80"
                >
                  Phone Number <span className="text-red-500">*</span>
                </Label>
                <PhoneInputField
                  id="profile-phone"
                  value={formData.phone}
                  onChange={(val) => handleChange("phone", val)}
                  required
                />
              </div>

              {/* Secondary Phone */}
              <div className="space-y-1.5 col-span-6">
                <Label
                  htmlFor="profile-secondary-phone"
                  className="text-xs font-bold text-muted-foreground/80"
                >
                  Secondary Phone Number
                </Label>
                <PhoneInputField
                  id="profile-secondary-phone"
                  value={formData.secondaryPhone}
                  onChange={(val) => handleChange("secondaryPhone", val)}
                />
              </div>

              {[ROLE_EXPERT, ROLE_ADMIN].includes(profileData?.role) && (
                <>
                  {/* Permanent Address Section */}
                  <div className="col-span-12">
                    <h3 className="text-sm font-bold text-muted-foreground mb-2 border-b pb-1.5">
                      Permanent Address
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

                  {/* Temporary Address Section */}
                  <div className="col-span-12">
                    <div className="flex items-center justify-between border-b pb-1.5 mb-2">
                      <h3 className="text-sm font-bold text-muted-foreground">
                        Temporary Address
                      </h3>
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="same-address"
                          checked={isSameAddress}
                          onCheckedChange={handleSameAddressChange}
                        />
                        <label
                          htmlFor="same-address"
                          className="text-xs font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Same as Permanent Address
                        </label>
                      </div>
                    </div>
                    {!isSameAddress && (
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
                      />
                    )}
                  </div>
                </>
              )}
            </div>
          </div>

          <ModalFooter
            onCancel={onClose}
            cancelLabel="Discard"
            isSaving={loading}
            savingLabel="Updating..."
            actionLabel="Save Changes"
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default EditProfileModal;
