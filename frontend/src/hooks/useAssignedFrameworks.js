import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "@/context/authContext/useAuth";
import { getAssignmentFrameworks } from "@/services/deploymentFrameworkService";

/**
 * useAssignedFrameworks
 *
 * Replaces CustomerAssignedFrameworksContext.
 * Fetches fresh data on every mount — no stale cache.
 * Same return shape as the old context so consumers need minimal changes.
 */
export function useAssignedFrameworks() {
  const { user, isAuthenticated } = useAuth();
  const [assignedFrameworks, setAssignedFrameworks] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAssignedFrameworks = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setAssignedFrameworks([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await getAssignmentFrameworks({
        page: 1,
        limit: 1000,
      });
      if (response.success) {
        setAssignedFrameworks(response.data || []);
      }
    } catch (err) {
      console.error("Error fetching assigned frameworks:", err);
      setAssignedFrameworks([]);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, user?.role]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchAssignedFrameworks();
  }, [fetchAssignedFrameworks]);

  const hasAccessToFramework = useCallback(
    (frameworkId) => {
      if (!frameworkId) return false;
      return assignedFrameworks.some(
        (fw) =>
          fw.frameworkId === frameworkId ||
          fw.frameworkId?._id === frameworkId ||
          fw.frameworkId?.id === frameworkId
      );
    },
    [assignedFrameworks]
  );

  const getAssignedFramework = useCallback(
    (frameworkId) => {
      if (!frameworkId) return null;
      return (
        assignedFrameworks.find(
          (fw) =>
            fw.frameworkId === frameworkId ||
            fw.frameworkId?._id === frameworkId ||
            fw.frameworkId?.id === frameworkId
        ) || null
      );
    },
    [assignedFrameworks]
  );

  return useMemo(
    () => ({
      assignedFrameworks,
      loading,
      fetchAssignedFrameworks,
      refreshAssignedFrameworks: fetchAssignedFrameworks,
      hasAccessToFramework,
      getAssignedFramework,
    }),
    [
      assignedFrameworks,
      loading,
      fetchAssignedFrameworks,
      hasAccessToFramework,
      getAssignedFramework,
    ]
  );
}
