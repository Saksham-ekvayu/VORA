/* eslint-disable react/prop-types */

import { Button } from "../ui/button";
import { Skeleton } from "../ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import {
  ChevronDown,
  Folder,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  TriangleAlert,
} from "lucide-react";
import TableHeaderActions from "../custom/TableHeaderActions";
import SearchInput from "../custom/SearchInput";

/**
 * Premium GridCardView Component
 * A fully standalone reusable component for displaying data in a responsive card grid.
 *
 * @param {Array} data - The array of items to display
 * @param {Function} renderCard - Reusable render function: (item, index) => ReactNode
 * @param {boolean} loading - Loading state (shows skeletons)
 * @param {Object} pagination - Pagination config {currentPage, totalPages, totalItems, limit, onPageChange, onLimitChange}
 * @param {Function} onSearch - Search function callback
 * @param {string} searchTerm - External search term to sync
 * @param {Function} onRefresh - Refresh action callback
 * @param {Function} renderHeaderActions - Custom actions on the right side of header
 * @param {string} searchPlaceholder - Placeholder for the search input
 * @param {string} entityName - Label for the items (e.g., "Frameworks")
 * @param {string} gridCols - Tailwind grid structure (default responsive grid)
 */
export default function GridCardView({
  data = [],
  renderCard,
  loading = false,
  pagination = null,
  onSearch,
  onClearSearch,
  searchTerm: externalSearchTerm = "",
  onRefresh,
  renderHeaderActions,
  headerActions = [],
  sortOrder = "desc",
  onSortChange,
  searchPlaceholder = "Search...",
  emptyMessage = "No records found",
  entityName = "items",
  gridCols = "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3",
  error = null,
}) {
  const currentData = Array.isArray(data) ? data : [];

  const renderGridContent = () => {
    if (loading) {
      return (
        <div className={`grid gap-4 px-2 pb-2 ${gridCols}`}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={`skeleton-${i + 1}`}
              className="bg-card border border-border group rounded overflow-hidden shadow-sm flex flex-col h-full border-b-[3px] border-b-transparent animate-pulse"
            >
              {/* Card Header Skeleton */}
              <div className="p-2 flex flex-col gap-1">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2">
                    <Skeleton className="w-8 h-8 rounded bg-primary/5" />
                    <div className="flex flex-col gap-1">
                      <Skeleton className="h-3 w-16 rounded" />
                      <Skeleton className="h-2 w-10 rounded" />
                    </div>
                  </div>
                  <Skeleton className="h-8 w-8 rounded" />
                </div>

                <div className="mt-1">
                  <Skeleton className="h-4 w-3/4 rounded mb-1" />
                  <Skeleton className="h-4 w-1/2 rounded" />
                </div>

                {/* File Section Skeleton */}
                <div className="flex items-center justify-between p-2 bg-muted/20 rounded border border-border/40 mt-1">
                  <div className="flex items-center gap-2 flex-1">
                    <Skeleton className="w-7 h-7 rounded shrink-0" />
                    <div className="flex flex-col gap-1 flex-1">
                      <Skeleton className="h-2.5 w-full rounded" />
                      <Skeleton className="h-2 w-1/3 rounded" />
                    </div>
                  </div>
                  <Skeleton className="h-4 w-12 rounded ml-2" />
                </div>

                {/* Status Indicators Skeleton */}
                <div className="grid grid-cols-2 gap-3 mt-1">
                  <div className="border border-border/50 rounded p-1 flex flex-col gap-1">
                    <Skeleton className="h-2 w-12 rounded" />
                    <Skeleton className="h-7 w-full rounded" />
                  </div>
                  <div className="border border-border/50 rounded p-1 flex flex-col gap-1">
                    <Skeleton className="h-2 w-12 rounded" />
                    <Skeleton className="h-7 w-full rounded" />
                  </div>
                </div>
              </div>

              {/* User Info (Footer) Skeleton */}
              <div className="mt-auto px-3.5 py-2.5 bg-muted/5 border-t border-border/50 flex items-center gap-2.5">
                <Skeleton className="w-8 h-8 rounded shrink-0" />
                <div className="flex justify-between w-full items-center">
                  <div className="flex flex-col gap-1.5 flex-1">
                    <Skeleton className="h-2.5 w-24 rounded" />
                    <Skeleton className="h-2 w-32 rounded" />
                  </div>
                  <Skeleton className="h-3 w-14 rounded" />
                </div>
              </div>

              {/* Action Buttons Skeleton */}
              <div className="p-1 bg-card border-t border-border/50 flex items-center gap-2">
                <Skeleton className="flex-1 h-8 rounded" />
                <Skeleton className="flex-1 h-8 rounded" />
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (currentData.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-16 bg-muted/20 border border-dashed border-border/80 rounded animate-in zoom-in duration-300 p-1">
          <div
            className={`w-16 h-16 rounded shadow-sm flex items-center justify-center mb-4 ring-8 ring-muted/5 ${
              error ? "bg-red-500/10 text-red-500" : "bg-card text-muted-foreground/30"
            }`}
          >
            {error ? (
              <TriangleAlert size={30} className="text-red-500" />
            ) : (
              <Folder size={30} />
            )}
          </div>
          <h4
            className={`text-lg font-bold tracking-tight mb-1 opacity-80 ${
              error ? "text-red-500" : ""
            }`}
          >
            {emptyMessage}
          </h4>
          <p
            className={`max-w-xs text-center text-xs font-medium leading-relaxed ${
              error ? "text-red-500/80" : "text-muted-foreground"
            }`}
          >
            {error
              ? "Please check your backend logs or try again later"
              : "No results match your search. Try adjusting filters and try again."}
          </p>
        </div>
      );
    }

    return (
      <div className={`grid gap-4 px-2 pb-2 ${gridCols}`}>
        {currentData.map((item, index) => renderCard(item, index))}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-2 w-full animate-in fade-in duration-500 relative bg-card border border-border rounded">
      {/* Integrated Header: Search + Pagination + Limit + Actions */}
      <div className="sticky top-14 z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-3 bg-card/90 backdrop-blur-md p-2 border-b rounded-t shadow-sm">
        <div className="flex flex-col sm:flex-row items-center gap-3 flex-1">
          {/* Search bar */}
          <SearchInput
            debounced
            searchTerm={externalSearchTerm}
            onSearch={onSearch}
            onClearSearch={onClearSearch}
            loading={loading}
            debounceDelay={800}
            placeholder={searchPlaceholder}
            className="flex-1 min-w-60"
          />

          {/* Inline Pagination & Limit & Sort */}
          {pagination && pagination.totalPages > 0 && (
            <div className="flex items-center gap-2 px-2 py-1 bg-muted/10 border border-border/30 rounded h-9">
              {/* Pagination arrows */}
              <div className="flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground/60 hover:text-foreground rounded"
                  onClick={() =>
                    pagination.onPageChange(pagination.currentPage - 1)
                  }
                  disabled={!pagination.hasPrevPage || loading}
                >
                  <ChevronLeft size={14} />
                </Button>
                <div className="text-[11px] font-bold px-2 whitespace-nowrap">
                  <span className="text-foreground">
                    {pagination.currentPage}
                  </span>
                  <span className="text-muted-foreground/40 mx-1">/</span>
                  <span className="text-muted-foreground/70">
                    {pagination.totalPages}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground/60 hover:text-foreground rounded"
                  onClick={() =>
                    pagination.onPageChange(pagination.currentPage + 1)
                  }
                  disabled={!pagination.hasNextPage || loading}
                >
                  <ChevronRight size={14} />
                </Button>
              </div>
              <div className="w-px h-4 bg-border/40 mx-1" />

              {pagination.onLimitChange && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-1.5 hover:bg-muted font-bold gap-1 text-foreground rounded text-[10px]"
                    >
                      {pagination.limit}
                      <ChevronDown size={10} className="opacity-40" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    className="min-w-20 rounded shadow-lg border-border/50"
                  >
                    {["3", "6", "12", "24", "48"].map((val) => (
                      <DropdownMenuItem
                        key={val}
                        onClick={() => pagination.onLimitChange(Number(val))}
                        className="font-medium cursor-pointer rounded text-[10px]"
                      >
                        {val} per page
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}

              <div className="w-px h-4 bg-border/40 mx-1" />

              {/* Sort Toggle */}
              {onSortChange && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground/60 hover:text-foreground rounded hover:bg-muted/50"
                  onClick={() =>
                    onSortChange(sortOrder === "asc" ? "desc" : "asc")
                  }
                  title={`Sort: ${sortOrder === "asc" ? "Ascending" : "Descending"}`}
                >
                  <div
                    className={`transition-transform duration-200 ${sortOrder === "desc" ? "rotate-180" : ""}`}
                  >
                    <ChevronDown size={14} />
                  </div>
                </Button>
              )}

              <div className="w-px h-4 bg-border/40 mx-1" />

              <div className="text-[11px] text-muted-foreground/80 whitespace-nowrap">
                Showing{" "}
                {Math.min(
                  (pagination.currentPage - 1) * pagination.limit + 1,
                  pagination.totalItems
                )}{" "}
                to{" "}
                {Math.min(
                  pagination.currentPage * pagination.limit,
                  pagination.totalItems
                )}{" "}
                of {pagination.totalItems} {entityName}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {renderHeaderActions?.()}
          <TableHeaderActions actions={headerActions} />
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              className="h-9 px-3 border-border/60 bg-card hover:bg-accent transition-colors shadow-sm rounded text-[11px] font-bold"
              onClick={onRefresh}
              disabled={loading}
            >
              <RefreshCw
                size={12}
                className={loading ? "animate-spin mr-1.5" : "mr-1.5"}
              />
              Refresh
            </Button>
          )}
        </div>
      </div>

      {/* Main Grid Content */}
      {renderGridContent()}
    </div>
  );
}
