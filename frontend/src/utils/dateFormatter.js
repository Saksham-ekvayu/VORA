/**
 * Formats ISO date string to DD-MM-YYYY, H:MM AM/PM format
 * @param {string} isoDateString - ISO date string like "2025-12-29T10:13:09.709Z"
 * @returns {string} Formatted date string like "29-12-2025, 4:08 PM"
 */
export const formatDateTime = (isoDateString) => {
  if (!isoDateString) return "";

  try {
    const date = new Date(isoDateString);

    // Check if date is valid
    if (Number.Number.isNaN(date.getTime())) {
      return "Invalid Date";
    }

    // Get date components
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0"); // Month is 0-indexed
    const year = date.getFullYear();

    // Get time components
    let hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, "0");

    // Convert to 12-hour format
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;

    return `${day}-${month}-${year}, ${hours}:${minutes} ${ampm}`;
  } catch (error) {
    console.error("Error formatting date:", error);
    return "Invalid Date";
  }
};

/**
 * Formats ISO date string to just date part (DD-MM-YYYY)
 * @param {string} isoDateString - ISO date string
 * @returns {string} Formatted date string like "29-12-2025"
 */
export const formatDateOnly = (isoDateString) => {
  if (!isoDateString) return "";

  try {
    const date = new Date(isoDateString);

    if (Number.isNaN(date.getTime())) {
      return "Invalid Date";
    }

    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = date.getFullYear();

    return `${day}-${month}-${year}`;
  } catch (error) {
    console.error("Error formatting date:", error);
    return "Invalid Date";
  }
};

/**
 * Formats ISO date string to just time part (H:MM AM/PM)
 * @param {string} isoDateString - ISO date string
 * @returns {string} Formatted time string like "4:08 PM"
 */
export const formatTimeOnly = (isoDateString) => {
  if (!isoDateString) return "";

  try {
    const date = new Date(isoDateString);

    if (Number.isNaN(date.getTime())) {
      return "Invalid Time";
    }

    let hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, "0");

    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;

    return `${hours}:${minutes} ${ampm}`;
  } catch (error) {
    console.error("Error formatting time:", error);
    return "Invalid Time";
  }
};

/**
 * Formats ISO date string to "20 May 2026" format
 * @param {string} isoDateString - ISO date string
 * @returns {string} Formatted date string like "20 May 2026"
 */
export const formatDateWithMonthName = (isoDateString) => {
  if (!isoDateString) return "";

  try {
    const date = new Date(isoDateString);

    if (Number.isNaN(date.getTime())) {
      return "Invalid Date";
    }

    const day = date.getDate();
    const year = date.getFullYear();

    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];

    const month = monthNames[date.getMonth()];

    return `${day} ${month} ${year}`;
  } catch (error) {
    console.error("Error formatting date:", error);
    return "Invalid Date";
  }
};

/**
 * Formats ISO date string to "20 May 2026, 4:08 PM" format
 * @param {string} isoDateString - ISO date string
 * @returns {string} Formatted date-time string like "20 May 2026, 4:08 PM"
 */
export const formatDateWithMonthNameAndTime = (isoDateString) => {
  if (!isoDateString) return "";

  try {
    const date = new Date(isoDateString);

    if (Number.isNaN(date.getTime())) {
      return "Invalid Date";
    }

    const day = date.getDate();
    const year = date.getFullYear();

    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];

    const month = monthNames[date.getMonth()];

    // Time formatting
    let hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, "0");

    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;

    return `${day} ${month} ${year}, ${hours}:${minutes} ${ampm}`;
  } catch (error) {
    console.error("Error formatting date:", error);
    return "Invalid Date";
  }
};
