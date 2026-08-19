/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";

// ─── Static mock data ─────────────────────────────────────────────────────────

const STATS = {
  passing: 711,
  failing: 98,
  warning: 38,
  notEvaluated: 0,
  total: 847,
  passRate: 84,
  failingOrEvidence: 136,
  updatedAgo: "4 hours ago",
};

const ALL_CONTROLS = [
  {
    id: "AC-2.1",
    ctrlId: "AC-2.1",
    control: "Least Privilege Enforcement",
    frameworkVersion: "ISO-27001:2022",
    frameworkName: "Information Security Management System (ISMS)",
    section: "Access Control",
    instances: 14,
    passRate: 78,
    status: "Failing",
    lastRun: "4h ago",
  },
  {
    id: "AU-2.1",
    ctrlId: "AU-2.1",
    control: "Admin Activity Logging",
    frameworkVersion: "ISO-27001:2022",
    frameworkName: "Information Security Management System (ISMS)",
    section: "Audit & Accountability",
    instances: 9,
    passRate: 81,
    status: "Failing",
    lastRun: "4h ago",
  },
  {
    id: "IA-2.1",
    ctrlId: "IA-2.1",
    control: "Multi-Factor Authentication",
    frameworkVersion: "ISO-27001:2022",
    frameworkName: "Information Security Management System (ISMS)",
    section: "Identification & Auth",
    instances: 22,
    passRate: 88,
    status: "Warning",
    lastRun: "4h ago",
  },
];

// Items per page (client-side)
const PAGE_SIZE = 10;

// ─── Stat Box ─────────────────────────────────────────────────────────────────

function StatBox({ label, value, valueColor }) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-2 rounded border border-border bg-accent min-w-22.5">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
        {label}
      </p>
      <p className={`text-2xl font-bold leading-none ${valueColor}`}>{value}</p>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ControlsPassing() {
  usePageTitle("controls-passing", "Controls Passing");

  const navigate = useNavigate();

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState(""); // "" = All

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 whenever a filter changes
  const handleStatusFilter = useCallback((val) => {
    setStatusFilter(val);
    setCurrentPage(1);
  }, []);

  const handleSearch = useCallback((term) => {
    setSearchTerm(term);
    setCurrentPage(1);
  }, []);

  // Apply all filters
  const filteredData = useMemo(() => {
    let list = ALL_CONTROLS;

    if (statusFilter) {
      list = list.filter((c) => c.status === statusFilter);
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(
        (c) =>
          c.ctrlId.toLowerCase().includes(q) ||
          c.control.toLowerCase().includes(q) ||
          c.framework.toLowerCase().includes(q) ||
          c.section.toLowerCase().includes(q)
      );
    }

    return list;
  }, [searchTerm, statusFilter]);

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
        <button
          type="button"
          onClick={() => navigate(`/dashboard/framework/${row.id}`)}
          className="text-xs font-semibold hover:underline text-left whitespace-nowrap"
        >
          {value}
        </button>
      ),
    },
    {
      key: "frameworkName",
      label: "Framework Name",
      sortable: false,
      render: (value) => <span className="">{value}</span>,
    },
    {
      key: "section",
      label: "Section",
      sortable: false,
      render: (value) => <span className="">{value}</span>,
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
      label: "Control",
      sortable: false,
      render: (value) => <span className="">{value}</span>,
    },
    {
      key: "instances",
      label: "Instances",
      sortable: false,
      render: (value) => (
        <span className="text-sm font-medium text-foreground text-center block">
          {value}
        </span>
      ),
    },
    {
      key: "passRate",
      label: "Pass Rate",
      sortable: false,
      render: (value, row) => {
        let color = "text-emerald-500";
        if (row.status === "Failing") color = "text-red-500";
        else if (row.status === "Warning") color = "text-amber-500";
        return <span className={`text-sm font-bold ${color}`}>{value}%</span>;
      },
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      render: (value) => <CustomBadge status={value} size="sm" />,
    },
    {
      key: "lastRun",
      label: "Last Run",
      sortable: false,
      render: (value) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {value}
        </span>
      ),
    },
  ];

  // ── Header actions (status dropdown) ───────────────────
  const getHeaderActions = () => [
    {
      type: "dropdown",
      label: statusFilter || "All Status",
      triggerClassName: "w-fit min-w-28",
      options: [
        { label: "All Status", onClick: () => handleStatusFilter("") },
        {
          label: "Passing",
          separatorBefore: true,
          onClick: () => handleStatusFilter("Passing"),
        },
        { label: "Failing", onClick: () => handleStatusFilter("Failing") },
        { label: "Warning", onClick: () => handleStatusFilter("Warning") },
        {
          label: "Not Evaluated",
          onClick: () => handleStatusFilter("Not Evaluated"),
        },
      ],
    },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* Hero summary banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card shadow-lg p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-primary">{STATS.passing}</span>
            <span className="text-muted-foreground text-lg font-semibold">
              {" "}
              / {STATS.total}
            </span>{" "}
            <span className="text-base font-semibold">Controls Passing</span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            {STATS.passRate}% pass rate across all deployed controls.{" "}
            {STATS.failingOrEvidence} controls currently failing or requiring
            evidence. Updated {STATS.updatedAgo}.
          </p>
        </div>

        {/* Right — Button & 4 stat boxes */}
        <div className="flex flex-col items-end gap-3 shrink-0">
          <Button
            size="xs"
            variant="outline"
            onClick={() => navigate("/dashboard")}
          >
            <Icon name="arrow-left" size="13px" /> Back to Dashboard
          </Button>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <StatBox
              label="Passing"
              value={STATS.passing}
              valueColor="text-emerald-500"
            />
            <StatBox
              label="Failing"
              value={STATS.failing}
              valueColor="text-red-500"
            />
            <StatBox
              label="Warning"
              value={STATS.warning}
              valueColor="text-amber-500"
            />
            <StatBox
              label="Not Evaluated"
              value={STATS.notEvaluated}
              valueColor="text-muted-foreground"
            />
          </div>
        </div>
      </div>

      {/* DataTable — Control Registry */}
      <DataTable
        entityName="Controls"
        columns={columns}
        data={pagedData}
        loading={false}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        onClearSearch={() => handleSearch("")}
        pagination={pagination}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search controls..."
        emptyMessage={
          searchTerm || statusFilter
            ? "No controls match your filters"
            : "No controls found"
        }
      />
    </div>
  );
}
