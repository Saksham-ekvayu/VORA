/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";

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
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
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
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
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
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Identification & Auth",
    instances: 22,
    passRate: 88,
    status: "Warning",
    lastRun: "4h ago",
  },
  {
    id: "CM-6.3",
    ctrlId: "CM-6.3",
    control: "Configuration Baseline",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Config Management",
    instances: 7,
    passRate: 96,
    status: "Passing",
    lastRun: "4h ago",
  },
  {
    id: "SC-12.4",
    ctrlId: "SC-12.4",
    control: "Cryptographic Key Rotation",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "System & Comms",
    instances: 3,
    passRate: 93,
    status: "Warning",
    lastRun: "4h ago",
  },
  {
    id: "BC-12.4",
    ctrlId: "BC-12.4",
    control: "Business Continuity Testing",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Business Continuity",
    instances: 5,
    passRate: 91,
    status: "Passing",
    lastRun: "4h ago",
  },
  {
    id: "PR.AC-4",
    ctrlId: "PR.AC-4",
    control: "Access Permissions Management",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Access Control",
    instances: 11,
    passRate: 69,
    status: "Failing",
    lastRun: "4h ago",
  },
  {
    id: "DE.CM-1",
    ctrlId: "DE.CM-1",
    control: "Network Monitoring",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Continuous Monitoring",
    instances: 8,
    passRate: 76,
    status: "Failing",
    lastRun: "4h ago",
  },
  {
    id: "QM-4.2",
    ctrlId: "QM-4.2",
    control: "Document Control Procedures",
    framework: "ISO 9001",
    frameworkSlug: "iso-9001",
    section: "Documentation",
    instances: 6,
    passRate: 86,
    status: "Warning",
    lastRun: "4h ago",
  },
  {
    id: "QM-9.1",
    ctrlId: "QM-9.1",
    control: "Monitoring and Measurement",
    framework: "ISO 9001",
    frameworkSlug: "iso-9001",
    section: "Performance Evaluation",
    instances: 4,
    passRate: 93,
    status: "Passing",
    lastRun: "4h ago",
  },
  {
    id: "11.10a",
    ctrlId: "11.10a",
    control: "Validation of Systems",
    framework: "21 CFR Part II",
    frameworkSlug: "21-cfr-part-ii",
    section: "System Validation",
    instances: 5,
    passRate: 81,
    status: "Failing",
    lastRun: "4h ago",
  },
  {
    id: "IA-5.1",
    ctrlId: "IA-5.1",
    control: "Authenticator Management",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Identification & Auth",
    instances: 7,
    passRate: 88,
    status: "Passing",
    lastRun: "4h ago",
  },
];

// Unique framework Control  for the dropdown
const FRAMEWORK_Control = Array.from(
  new Set(ALL_CONTROLS.map((c) => c.framework))
);

const FRAMEWORK_COLORS = {
  "ISO 27001": "text-blue-400",
  "ISO 9001": "text-green-400",
  "NIST CSF": "text-violet-400",
  "21 CFR Part II": "text-red-400",
};

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
  const [frameworkFilter, setFrameworkFilter] = useState(""); // "" = All

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 whenever a filter changes
  const handleStatusFilter = useCallback((val) => {
    setStatusFilter(val);
    setCurrentPage(1);
  }, []);

  const handleFrameworkFilter = useCallback((val) => {
    setFrameworkFilter(val);
    setCurrentPage(1);
  }, []);

  const handleSearch = useCallback((term) => {
    setSearchTerm(term);
    setCurrentPage(1);
  }, []);

  // Apply all filters
  const filteredData = useMemo(() => {
    let list = ALL_CONTROLS;

    if (frameworkFilter) {
      list = list.filter((c) => c.framework === frameworkFilter);
    }

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
  }, [searchTerm, statusFilter, frameworkFilter]);

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
      render: (value) => (
        <span className="text-sm font-medium text-foreground">{value}</span>
      ),
    },
    {
      key: "framework",
      label: "Framework",
      sortable: false,
      render: (value, row) => (
        <button
          type="button"
          onClick={() => navigate(`/dashboard/framework/${row.frameworkSlug}`)}
          className={`text-xs font-semibold hover:underline text-left whitespace-nowrap ${FRAMEWORK_COLORS[value] ?? "text-primary"}`}
        >
          {value}
        </button>
      ),
    },
    {
      key: "section",
      label: "Section",
      sortable: false,
      render: (value) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {value}
        </span>
      ),
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

  // ── Header actions (framework dropdown + status dropdown) ───────────────────
  const getHeaderActions = () => [
    {
      type: "dropdown",
      label: frameworkFilter || "All Frameworks",
      triggerClassName: "w-fit min-w-36",
      options: [
        { label: "All Frameworks", onClick: () => handleFrameworkFilter("") },
        ...FRAMEWORK_Control.map((fw, i) => ({
          label: fw,
          separatorBefore: i === 0,
          onClick: () => handleFrameworkFilter(fw),
        })),
      ],
    },
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
      {/* Page header */}
      <div className="flex items-center justify-between px-1">
        <h2 className="text-lg font-semibold text-foreground">
          Controls Passing
        </h2>
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-primary border border-border bg-accent hover:border-primary rounded px-3 py-1.5 transition-colors"
        >
          <Icon name="arrow-left" size="13px" /> Back to Dashboard
        </button>
      </div>

      {/* Hero summary banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card shadow-lg p-3 flex flex-col sm:flex-row sm:items-center gap-4">
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
        <div className="flex items-center gap-2 flex-wrap shrink-0">
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
          searchTerm || statusFilter || frameworkFilter
            ? "No controls match your filters"
            : "No controls found"
        }
      />
    </div>
  );
}
