/**
 * modalFetchHelpers.js
 *
 * Stable fetch-wrapper functions used by the dual-table picker modals
 * (AssignFrameworkModal, GiveFrameworkAccessModal, RequestReviewModal).
 *
 * Defined at module level (outside any component) so their identity is
 * stable across renders — required by useModalPaginatedList which uses
 * them as a useCallback dependency.
 *
 * All functions return the shape expected by useModalPaginatedList:
 *   { data: [...], pagination: { totalPages, totalItems } }
 */

import { getAllUsers } from "@/services/userService";
import { getAllCustomers } from "@/services/customerService";
import {
  getAdminFrameworkCategory,
  getApprovedFrameworksForAssignment,
} from "@/services/adminService";

/** Generic user list — sorted by createdAt desc. Pass `role` via extraParams. */
export const fetchUsersFn = (params) =>
  getAllUsers({ ...params, sortBy: "createdAt", sortOrder: "desc" });

/** Customer list — sorted by createdAt desc. */
export const fetchCustomersFn = (params) =>
  getAllCustomers({ ...params, sortBy: "createdAt", sortOrder: "desc" });

/** Approved frameworks for assignment — sorted by createdAt desc. */
export const fetchApprovedFrameworksFn = (params) =>
  getApprovedFrameworksForAssignment({
    ...params,
    approvalStatus: "approved",
    sortBy: "createdAt",
    sortOrder: "desc",
  });

/**
 * Active framework categories with client-side search + pagination.
 *
 * The admin category API doesn't support server-side search/pagination so
 * we fetch all active categories once, filter locally, then slice.
 */
export async function fetchFrameworkCategoriesFn({ page, limit, search }) {
  const res = await getAdminFrameworkCategory({
    page,
    limit,
    search,
    isActive: "true",
  });

  return {
    data: res.data || [],
    pagination: {
      totalPages: res.pagination?.totalPages || 1,
      totalItems: res.pagination?.totalItems || 0,
    },
  };
}
