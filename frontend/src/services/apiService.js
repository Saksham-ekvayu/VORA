/**
 * Common API Service
 * Handles base URL, headers, auth token & error handling
 */

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api`;

// Global flag to prevent multiple 401 events
let unauthorizedEventDispatched = false;
let unauthorizedEventTimer = null;

/**
 * Get auth token from sessionStorage (matches AuthContext)
 */
function getAuthToken() {
  return sessionStorage.getItem("token");
}

function getTenantId() {
  return sessionStorage.getItem("tenantId") || null;
}

/**
 * Dispatch unauthorized event only once
 */
function dispatchUnauthorizedEvent(message) {
  // If already dispatched, ignore
  if (unauthorizedEventDispatched) {
    return;
  }

  // Mark as dispatched
  unauthorizedEventDispatched = true;

  // Dispatch event
  globalThis.dispatchEvent(
    new CustomEvent("unauthorized-response", {
      detail: {
        status: 401,
        message: message || "Your session has expired. Please log in again.",
      },
    })
  );

  // Reset flag after 5 seconds to allow future 401s (in case user logs in again)
  if (unauthorizedEventTimer) {
    clearTimeout(unauthorizedEventTimer);
  }

  unauthorizedEventTimer = setTimeout(() => {
    unauthorizedEventDispatched = false;
  }, 5000);
}

/**
 * Reset unauthorized event flag (call this on successful login)
 */
export function resetUnauthorizedFlag() {
  unauthorizedEventDispatched = false;
  if (unauthorizedEventTimer) {
    clearTimeout(unauthorizedEventTimer);
    unauthorizedEventTimer = null;
  }
}

/**
 * Generic API request helper
 * Supports:
 * 1. GET without options
 * 2. POST/PUT/DELETE with options + auth
 */

async function handleBlobResponse(response) {
  if (!response.ok) {
    const res = await response.json();
    const error = new Error(res.message || "Download failed");
    error.status = res.status;
    throw error;
  }
  return response.blob();
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return response.json();
  }
  return null;
}

export async function apiRequest(endpoint, optionsOrAuth, maybeAuth) {
  const url = `${API_BASE_URL}${endpoint}`;

  let options = { method: "GET" };
  let requireAuth = false;

  if (typeof optionsOrAuth === "boolean") {
    requireAuth = optionsOrAuth;
  } else if (typeof optionsOrAuth === "object") {
    options = { method: "GET", ...optionsOrAuth };
    requireAuth = maybeAuth || false;
  }

  const token = getAuthToken();
  const tenantId = getTenantId();

  const headers = {
    ...(requireAuth && token && { Authorization: `Bearer ${token}` }),
    ...(tenantId && { "X-TENANT-ID": tenantId }),
    ...options.headers,
  };

  // Only set Content-Type for non-FormData requests
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (Object.keys(headers).length) options.headers = headers;

  try {
    const response = await fetch(url, options);

    if (options.responseType === "blob") {
      return handleBlobResponse(response);
    }

    const data = await parseResponse(response);

    if (!response.ok) {
      if (response.status === 401) {
        dispatchUnauthorizedEvent(
          data?.message || "Token has been invalidated. Please login again."
        );
      }

      const error = new Error(data?.message || "Something went wrong");
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (error) {
    if (error?.status) throw error;
    const wrappedError = new Error(error?.message || "Network error");
    wrappedError.status = 500;
    wrappedError.data = null;
    throw wrappedError;
  }
}
