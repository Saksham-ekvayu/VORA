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
  score: 84,
  trend: "+2% vs last month",
  trendUp: true,
  timePeriod: "Last 180 Days",
  description:
    "Composite score across all active frameworks, deployment points, and control categories. Weighted by criticality and asset exposure.",
  frameworksActive: 4,
  controlsEvaluated: 847,
  deploymentPoints: 581,
};

const FRAMEWORK_ROWS = [
  {
    id: "iso-27001",
    version: "ISO-27001:2022",
    framework: "Information Security Management System",
    frameworkSlug: "iso-27001",
    weight: "35%",
    rawScore: "91%",
    contribution: "31.85%",
    trend: "+3%",
    trendUp: true,
    status: "On Track",
  },
  {
    id: "iso-9001",
    version: "ISO-9001:2015",
    framework: "Quality Management System",
    frameworkSlug: "iso-9001",
    weight: "25%",
    rawScore: "89%",
    contribution: "22.25%",
    trend: "+1%",
    trendUp: true,
    status: "On Track",
  },
  {
    id: "nist-csf",
    version: "NIST-CSF:2023",
    framework: "Cybersecurity Framework",
    frameworkSlug: "nist-csf",
    weight: "25%",
    rawScore: "58%",
    contribution: "14.50%",
    trend: "-2%",
    trendUp: false,
    status: "Needs Attention",
  },
  {
    id: "21-cfr-part-ii",
    version: "CFR-Part-II:2025",
    framework: "21 CFR Part II",
    frameworkSlug: "21-cfr-part-ii",
    weight: "15%",
    rawScore: "67%",
    contribution: "10.05%",
    trend: "-1%",
    trendUp: false,
    status: "At Risk",
  },
];

const PAGE_SIZE = 10;

// ─── Stat Mini Box ────────────────────────────────────────────────────────────

function MiniStatBox({ label, value, valueColor }) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-2 rounded border border-border bg-accent min-w-27.5">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1 text-center">
        {label}
      </p>
      <p
        className={`text-2xl font-bold leading-none ${valueColor ?? "text-foreground"}`}
      >
        {value}
      </p>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function OverallProtection() {
  usePageTitle("overall-protection", "Overall Protection");

  const navigate = useNavigate();

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

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
    let list = FRAMEWORK_ROWS;

    if (statusFilter) {
      list = list.filter((r) => r.status === statusFilter);
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((r) => r.framework.toLowerCase().includes(q));
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
      key: "version",
      label: "Framework Version",
      sortable: false,
      render: (value, row) => (
        <button
          type="button"
          onClick={() => navigate(`/dashboard/framework/${row.frameworkSlug}`)}
          className="text-xs font-semibold hover:underline text-left whitespace-nowrap cursor-pointer"
        >
          {value}
        </button>
      ),
    },
    {
      key: "framework",
      label: "Framework Name",
      sortable: false,
      render: (value) => (
        <span className="text-sm font-medium text-foreground">{value}</span>
      ),
    },
    {
      key: "weight",
      label: "Weight",
      sortable: false,
      render: (value) => (
        <span className="text-sm font-medium text-foreground">{value}</span>
      ),
    },
    {
      key: "rawScore",
      label: "Raw Score",
      sortable: false,
      render: (value) => (
        <span className="text-sm font-bold text-foreground">{value}</span>
      ),
    },
    {
      key: "contribution",
      label: "Contribution",
      sortable: false,
      render: (value) => (
        <span className="text-sm font-bold text-emerald-400">{value}</span>
      ),
    },
    {
      key: "trend",
      label: "Trend",
      sortable: false,
      render: (value, row) => (
        <span
          className={`text-xs font-semibold flex items-center gap-1 ${row.trendUp ? "text-emerald-400" : "text-red-400"
            }`}
        >
          <Icon
            name={row.trendUp ? "trending-up" : "trending-down"}
            size="13px"
          />
          {value}
        </span>
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      render: (value) => <CustomBadge status={value} size="sm" />,
    },
  ];

  // ── Header actions ──────────────────────────────────────────────────────────
  const getHeaderActions = () => [
    {
      type: "dropdown",
      label: statusFilter || "All Status",
      triggerClassName: "w-fit min-w-36",
      options: [
        { label: "All Status", onClick: () => handleStatusFilter("") },
        {
          label: "On Track",
          separatorBefore: true,
          onClick: () => handleStatusFilter("On Track"),
        },
        {
          label: "Needs Attention",
          onClick: () => handleStatusFilter("Needs Attention"),
        },
        { label: "At Risk", onClick: () => handleStatusFilter("At Risk") },
      ],
    },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* ── Hero banner ───────────────────────────────────────────────────── */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        {/* Left — score + description + pills */}
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-primary">{STATS.score}%</span>{" "}
            <span className="text-base font-semibold">
              Overall Protection Score
            </span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            {STATS.description}
          </p>
          {/* Trend + period pills */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1 ${STATS.trendUp
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "bg-red-500/20 text-red-400 border border-red-500/30"
                }`}
            >
              <Icon
                name={STATS.trendUp ? "trending-up" : "trending-down"}
                size="11px"
              />
              {STATS.trend}
            </span>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-accent text-muted-foreground border border-border">
              {STATS.timePeriod}
            </span>
          </div>
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
            <MiniStatBox
              label="Frameworks Active"
              value={STATS.frameworksActive}
              valueColor="text-primary"
            />
            <MiniStatBox
              label="Controls Evaluated"
              value={STATS.controlsEvaluated}
              valueColor="text-foreground"
            />
            <MiniStatBox
              label="Deployment Points"
              value={STATS.deploymentPoints}
              valueColor="text-primary"
            />
          </div>
        </div>
      </div>

      {/* ── Framework Contribution table ───────────────────────────────────── */}
      <DataTable
        entityName="Frameworks"
        columns={columns}
        data={pagedData}
        loading={false}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        onClearSearch={() => handleSearch("")}
        pagination={pagination}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search framework..."
        emptyMessage={
          searchTerm || statusFilter
            ? "No frameworks match your filters"
            : "No framework data found"
        }
      />
    </div>
  );
}
