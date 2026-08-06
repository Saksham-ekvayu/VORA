import { isValidPhoneNumber } from "react-phone-number-input";

/**
 * Centralized form validation utilities
 * Eliminates duplication across 8+ modal components
 */

export const validateEmail = (email) => {
  if (!email?.trim()) {
    return "Email is required";
  }
  if (!/^[^\s@]+@[^\s@]{1,253}\.[^\s@]{2,}$/.test(email)) {
    return "Invalid email format";
  }
  return null;
};

export const validateName = (name) => {
  if (!name?.trim()) {
    return "Name is required";
  }
  return null;
};

export const validatePhone = (phone) => {
  if (!phone) {
    return "Phone number is required";
  }
  if (!isValidPhoneNumber(phone)) {
    return "Please enter a valid phone number";
  }
  return null;
};

export const validateOptionalPhone = (phone) => {
  if (phone && !isValidPhoneNumber(phone)) {
    return "Please enter a valid phone number";
  }
  return null;
};

export const validateSecondaryPhone = (phone) => {
  if (phone && !isValidPhoneNumber(phone)) {
    return "Please enter a valid secondary phone number";
  }
  return null;
};

export const validateAddressFields = (
  addressType,
  country,
  state,
  city,
  locality
) => {
  const errors = {};

  if (!country) {
    errors[`${addressType.toLowerCase()}Country`] =
      `${addressType} country is required`;
  }
  if (!state) {
    errors[`${addressType.toLowerCase()}State`] =
      `${addressType} state is required`;
  }
  if (!city) {
    errors[`${addressType.toLowerCase()}City`] =
      `${addressType} city is required`;
  }
  if (!locality) {
    errors[`${addressType.toLowerCase()}Locality`] =
      `${addressType} locality is required`;
  }

  return errors;
};

export const validateBasicUserInfo = (formData) => {
  const errors = {};

  const emailError = validateEmail(formData.email);
  if (emailError) errors.email = emailError;

  const nameError = validateName(formData.name);
  if (nameError) errors.name = nameError;

  const phoneError = validatePhone(formData.phone);
  if (phoneError) errors.phone = phoneError;

  return errors;
};

export const validateCustomerInfo = (formData, isSameAddress = false) => {
  const errors = {};

  // Basic info
  const emailError = validateEmail(formData.email);
  if (emailError) errors.email = emailError;

  const nameError = validateName(formData.name);
  if (nameError) errors.name = nameError;

  const phoneError = validatePhone(formData.phone);
  if (phoneError) errors.phone = phoneError;

  const secondaryPhoneError = validateSecondaryPhone(formData.secondaryPhone);
  if (secondaryPhoneError) errors.secondaryPhone = secondaryPhoneError;

  // Permanent address
  Object.assign(
    errors,
    validateAddressFields(
      "Permanent",
      formData.permanentCountry,
      formData.permanentState,
      formData.permanentCity,
      formData.permanentLocality
    )
  );

  // Temporary address (only if different)
  if (!isSameAddress) {
    Object.assign(
      errors,
      validateAddressFields(
        "Temporary",
        formData.temporaryCountry,
        formData.temporaryState,
        formData.temporaryCity,
        formData.temporaryLocality
      )
    );
  }

  return errors;
};
