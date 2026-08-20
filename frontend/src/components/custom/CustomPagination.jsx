import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from "../ui/pagination";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { Label } from "../ui/label";
import { Button } from "../ui/button";
import { ChevronDown } from "lucide-react";
import Icon from "./Icon";

// Helper function to generate page numbers with ellipsis
function generatePageNumbers(currentPage, totalPages) {
  const pages = [];
  const delta = 2;

  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) {
      pages.push(i);
    }
  } else {
    pages.push(1);

    if (currentPage > delta + 2) {
      pages.push("...");
    }

    const start = Math.max(2, currentPage - delta);
    const end = Math.min(totalPages - 1, currentPage + delta);

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (currentPage < totalPages - delta - 1) {
      pages.push("...");
    }

    pages.push(totalPages);
  }

  return pages;
}

export default function CustomPagination({
  pagination,
  onPageChange,
  loading = false,
  entityName = "items",
}) {
  if (!pagination || pagination.totalPages <= 0) return null;

  const handlePageChange = (event, page, isDisabled) => {
    event.preventDefault();
    if (isDisabled) return;
    if (onPageChange) {
      onPageChange(page);
    } else if (pagination.onPageChange) {
      pagination.onPageChange(page);
    }
  };

  return (
    <div className="flex justify-between items-center px-4 py-3 border-t border-border bg-muted flex-wrap gap-4 text-muted-foreground">
      <div className="flex items-center gap-4">
        <div className="text-sm">
          Showing {(pagination.currentPage - 1) * pagination.limit + 1} to{" "}
          {Math.min(
            pagination.currentPage * pagination.limit,
            pagination.totalItems
          )}{" "}
          of {pagination.totalItems} {entityName}
        </div>
        {pagination.onLimitChange && (
          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">Rows per page:</Label>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="xs"
                  className="justify-between rounded min-w-12.5 select-none"
                  disabled={loading}
                >
                  <span>{pagination.limit}</span>
                  <ChevronDown className="h-4 w-4 opacity-50" />
                </Button>
              </DropdownMenuTrigger>

              <DropdownMenuContent
                align="center"
                className="min-w-12.5 p-0 rounded"
              >
                {["5", "10", "25", "50", "100"].map((value) => (
                  <DropdownMenuItem
                    key={value}
                    className="justify-center cursor-pointer"
                    onClick={() => pagination.onLimitChange(Number(value))}
                  >
                    {value} rows
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>
      <Pagination className="w-auto justify-end mx-0">
        <PaginationContent className="select-none">
          <PaginationItem>
            <PaginationLink
              href="#"
              size="sm"
              className="rounded"
              aria-label="Go to first page"
              aria-disabled={!pagination.hasPrevPage || loading}
              tabIndex={!pagination.hasPrevPage || loading ? -1 : 0}
              onClick={(event) =>
                handlePageChange(event, 1, !pagination.hasPrevPage || loading)
              }
              title="First page"
            >
              <Icon name="left-dubble-arrow" size="14px" />
            </PaginationLink>
          </PaginationItem>

          <PaginationItem>
            <PaginationLink
              href="#"
              size="sm"
              className="rounded"
              aria-label="Go to previous page"
              aria-disabled={!pagination.hasPrevPage || loading}
              tabIndex={!pagination.hasPrevPage || loading ? -1 : 0}
              onClick={(event) =>
                handlePageChange(
                  event,
                  pagination.currentPage - 1,
                  !pagination.hasPrevPage || loading
                )
              }
              title="Previous page"
            >
              <Icon name="arrow-left" size="14px" />
            </PaginationLink>
          </PaginationItem>

          {generatePageNumbers(
            pagination.currentPage,
            pagination.totalPages
          ).map((page, idx) =>
            page === "..." ? (
              <PaginationItem key={`ellipsis-${idx + 1}`}>
                <PaginationEllipsis className="text-muted-foreground" />
              </PaginationItem>
            ) : (
              <PaginationItem key={page}>
                <PaginationLink
                  href="#"
                  size="sm"
                  isActive={page === pagination.currentPage}
                  className={
                    page === pagination.currentPage
                      ? "font-semibold rounded"
                      : "border-transparent"
                  }
                  aria-disabled={loading}
                  tabIndex={loading ? -1 : 0}
                  onClick={(event) => handlePageChange(event, page, loading)}
                >
                  {page}
                </PaginationLink>
              </PaginationItem>
            )
          )}

          <PaginationItem>
            <PaginationLink
              href="#"
              size="sm"
              className="rounded"
              aria-label="Go to next page"
              aria-disabled={!pagination.hasNextPage || loading}
              tabIndex={!pagination.hasNextPage || loading ? -1 : 0}
              onClick={(event) =>
                handlePageChange(
                  event,
                  pagination.currentPage + 1,
                  !pagination.hasNextPage || loading
                )
              }
              title="Next page"
            >
              <Icon name="arrow-right" size="14px" />
            </PaginationLink>
          </PaginationItem>

          <PaginationItem>
            <PaginationLink
              href="#"
              size="sm"
              className="rounded"
              aria-label="Go to last page"
              aria-disabled={!pagination.hasNextPage || loading}
              tabIndex={!pagination.hasNextPage || loading ? -1 : 0}
              onClick={(event) =>
                handlePageChange(
                  event,
                  pagination.totalPages,
                  !pagination.hasNextPage || loading
                )
              }
              title="Last page"
            >
              <Icon name="right-dubble-arrow" size="14px" />
            </PaginationLink>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  );
}
