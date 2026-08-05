import { apiRequest } from "./apiService";

const BASE_PATH = "/admin/customers";

/**
 * Get all customers
 */
export function getAllCustomers({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "",
  sortOrder = "",
  isActive = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
    ...(isActive && { isActive }),
  });

  return apiRequest(`${BASE_PATH}?${params.toString()}`, true);
}

/**
 * Get customer by ID
 */
export function getCustomerById(customerId, paramsObj = {}) {
  const params = new URLSearchParams(paramsObj);
  const queryString = params.toString();
  const url = queryString
    ? `${BASE_PATH}/${customerId}?${queryString}`
    : `${BASE_PATH}/${customerId}`;

  return apiRequest(url, true);
}

/**
 * Create customer
 */
export function createCustomer(customerData) {
  return apiRequest(
    BASE_PATH,
    {
      method: "POST",
      body: JSON.stringify(customerData),
    },
    true
  );
}

/**
 * Update customer
 */
export function updateCustomer(customerId, customerData) {
  return apiRequest(
    `${BASE_PATH}/${customerId}`,
    {
      method: "PATCH",
      body: JSON.stringify(customerData),
    },
    true
  );
}

/**
 * Toggle customer status
 */
export function toggleCustomerStatus(customerId) {
  return apiRequest(
    `${BASE_PATH}/${customerId}/toggle-status`,
    {
      method: "PATCH",
    },
    true
  );
}

/**
 * Delete customer
 */
export function deleteCustomer(customerId) {
  return apiRequest(
    `${BASE_PATH}/${customerId}`,
    {
      method: "DELETE",
    },
    true
  );
}

export default {
  getAllCustomers,
  getCustomerById,
  createCustomer,
  updateCustomer,
  toggleCustomerStatus,
  deleteCustomer,
};
