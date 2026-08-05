import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import useDebounce from "@/hooks/useDebounce";

/**
 * useModalPaginatedList
 *
 * Encapsulates the repeated paginated-list state used in every
 * dual-table picker modal (AssignFrameworkModal, GiveFrameworkAccessModal,
 * RequestReviewModal, etc.).
 *
 * Each "panel" (left / right table) in those modals had:
 *   - items []
 *   - loading boolean
 *   - pagination { currentPage, totalPages, totalItems, limit, hasPrevPage, hasNextPage }
 *   - searchTerm + debounced variant
 *   - a fetchFn callback that called the API, set items, updated pagination
 *
 * This hook wires all of that up in one place.
 *
 * @param {Function} fetchFn
 *   Async function that receives `{ page, limit, search, ...extraParams }` and
 *   must return `{ data: [...], pagination: { totalPages, totalItems } }`.
 *
 * @param {Object}  options
 * @param {number}  options.limit          – page size  (default 5)
 * @param {number}  options.debounceDelay  – search debounce ms  (default 500)
 * @param {boolean} options.enabled        – set false to skip fetching  (default true)
 * @param {Object}  options.extraParams    – additional params merged into every fetch call
 * @param {string}  options.errorMessage   – toast error prefix  (default "Failed to load items")
 *
 * @returns {{
 *   items: any[],
 *   loading: boolean,
 *   pagination: object,
 *   searchTerm: string,
 *   setSearchTerm: Function,
 *   onPageChange: Function,
 *   refetch: Function,
 * }}
 */
export default function useModalPaginatedList(fetchFn, options = {}) {
  const {
    limit = 5,
    debounceDelay = 500,
    enabled = true,
    extraParams = {},
    errorMessage = "Failed to load items",
  } = options;

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    limit,
    hasPrevPage: false,
    hasNextPage: false,
  });

  const debouncedSearch = useDebounce(searchTerm, debounceDelay);

  const fetchItems = useCallback(async () => {
    if (!enabled) return;

    setLoading(true);
    try {
      const res = await fetchFn({
        page: pagination.currentPage,
        limit: pagination.limit,
        search: debouncedSearch,
        ...extraParams,
      });

      setItems(res.data || []);
      setPagination((prev) => ({
        ...prev,
        totalPages: res.pagination?.totalPages || 1,
        totalItems: res.pagination?.totalItems || 0,
        hasPrevPage: prev.currentPage > 1,
        hasNextPage: prev.currentPage < (res.pagination?.totalPages || 1),
      }));
    } catch (err) {
      toast.error(err.message || errorMessage);
      setItems([]);
    } finally {
      setLoading(false);
    }
    // extraParams is excluded from deps intentionally — callers should pass a
    // stable reference (useMemo / module constant) to avoid infinite loops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    fetchFn,
    pagination.currentPage,
    pagination.limit,
    debouncedSearch,
    enabled,
  ]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const onPageChange = useCallback((page) => {
    setPagination((prev) => ({ ...prev, currentPage: page }));
  }, []);

  // When search changes, reset to page 1
  const handleSetSearchTerm = useCallback((term) => {
    setSearchTerm(term);
    setPagination((prev) => ({ ...prev, currentPage: 1 }));
  }, []);

  return {
    items,
    loading,
    pagination,
    searchTerm,
    setSearchTerm: handleSetSearchTerm,
    onPageChange,
    refetch: fetchItems,
  };
}
