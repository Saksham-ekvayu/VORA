/**
 * String Utility Functions
 */

/**
 * Capitalizes the first letter of a given string.
 * @param {string} str - The string to capitalize.
 * @returns {string} The string with the first letter capitalized, or an empty string if invalid.
 */
export function capitalizeFirstLetter(str) {
  if (!str || typeof str !== "string") return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}
