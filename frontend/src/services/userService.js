import { apiRequest } from "./apiService";

const ADMIN_BASE = "/admin";
const USER_BASE = "/user";

/**
 * Get all users
 */
export function getAllUsers({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "",
  sortOrder = "",
  role = "",
  isActive = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
    ...(role && { role }),
    ...(isActive && { isActive }),
  });

  return apiRequest(`${ADMIN_BASE}/all-users?${params.toString()}`, true);
}

/**
 * Get user by ID
 */
export function getUserById(userId) {
  return apiRequest(`${ADMIN_BASE}/${userId}`, true); // ✅ GET with auth
}

/**
 * Create user (Admin)
 */
export function createUser(userData) {
  return apiRequest(
    `${ADMIN_BASE}/create`,
    {
      method: "POST",
      body: JSON.stringify(userData),
    },
    true
  );
}

/**
 * Update user by admin
 */
export function updateUserByAdmin(userId, userData) {
  return apiRequest(
    `${ADMIN_BASE}/${userId}`,
    {
      method: "PATCH",
      body: JSON.stringify(userData),
    },
    true
  );
}

/**
 * Own profile
 */
export function userProfile() {
  return apiRequest(`${USER_BASE}/my-profile`, true);
}

/**
 * Update own profile
 */
export function updateUser(userData) {
  return apiRequest(
    `${USER_BASE}/update`,
    {
      method: "PATCH",
      body: JSON.stringify(userData),
    },
    true
  );
}

/**
 * Delete user
 */
export function deleteUser(userId) {
  return apiRequest(
    `${ADMIN_BASE}/${userId}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Toggle user status (active/inactive)
 */
export function toggleUserStatus(userId) {
  return apiRequest(
    `${ADMIN_BASE}/${userId}/toggle-status`,
    {
      method: "PATCH",
    },
    true
  );
}

/**
 * Upload avatar (multipart/form-data)
 */
export function uploadAvatar(file) {
  const formData = new FormData();
  formData.append("avatar", file);
  return apiRequest(
    `${USER_BASE}/avatar`,
    {
      method: "POST",
      body: formData,
    },
    true
  );
}

/**
 * Upload customer organisation avatar (customer-admin only)
 * Hits POST /profile/customers/my/avatar
 * Used in MyProfile page where customer admin uploads their own org avatar
 */
export function uploadCustomerAvatarOwn(file) {
  const formData = new FormData();
  formData.append("avatar", file);

  return apiRequest(
    `${USER_BASE}/customers/my/avatar`,
    {
      method: "POST",
      body: formData,
    },
    true
  );
}

/**
 * Upload customer organisation avatar (admin only)
 * Hits POST /profile/customers/:customerId/avatar
 * Used in CustomerDetails page where admin uploads customer org avatar
 */
export function uploadCustomerAvatarById(file, customerId) {
  const formData = new FormData();
  formData.append("avatar", file);

  return apiRequest(
    `${ADMIN_BASE}/customers/${customerId}/avatar`,
    {
      method: "POST",
      body: formData,
    },
    true
  );
}

export function resolveAvatarUrl(avatar) {
  if (!avatar) return null;
  if (avatar.startsWith("http") || avatar.startsWith("data:")) return avatar;
  return `${import.meta.env.VITE_API_BASE_URL}${avatar}`;
}

export default {
  getAllUsers,
  getUserById,
  createUser,
  updateUserByAdmin,
  updateUser,
  deleteUser,
  toggleUserStatus,
};
