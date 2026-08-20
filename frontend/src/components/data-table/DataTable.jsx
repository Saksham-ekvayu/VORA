/* eslint-disable react/prop-types */

import Icon from "../custom/Icon";
import { Button } from "../ui/button";
import { Skeleton } from "../ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import TableHeaderActions from "../custom/TableHeaderActions";
import SearchInput from "../custom/SearchInput";
import CustomPagination from "../custom/CustomPagination";

/**
 * Reusable DataTable Component
 * Features: sorting, pagination, search/filtering, loading states, empty states
 *
 * @param {Array} columns - Column configuration array [{key, label, sortable, render}]
 * @param {Array} data - Array of data objects
 * @param {Object} pagination - Pagination config {currentPage, totalPages, totalItems, limit, onPageChange}
 * @param {Function} onSearch - Search handler function
 * @param {Function} onSort - Sort handler function (for server-side sorting)
 * @param {Object} sortConfig - Current sort configuration {sortBy, sortOrder}
 * @param {boolean} loading - Loading state
 * @param {string} emptyMessage - Message to show when no data
 * @param {Function} renderActions - Function to render action buttons for each row
 * @param {string} searchPlaceholder - Placeholder text for search input
 * @param {string} entityName - Name of the entity for pagination text (e.g. "Users", "Frameworks")
 * @param {Function} renderHeaderActions - Function to render custom actions in table header
 */
