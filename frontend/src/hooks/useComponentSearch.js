import { useState, useEffect, useRef } from "react";

/**
 * Custom hook to manage search inputs, syncing with parent values and debouncing search callbacks.
 *
 * @param {object} params
 * @param {string} params.externalSearchTerm - The external search term to sync with.
 * @param {function} params.onSearch - Callback function triggered when searching.
 * @param {function} params.onClearSearch - Callback function triggered when search is cleared.
 * @param {boolean} params.loading - State representing whether the component/parent is currently loading.
 * @param {number} params.debounceDelay - Debounce delay in milliseconds.
 */
export default function useComponentSearch({
  externalSearchTerm = "",
  onSearch,
  onClearSearch,
  loading = false,
  debounceDelay = 800,
}) {
  const [internalSearchTerm, setInternalSearchTerm] = useState(
    externalSearchTerm || ""
  );
  const [isSearching, setIsSearching] = useState(false);
  const debounceTimerRef = useRef(null);

  // Sync external search term to internal when it changes (e.g., from URL params)
  useEffect(() => {
    if (
      externalSearchTerm !== undefined &&
      externalSearchTerm !== internalSearchTerm
    ) {
      setInternalSearchTerm(externalSearchTerm || "");
    }
    // Only sync when externalSearchTerm changes, not internalSearchTerm
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalSearchTerm]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const displaySearchTerm = internalSearchTerm;
  const displayIsSearching = isSearching && loading;

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setInternalSearchTerm(value);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      if (onSearch) {
        setIsSearching(true);
        onSearch(value);
      }
    }, debounceDelay);
  };

  const clearSearch = () => {
    setInternalSearchTerm("");
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    if (onClearSearch) {
      onClearSearch();
    } else if (onSearch) {
      onSearch("");
    }
  };

  return {
    internalSearchTerm,
    setInternalSearchTerm,
    displaySearchTerm,
    displayIsSearching,
    handleSearchChange,
    clearSearch,
    setIsSearching,
  };
}
