/* eslint-disable react/prop-types */

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Icon from "@/components/custom/Icon";
import { Search } from "lucide-react";
import useComponentSearch from "@/hooks/useComponentSearch";

/**
 * GlobalSearchInput — single reusable search input used across the entire app.
 *
 * Two modes:
 *
 * 1. SIMPLE mode (default) — for inline/sidebar searches where the parent
 *    controls the value directly (no debounce, no spinner).
 *    Props: value, onChange, onClear, placeholder, className
 *
 * 2. DEBOUNCED mode — for DataTable / GridCardView where the search fires a
 *    server-side callback after a delay and shows a spinner while loading.
 *    Activated by passing `debounced={true}`.
 *    Props: debounced, searchTerm, onSearch, onClearSearch, loading,
 *           debounceDelay, placeholder, className
 *
 * Common optional props:
 *   placeholder   – input placeholder text   (default "Search…")
 *   className     – extra classes on <Input>
 */
export default function SearchInput({
  // --- simple mode ---
  value,
  onChange,
  onClear,

  // --- debounced mode ---
  debounced = false,
  searchTerm: externalSearchTerm = "",
  onSearch,
  onClearSearch,
  loading = false,
  debounceDelay = 800,

  // --- shared ---
  placeholder = "Search…",
  className = "",
}) {
  const {
    displaySearchTerm,
    displayIsSearching,
    handleSearchChange,
    clearSearch,
  } = useComponentSearch({
    externalSearchTerm: debounced ? externalSearchTerm : "",
    onSearch: debounced ? onSearch : undefined,
    onClearSearch: debounced ? onClearSearch : undefined,
    loading,
    debounceDelay,
  });

  const inputValue = debounced ? displaySearchTerm : value;
  const isSearching = debounced ? displayIsSearching : false;
  const hasValue = Boolean(inputValue);

  const handleChange = (e) => {
    const val = e.target.value.trimStart();
    if (debounced) {
      handleSearchChange({ target: { value: val } });
    } else {
      onChange?.(val);
    }
  };

  const handleClear = debounced ? clearSearch : () => onClear?.();

  return (
    <div className="relative w-full">
      <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
      <Input
        type="text"
        placeholder={placeholder}
        value={inputValue}
        onChange={handleChange}
        className={`h-8 pl-9 pr-8 text-xs ${className}`}
      />
      <div className="absolute inset-y-0 right-0 flex items-center gap-1 pr-2">
        {isSearching && (
          <div className="w-3 h-3 border-2 border-border border-t-primary rounded-full animate-spin" />
        )}
        {hasValue && !isSearching && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClear}
            className="h-5 w-5 hover:bg-accent rounded-full"
            title="Clear search"
          >
            <Icon name="close" size="12px" />
          </Button>
        )}
      </div>
    </div>
  );
}
