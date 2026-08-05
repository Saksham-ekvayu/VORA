/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";

/**
 * ModalTableBody — shared loading / empty / rows renderer used inside
 * picker modals (AssignFrameworkModal, GiveFrameworkAccessModal, RequestReviewModal).
 *
 * Props:
 *   loading       – boolean
 *   items         – array
 *   renderRow     – (item) => ReactNode
 *   emptyMessage  – string  (default "No results found")
 *   colSpan       – number  (default 2)
 *   loadingLabel  – string  (default "Loading...")
 */
export function ModalTableBody({
  loading,
  items,
  renderRow,
  emptyMessage = "No results found",
  colSpan = 2,
  loadingLabel = "Loading...",
}) {
  if (loading) {
    return (
      <tr>
        <td colSpan={colSpan} className="px-3 py-6 text-center">
          <div className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-muted-foreground text-sm">
              {loadingLabel}
            </span>
          </div>
        </td>
      </tr>
    );
  }

  if (!items || items.length === 0) {
    return (
      <tr>
        <td
          colSpan={colSpan}
          className="px-3 py-6 text-center text-muted-foreground text-sm"
        >
          {emptyMessage}
        </td>
      </tr>
    );
  }

  return items.map(renderRow);
}

/**
 * ModalTablePagination — shared prev/next pagination strip used in
 * AssignFrameworkModal, GiveFrameworkAccessModal, RequestReviewModal.
 *
 * Props:
 *   pagination  – { currentPage, totalPages, totalItems, limit, hasPrevPage, hasNextPage }
 *   onPageChange – (page: number) => void
 */
export function ModalTablePagination({ pagination, onPageChange }) {
  const from = (pagination.currentPage - 1) * pagination.limit + 1;
  const to = Math.min(
    pagination.currentPage * pagination.limit,
    pagination.totalItems
  );

  return (
    <div className="flex items-center justify-between px-3 py-2 border-t border-border">
      <span className="text-xs text-muted-foreground">
        Showing {from} to {to} of {pagination.totalItems} results
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(pagination.currentPage - 1)}
          disabled={!pagination.hasPrevPage}
          className="px-2 py-1 text-xs border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          Prev
        </button>
        <span className="text-[11px] text-muted-foreground px-1">
          {pagination.currentPage} / {pagination.totalPages}
        </span>
        <button
          onClick={() => onPageChange(pagination.currentPage + 1)}
          disabled={!pagination.hasNextPage}
          className="px-2 py-1 text-xs border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          Next
        </button>
      </div>
    </div>
  );
}

/**
 * ModalSearchInput — simple search input with icon, used inside picker modals
 * (AssignFrameworkModal, GiveFrameworkAccessModal, RequestReviewModal).
 *
 * Props:
 *   value        – string
 *   onChange     – (value: string) => void
 *   onClear      – () => void (optional, if not provided clear button won't show)
 *   placeholder  – string  (default "Search...")
 *   className    – extra classes
 */
export function ModalSearchInput({
  value,
  onChange,
  onClear,
  placeholder = "Search...",
  className = "",
}) {
  return (
    <div className={`relative flex-1 ${className}`}>
      <div className="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none">
        <Icon name="search" size="14px" className="text-muted-foreground" />
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-8 pr-9 h-9 text-sm rounded border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1"
      />
      {value && onClear && (
        <button
          type="button"
          onClick={onClear}
          className="absolute inset-y-0 right-0 flex items-center pr-2.5 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          aria-label="Clear search"
          title="Clear search"
        >
          <Icon name="x" size="14px" />
        </button>
      )}
    </div>
  );
}
