import { apiRequest } from "./apiService";

const CATEGORY_BASE = "/framework-categories";
const ACCESS_BASE = "/framework-category-service/framework-access";
const ASSIGNMENT_BASE = "/assignment-frameworks";
const FRAMEWORK_BASE = "/framework";

/**
 * Get admin framework category
 */
export function getAdminFrameworkCategory({
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
  return apiRequest(`${CATEGORY_BASE}?${params.toString()}`, true);
}
/**
 * Get admin framework access (all statuses)
 */
export function getAdminFrameworkAccess({
  page = 1,
  limit = 10,
  search = "",
  status = "",
  sortBy = "createdAt",
  sortOrder = "desc",
  frameworkCode = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(status && { status }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
    ...(frameworkCode && { frameworkCode }),
  });
  return apiRequest(`${ACCESS_BASE}?${params.toString()}`, true);
}

/**
 * Create framework category
 */
export function createFrameworkCategory(categoryData) {
  return apiRequest(
    `${CATEGORY_BASE}`,
    {
      method: "POST",
      body: JSON.stringify(categoryData),
    },
    true
  );
}

/**
 * Update framework category
 */
export function updateFrameworkCategory(categoryId, categoryData) {
  return apiRequest(
    `${CATEGORY_BASE}/${categoryId}`,
    {
      method: "PUT",
      body: JSON.stringify(categoryData),
    },
    true
  );
}

/**
 * Delete framework category
 */
export function deleteFrameworkCategory(categoryId) {
  return apiRequest(
    `${CATEGORY_BASE}/${categoryId}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Revoke framework access
 */
export function revokeFrameworkAccess(expertId, frameworkId) {
  return apiRequest(
    `${ACCESS_BASE}/revoke/${expertId}/${frameworkId}`,
    {
      method: "PUT",
    },
    true
  );
}

/**
 * Approve framework access request
 */
export function approveFrameworkAccessRequest(requestId) {
  return apiRequest(
    `${ACCESS_BASE}/approve/${requestId}`,
    {
      method: "PUT",
    },
    true
  );
}

/**
 * Reject framework access request
 */
export function rejectFrameworkAccessRequest(requestId) {
  return apiRequest(
    `${ACCESS_BASE}/reject/${requestId}`,
    {
      method: "PUT",
    },
    true
  );
}

/**
 * Request framework access
 */
export function requestFrameworkAccess(frameworkId) {
  return apiRequest(
    `${ACCESS_BASE}/${frameworkId}/request`,
    {
      method: "POST",
    },
    true
  );
}

/**
 * Assign framework access directly (supports multiple frameworks)
 */
export function assignFrameworkAccess(expertId, frameworkCategoryIds) {
  return apiRequest(
    `${ACCESS_BASE}/assign`,
    {
      method: "POST",
      body: JSON.stringify({
        expertId,
        frameworkCategoryIds: Array.isArray(frameworkCategoryIds)
          ? frameworkCategoryIds
          : [frameworkCategoryIds],
      }),
    },
    true
  );
}

/**
 * Get framework assignments list
 */
export function getFrameworkAssignments({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "createdAt",
  sortOrder = "desc",
  assignmentStatus = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
    ...(assignmentStatus && { assignmentStatus }),
  });
  return apiRequest(
    `${ASSIGNMENT_BASE}/assignments?${params.toString()}`,
    true
  );
}

/**
 * Get approved frameworks from category-service local replica
 */
export function getApprovedFrameworksForAssignment({
  page = 1,
  limit = 10,
  search = "",
  approvalStatus = "",
  sortBy = "",
  sortOrder = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(approvalStatus && { approvalStatus }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
  });

  return apiRequest(`/framework/all-frameworks?${params.toString()}`, true);
}

/**
 * Assign frameworks to customers
 */
export function assignFrameworksToCustomers(
  customerId,
  tenantId,
  frameworkIds
) {
  return apiRequest(
    `${FRAMEWORK_BASE}/assign-framework-to-customer`,
    {
      method: "POST",
      body: JSON.stringify({
        customerId,
        tenantId,
        frameworkIds: Array.isArray(frameworkIds)
          ? frameworkIds
          : [frameworkIds],
      }),
    },
    true
  );
}

/**
 * Revoke framework assignment
 */
export function revokeFrameworkAssignment(customerId, frameworkId) {
  return apiRequest(
    `${ASSIGNMENT_BASE}/assignments/${frameworkId}/${customerId}/revoke`,
    {
      method: "PATCH",
    },
    true
  );
}

/**
 * Get framework access list by user (expert) ID.
 * Returns a curried function so useTableData can call it with pagination params.
 */
export function getFrameworkAccessByUserId(userId) {
  return function ({
    page = 1,
    limit = 10,
    sortBy = "createdAt",
    sortOrder = "desc",
    status = "",
    search = "",
  } = {}) {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...(sortBy && { sortBy }),
      ...(sortOrder && { sortOrder }),
      ...(status && { status }),
      ...(search && { search }),
    });
    return apiRequest(
      `${ACCESS_BASE}/user/${userId}?${params.toString()}`,
      true
    );
  };
}

/**
 * Get available frameworks category access
 */
export function getFrameworkCategoryAccess({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "",
  sortOrder = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
  });

  return apiRequest(`${ACCESS_BASE}/my-access?${params.toString()}`, true);
}

export default {
  getAdminFrameworkCategory,
  getAdminFrameworkAccess,
  createFrameworkCategory,
  updateFrameworkCategory,
  deleteFrameworkCategory,
  revokeFrameworkAccess,
  requestFrameworkAccess,
  approveFrameworkAccessRequest,
  rejectFrameworkAccessRequest,
  assignFrameworkAccess,
  getFrameworkAccessByUserId,
  getFrameworkCategoryAccess,
};
