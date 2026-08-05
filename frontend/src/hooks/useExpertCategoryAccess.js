import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "@/context/authContext/useAuth";
import { isExpert } from "@/utils/commonUtils";
import { getFrameworkCategoryAccess } from "@/services/frameworkService";

/**
 * useExpertCategoryAccess
 *
 * Replaces ExpertAccessContext.
 * Fetches fresh data on every mount — no stale cache.
 * Same return shape as the old context so consumers need minimal changes.
 */
export function useExpertCategoryAccess() {
  const { user, isAuthenticated } = useAuth();
  const [accessibleCategories, setAccessibleCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAccessibleCategories = useCallback(async () => {
    if (!isAuthenticated || !isExpert(user?.role)) {
      setAccessibleCategories([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await getFrameworkCategoryAccess({
        page: 1,
        limit: 100,
      });
      if (response.success) {
        const approved = (response.data || [])
          .filter((access) => access.status === "approved")
          .map((access) => access.frameworkCategory);
        setAccessibleCategories(approved);
      }
    } catch (err) {
      console.error("Error fetching accessible categories:", err);
      setAccessibleCategories([]);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, user?.role]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchAccessibleCategories();
  }, [fetchAccessibleCategories]);

  const hasAccessToCategory = useCallback(
    (categoryId) => {
      if (!categoryId) return false;
      return accessibleCategories.some(
        (cat) => cat.id === categoryId || cat._id === categoryId
      );
    },
    [accessibleCategories]
  );

  const getAccessibleCategory = useCallback(
    (categoryId) => {
      if (!categoryId) return null;
      return (
        accessibleCategories.find(
          (cat) => cat.id === categoryId || cat._id === categoryId
        ) || null
      );
    },
    [accessibleCategories]
  );

  return useMemo(
    () => ({
      accessibleCategories,
      loading,
      fetchAccessibleCategories,
      refreshAccess: fetchAccessibleCategories,
      hasAccessToCategory,
      getAccessibleCategory,
    }),
    [
      accessibleCategories,
      loading,
      fetchAccessibleCategories,
      hasAccessToCategory,
      getAccessibleCategory,
    ]
  );
}
