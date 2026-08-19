/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

// ─── Static mock data ─────────────────────────────────────────────────────────

const STATS = {
  total: 43,
  description: `Your organization implements additional controls beyond mandatory framework minimums. These enhance your security posture and demonstrate proactive compliance maturity.`,
};

const ALL_EXTRA_CONTROLS = [
  {
    id: "EX-001",
    ctrlId: "EX-001",
    control: "Zero-Trust Network Segmentation",
    frameworkVersion: "ISO-27001:2022",
    frameworkName: "Information Security Management System (ISMS)",
    deploymentPoints: 5,
    createdAt: "2026-08-18T13:31:15.672868+00:00",
  },
  {
    id: "EX-002",
    ctrlId: "EX-002",
    control: "UEBA — Behavioral Anomaly Detection",
    frameworkVersion: "NIST-CSF:2025",
    frameworkName: "Cybersecurity Framework (CSF)",
    deploymentPoints: 5,
    createdAt: "2026-08-18T13:31:15.672868+00:00",
  },
  {
    id: "EX-003",
    ctrlId: "EX-003",
    control: "Immutable Backup Validation",
    frameworkVersion: "ISO-27001:2022",
    frameworkName: "Information Security Management System (ISMS)",
    deploymentPoints: 5,
    createdAt: "2026-08-18T13:31:15.672868+00:00",
  },
];

const PAGE_SIZE = 10;

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExtraControls() {
  usePageTitle("extra-controls", "Extra Controls");

  const navigate = useNavigate();

  // Filters
  const [searchTerm, setSearchTerm] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  const handleSearch = useCallback((term) => {
    setSearchTerm(term);
    setCurrentPage(1);
  }, []);

  // Apply all filters
  const filteredData = useMemo(() => {
    let list = ALL_EXTRA_CONTROLS;

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(
        (c) =>
          c.ctrlId.toLowerCase().includes(q) ||
          c.name.toLowerCase().includes(q) ||
          c.framework.toLowerCase().includes(q) ||
          c.section.toLowerCase().includes(q)
        // c.basis.toLowerCase().includes(q)
      );
    }

    return list;
  }, [searchTerm]);

  // Client-side pagination
  const totalItems = filteredData.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const pagedData = filteredData.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE
  );

  const pagination = {
    currentPage: safePage,
    totalPages,
    totalItems,
    limit: PAGE_SIZE,
    hasPrevPage: safePage > 1,
    hasNextPage: safePage < totalPages,
    onPageChange: setCurrentPage,
  };

  // ── Column definitions ──────────────────────────────────────────────────────
  const columns = [
    {
      key: "frameworkVersion",
      label: "Version",
      sortable: false,
      render: (value, row) => (
        <Link
          to={`/dashboard/framework/${row.id}`}
          className="hover:underline hover:text-primary"
        >
          {value}
        </Link>
      ),
    },
    {
      key: "frameworkName",
      label: "Framework",
      sortable: false,
      render: (value, row) => (
        <Link
          to={`/dashboard/framework/${row.id}`}
          className="hover:underline hover:text-primary"
        >
          {value}
        </Link>
      ),
    },
    {
      key: "ctrlId",
      label: "Ctrl ID",
      sortable: false,
      render: (value) => (
        <span className="font-mono text-xs font-bold text-secondary bg-muted px-2 py-1 rounded whitespace-nowrap">
          {value}
        </span>
      ),
    },
    {
      key: "control",
      label: "control",
      sortable: false,
      render: (value) => <span className="">{value}</span>,
    },
    {
      key: "deploymentPoints",
      label: "Points",
      sortable: false,
      render: (value) => <span className="">{value}</span>,
    },
    {
      key: "createdAt",
      label: "Created At",
      sortable: false,
      render: (value) => (
        <span className="whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* Hero summary banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-amber-400">{STATS.total}</span>{" "}
            <span className="text-base font-semibold">
              Controls Above Standard Requirements
            </span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            {STATS.description}
          </p>
        </div>

        {/* Right — Button */}
        <div className="shrink-0">
          <Button
            size="xs"
            variant="outline"
            onClick={() => navigate("/dashboard")}
          >
            <Icon name="arrow-left" size="13px" /> Back to Dashboard
          </Button>
        </div>
      </div>

      {/* DataTable — Extra Controls Register */}
      <DataTable
        entityName="Controls"
        columns={columns}
        data={pagedData}
        loading={false}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        onClearSearch={() => handleSearch("")}
        pagination={pagination}
        searchPlaceholder="Search extra controls..."
        emptyMessage={
          searchTerm
            ? "No controls match your filters"
            : "No extra controls found"
        }
      />
    </div>
  );
}