export default function DataTable({
  columns = [],
  data = [],
  pagination = null,
  onSearch,
  onSort,
  sortConfig = { sortBy: null, sortOrder: "asc" },
  loading = false,
  emptyMessage = "No data found",
  renderActions,
  searchPlaceholder = "Search...",
  error = null,
  onRefresh,
  searchTerm: externalSearchTerm = "",
  onClearSearch,
  renderHeaderActions,
  headerActions = [],
  entityName = "Records",
}) {
  // Handle sorting
  const handleSort = (key) => {
    if (!columns.find((col) => col.key === key)?.sortable) return;

    // Use server-side sorting if onSort function is provided
    if (onSort) {
      onSort(key);
    } else {
      // Fallback to client-side sorting (legacy behavior)
      console.warn(
        "Client-side sorting with server-side pagination is not recommended"
      );
    }
  };

  // Ensure data is always an array
  const sortedData = Array.isArray(data) ? data : [];

  const getSerialNumber = (index, pagination) => {
    if (!pagination) return index + 1;
    return (pagination.currentPage - 1) * pagination.limit + index + 1;
  };

  const handlePageChange = (event, page, disabled = false) => {
    event.preventDefault();
    if (disabled) return;
    pagination.onPageChange(page);
  };

  // Render sort indicator
  const renderSortIndicator = (column) => {
    if (!column.sortable) return null;

    if (sortConfig.sortBy === column.key) {
      return (
        <span className="opacity-100 text-blue-500">
          <Icon
            name={sortConfig.sortOrder === "asc" ? "arrow-up" : "arrow-down"}
            size="12px"
          />
        </span>
      );
    }
    return (
      <span className="opacity-30 transition-opacity duration-200">
        <Icon name="arrow-up" size="12px" />
      </span>
    );
  };

  const emptyColSpan = columns.length + 1 + (renderActions ? 1 : 0);

  const renderTableBody = () => {
    if (loading) {
      return Array.from({
        length: sortedData.length || pagination?.totalItems || 7,
      }).map((_, i) => (
        <TableRow
          key={`skeleton-${i + 1}`}
          className="border-b border-border hover:bg-transparent"
        >
          <TableCell className="sticky left-0 z-10 w-16 px-4 py-3 sticky-sr-col">
            <Skeleton className="w-8 h-8 rounded-full" />
          </TableCell>
          {columns.map((column) => (
            <TableCell key={column.key} className="px-4 py-3">
              <Skeleton className="h-4 w-full rounded" />
            </TableCell>
          ))}
          {renderActions && (
            <TableCell className="w-20 px-2 py-3">
              <Skeleton className="h-4 w-10 rounded mx-auto" />
            </TableCell>
          )}
        </TableRow>
      ));
    }

    if (sortedData.length === 0) {
      return [
        <TableRow key="empty-state" className="hover:bg-transparent">
          <TableCell colSpan={emptyColSpan} className="text-center py-12 px-4">
            <div className="flex flex-col items-center gap-4 text-muted-foreground">
              <div
                className={`w-16 h-16 rounded-full flex items-center justify-center ${error ? "bg-red-500/10 text-red-500" : "bg-muted"}`}
              >
                <Icon
                  name={error ? "triangle-alert" : "folder"}
                  size="32px"
                  className={error ? "" : "opacity-50"}
                />
              </div>
              <div className="text-center">
                <p
                  className={`text-base font-medium ${error ? "text-red-500" : "text-muted-foreground"}`}
                >
                  {emptyMessage}
                </p>
                <p
                  className={`text-sm mt-1 ${error ? "text-red-500/80" : "text-muted-foreground/70"}`}
                >
                  {error
                    ? "Please check your backend logs or try again later"
                    : "Try adjusting your search or filters"}
                </p>
              </div>
            </div>
          </TableCell>
        </TableRow>,
      ];
    }

    return sortedData.map((row, index) => (
      <TableRow
        key={row.id || index}
        className="transition-all duration-200 hover:bg-accent group"
      >
        {/* SR NO */}
        <TableCell className="sticky left-0 z-10 w-16 px-4 py-2.5 text-sm text-foreground align-middle sticky-sr-col transition-colors duration-200">
          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-muted-foreground text-xs font-medium group-hover:bg-primary/10 group-hover:text-primary transition-all duration-200">
            {getSerialNumber(index, pagination)}
          </div>
        </TableCell>
        {columns.map((column) => (
          <TableCell
            key={column.key}
            className="px-4 py-2.5 text-sm text-foreground align-middle"
          >
            {column.render
              ? column.render(row[column.key], row)
              : row[column.key]}
          </TableCell>
        ))}
        {renderActions && (
          <TableCell className="w-20 px-2 py-2.5 text-center align-middle">
            {renderActions(row)}
          </TableCell>
        )}
      </TableRow>
    ));
  };

  return (
    <div className="bg-card border border-border rounded overflow-hidden">
      {/* Table Header with Search */}
      <div className="flex justify-between gap-2 items-center p-2 border-b border-border bg-linear-to-r from-card to-muted/30">
        <div className="flex items-center gap-3 flex-1 max-w-xl">
          <SearchInput
            debounced
            searchTerm={externalSearchTerm}
            onSearch={onSearch}
            onClearSearch={onClearSearch}
            loading={loading}
            debounceDelay={1000}
            placeholder={searchPlaceholder}
            className="flex-1"
          />
        </div>
        <div className="flex items-center gap-2">
          {renderHeaderActions?.()}
          <TableHeaderActions actions={headerActions} />
          {onRefresh && (
            <Button
              size="lg"
              className="flex items-center gap-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={onRefresh}
              disabled={loading}
            >
              <Icon name="refresh" size="16px" />
              Refresh
            </Button>
          )}
        </div>
      </div>

      {/* Table Container with Scrollable Body and Sticky Header */}
      <div
        className="overflow-auto sidebar-scroll"
        style={{ maxHeight: "calc(100vh - 200px)" }}
      >
        <Table
          className="border-collapse"
          containerClassName="overflow-visible"
        >
          <TableHeader className="sticky top-0 z-20 bg-muted">
            <TableRow className="bg-linear-to-r from-muted to-muted/50 hover:bg-transparent">
              <TableHead className="sticky left-0 w-16 px-4 py-2.5 text-left border-b border-border font-semibold text-xs text-muted-foreground uppercase tracking-wider whitespace-nowrap sticky-sr-header">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-primary text-xs font-bold">
                    #
                  </span>
                </div>
              </TableHead>
              {columns.map((column) => (
                <TableHead
                  key={column.key}
                  onClick={() => handleSort(column.key)}
                  className={`px-4 py-2.5 text-left border-b border-border font-semibold text-xs text-muted-foreground uppercase tracking-wider whitespace-nowrap bg-muted ${column.sortable
                    ? "cursor-pointer select-none transition-all duration-200 hover:bg-accent/50 hover:text-primary"
                    : ""
                    }`}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.label}</span>
                    {renderSortIndicator(column)}
                  </div>
                </TableHead>
              ))}
              {renderActions && (
                <TableHead className="w-20 px-2 py-2.5 text-center border-b border-border font-semibold text-xs text-muted-foreground uppercase tracking-wider whitespace-nowrap bg-muted">
                  Actions
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-border">
            {renderTableBody()}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <CustomPagination
        pagination={pagination}
        onPageChange={handlePageChange}
        loading={loading}
        entityName={entityName}
      />
    </div>
  );
}
