import { useState, useCallback, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

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
    prefix = "",
  } = options;

  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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
    const page = Number.parseInt(searchParams.get(`${prefix}page`)) || 1;
    const search = searchParams.get(`${prefix}search`) || "";
    const sortBy = searchParams.get(`${prefix}sortBy`) || defaultSortBy;
    const sortOrder =
      searchParams.get(`${prefix}sortOrder`) || defaultSortOrder;
    const limit =
      Number.parseInt(searchParams.get(`${prefix}limit`)) || defaultLimit;

    setPagination((p) => ({ ...p, currentPage: page, limit }));
    setSearchTerm(search);
    setSortConfig({ sortBy, sortOrder });
  }, [searchParams, defaultSortBy, defaultSortOrder, defaultLimit, prefix]);

  const queryParamsObj = useMemo(() => {
    const page = Number.parseInt(searchParams.get(`${prefix}page`)) || 1;
    const search = searchParams.get(`${prefix}search`) || "";
    const sortBy = searchParams.get(`${prefix}sortBy`) || defaultSortBy;
    const sortOrder =
      searchParams.get(`${prefix}sortOrder`) || defaultSortOrder;
    const limit =
      Number.parseInt(searchParams.get(`${prefix}limit`)) || defaultLimit;

    const params = { page, limit, search, sortBy, sortOrder };

    for (const [key, value] of searchParams.entries()) {
      if (prefix && key.startsWith(prefix)) {
        const strippedKey = key.slice(prefix.length);
        if (
          !["page", "search", "sortBy", "sortOrder", "limit"].includes(
            strippedKey
          )
        ) {
          params[strippedKey] = value;
        }
      } else if (
        !prefix &&
        !["page", "search", "sortBy", "sortOrder", "limit"].includes(key)
      ) {
        params[key] = value;
      }
    }
    return params;
  }, [searchParams, prefix, defaultLimit, defaultSortBy, defaultSortOrder]);

  // Used to prevent unnecessary refetches when unrelated search params change
  const queryParamsString = JSON.stringify(queryParamsObj);

  /* ---------------- FETCH DATA ---------------- */
  const fetchData = useCallback(
    async (paramsToFetch) => {
      setLoading(true);

      try {
        setError(null);
        const res = await fetchFunction(paramsToFetch);

        setData(res.data || []);

        // Handle empty message
        if (res.message && res.data?.length === 0) {
          setEmptyMessage(res.message);
        } else if (paramsToFetch.search && res.data?.length === 0) {
          setEmptyMessage(`No results found for "${paramsToFetch.search}"`);
        } else {
          setEmptyMessage(defaultEmptyMessage);
        }

        // Update pagination
        setPagination((p) => ({
          ...p,
          currentPage: paramsToFetch.page,
          limit: paramsToFetch.limit,
          totalPages: res.pagination?.totalPages || 1,
          totalItems: res.pagination?.totalItems || 0,
          hasPrevPage: paramsToFetch.page > 1,
          hasNextPage: paramsToFetch.page < (res.pagination?.totalPages || 1),
        }));

        return res.data || [];
      } catch (err) {
        const errorMessage = err.message || "Failed to load data";

        if (onError) {
          onError(err);
        }

        setData([]);
        setError(errorMessage);
        setEmptyMessage(errorMessage);
        return [];
      } finally {
        setLoading(false);
      }
    },
    [
      fetchFunction,
      defaultEmptyMessage,
      onError,
      // eslint-disable-next-line react-hooks/exhaustive-deps
      ...additionalDeps,
    ]
  );

  useEffect(() => {
    fetchData(JSON.parse(queryParamsString));
  }, [fetchData, queryParamsString]);

  /* ---------------- HANDLERS ---------------- */
  const handlePageChange = useCallback(
    (page) => {
      const p = new URLSearchParams(searchParams);
      p.set(`${prefix}page`, page);
      setSearchParams(p);
    },
    [searchParams, setSearchParams, prefix]
  );

  const handleSearch = useCallback(
    (term) => {
      const p = new URLSearchParams(searchParams);
      term ? p.set(`${prefix}search`, term) : p.delete(`${prefix}search`);
      p.set(`${prefix}page`, "1");
      setSearchParams(p);
    },
    [searchParams, setSearchParams, prefix]
  );

  const handleSort = useCallback(
    (key) => {
      const order =
        sortConfig.sortBy === key && sortConfig.sortOrder === "asc"
          ? "desc"
          : "asc";

      const p = new URLSearchParams(searchParams);
      p.set(`${prefix}sortBy`, key);
      p.set(`${prefix}sortOrder`, order);
      p.set(`${prefix}page`, "1");
      setSearchParams(p);

      setSortConfig({ sortBy: key, sortOrder: order });
    },
    [sortConfig, searchParams, setSearchParams, prefix]
  );

  const handleFilterChange = useCallback(
    (filterKey, filterValue) => {
      const p = new URLSearchParams(searchParams);
      filterValue
        ? p.set(`${prefix}${filterKey}`, filterValue)
        : p.delete(`${prefix}${filterKey}`);
      p.set(`${prefix}page`, "1");
      setSearchParams(p);
    },
    [searchParams, setSearchParams, prefix]
  );

  const handleLimitChange = useCallback(
    (newLimit) => {
      const p = new URLSearchParams(searchParams);
      p.set(`${prefix}limit`, newLimit);
      p.set(`${prefix}page`, "1"); // Reset to first page when changing limit
      setSearchParams(p);
    },
    [searchParams, setSearchParams, prefix]
  );

  const refetch = useCallback(() => {
    return fetchData(JSON.parse(queryParamsString));
  }, [fetchData, queryParamsString]);

  return {
    // Data
    data,
    loading,
    error,
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
  };
}
