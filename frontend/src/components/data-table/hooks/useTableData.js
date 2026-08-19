import { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";

/**
 * Custom hook for managing table data with URL-based state management
 *
 * @param {Function} fetchFunction - API function to fetch data
 * @param {Object} options - Configuration options
 * @param {number} options.defaultLimit - Default items per page (default: 10)
 * @param {string} options.defaultSortBy - Default sort field (default: "createdAt")
 * @param {string} options.defaultSortOrder - Default sort order (default: "desc")
 * @param {string} options.emptyMessage - Default empty message
 * @param {Function} options.onError - Custom error handler
 * @param {Array} options.additionalDeps - Additional dependencies for fetch
 *
 * @returns {Object} - Table state and handlers
 */
export function useTableData(fetchFunction, options = {}) {
  const {
    defaultLimit = 10,
    defaultSortBy = "createdAt",
    defaultSortOrder = "desc",
    emptyMessage: defaultEmptyMessage = "No data found",
    onError,
    additionalDeps = [],
  } = options;

  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [data, setData] = useState([]);
  const [rawData, setRawData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [emptyMessage, setEmptyMessage] = useState(defaultEmptyMessage);

  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    limit: defaultLimit,
    hasPrevPage: false,
    hasNextPage: false,
  });

  const [searchTerm, setSearchTerm] = useState("");
  const [sortConfig, setSortConfig] = useState({
    sortBy: defaultSortBy,
    sortOrder: defaultSortOrder,
  });

  /* ---------------- URL SYNC ---------------- */
  useEffect(() => {
    const page = Number.parseInt(searchParams.get("page")) || 1;
    const search = searchParams.get("search") || "";
    const sortBy = searchParams.get("sortBy") || defaultSortBy;
    const sortOrder = searchParams.get("sortOrder") || defaultSortOrder;
    const limit = Number.parseInt(searchParams.get("limit")) || defaultLimit;

    setPagination((p) => ({ ...p, currentPage: page, limit }));
    setSearchTerm(search);
    setSortConfig({ sortBy, sortOrder });
  }, [searchParams, defaultSortBy, defaultSortOrder, defaultLimit]);

  /* ---------------- FETCH DATA ---------------- */
  const fetchData = useCallback(async () => {
    setLoading(true);

    // Read values directly from URL params to avoid stale state
    const page = Number.parseInt(searchParams.get("page")) || 1;
    const search = searchParams.get("search") || "";
    const sortBy = searchParams.get("sortBy") || defaultSortBy;
    const sortOrder = searchParams.get("sortOrder") || defaultSortOrder;
    const limit = Number.parseInt(searchParams.get("limit")) || defaultLimit;

    // Build query params object
    const queryParams = {
      page,
      limit,
      search,
      sortBy,
      sortOrder,
    };

    // Add any additional query params from URL
    for (const [key, value] of searchParams.entries()) {
      if (!["page", "search", "sortBy", "sortOrder", "limit"].includes(key)) {
        queryParams[key] = value;
      }
    }

    try {
      const res = await fetchFunction(queryParams);

      setRawData(res.data);

      let actualData = [];
      if (Array.isArray(res.data)) {
        actualData = res.data;
      } else if (res.data && typeof res.data === "object") {
        actualData = res.data.results || res.data.frameworks || res.data.items || [];
      }

      setData(actualData);

      // Handle empty message
      if (res.message && actualData.length === 0) {
        setEmptyMessage(res.message);
      } else if (search && actualData.length === 0) {
        setEmptyMessage(`No results found for "${search}"`);
      } else {
        setEmptyMessage(defaultEmptyMessage);
      }

      // Update pagination
      setPagination((p) => ({
        ...p,
        currentPage: page,
        limit,
        totalPages: res.pagination?.totalPages || 1,
        totalItems: res.pagination?.totalItems || 0,
        hasPrevPage: page > 1,
        hasNextPage: page < (res.pagination?.totalPages || 1),
      }));

      return res.data || [];
    } catch (err) {
      const errorMessage = err.message || "Failed to load data";

      if (onError) {
        onError(err);
      } else {
        toast.error(errorMessage);
      }

      setData([]);
      setRawData(null);
      setEmptyMessage(errorMessage);
      return [];
    } finally {
      setLoading(false);
    }
  }, [
    searchParams,
    fetchFunction,
    defaultEmptyMessage,
    defaultSortBy,
    defaultSortOrder,
    defaultLimit,
    onError,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    ...additionalDeps,
  ]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ---------------- HANDLERS ---------------- */
  const handlePageChange = useCallback(
    (page) => {
      const p = new URLSearchParams(searchParams);
      p.set("page", page);
      setSearchParams(p);
    },
    [searchParams, setSearchParams]
  );

  const handleSearch = useCallback(
    (term) => {
      const p = new URLSearchParams(searchParams);
      term ? p.set("search", term) : p.delete("search");
      p.set("page", "1");
      setSearchParams(p);
    },
    [searchParams, setSearchParams]
  );

  const handleSort = useCallback(
    (key) => {
      const order =
        sortConfig.sortBy === key && sortConfig.sortOrder === "asc"
          ? "desc"
          : "asc";

      const p = new URLSearchParams(searchParams);
      p.set("sortBy", key);
      p.set("sortOrder", order);
      p.set("page", "1");
      setSearchParams(p);

      setSortConfig({ sortBy: key, sortOrder: order });
    },
    [sortConfig, searchParams, setSearchParams]
  );

  const handleFilterChange = useCallback(
    (filterKey, filterValue) => {
      const p = new URLSearchParams(searchParams);
      filterValue ? p.set(filterKey, filterValue) : p.delete(filterKey);
      p.set("page", "1");
      setSearchParams(p);
    },
    [searchParams, setSearchParams]
  );

  const handleLimitChange = useCallback(
    (newLimit) => {
      const p = new URLSearchParams(searchParams);
      p.set("limit", newLimit);
      p.set("page", "1"); // Reset to first page when changing limit
      setSearchParams(p);
    },
    [searchParams, setSearchParams]
  );

  const refetch = useCallback(() => {
    return fetchData();
  }, [fetchData]);

  return {
    // Data
    data,
    loading,
    emptyMessage,

    // Pagination
    pagination: {
      ...pagination,
      onPageChange: handlePageChange,
      onLimitChange: handleLimitChange,
    },

    // Search & Sort
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,

    // Filters
    onFilterChange: handleFilterChange,

    // Utilities
    refetch,
    setData,
    setLoading,
    rawData,
  };
}
