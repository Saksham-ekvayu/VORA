/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";

// ─── Static mock data ─────────────────────────────────────────────────────────

const STATS = {
  total: 16,
  description:
    "Active control failures exceeding risk tolerance thresholds. Each gap requires remediation evidence before the next audit cycle.",
  priorities: [
    {
      label: "4 High Priority",
      color: "bg-red-500/20 text-red-400 border border-red-500/30",
    },
    {
      label: "8 Medium Priority",
      color: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    },
    {
      label: "4 Low Priority",
      color: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    },
  ],
};

const ALL_GAPS = [
  {
    id: "1",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    ctrlNo: "BC-12.4",
    controlName: "Business Continuity Planning",
    instances: 5,
    failingPct: "9%",
    severity: "Medium",
    daysOpen: 24,
    owner: "IT Ops",
  },
  {
    id: "2",
    framework: "ISO 9001",
    frameworkSlug: "iso-9001",
    ctrlNo: "QM-4.2",
    controlName: "Quality Management Objectives",
    instances: 6,
    failingPct: "14%",
    severity: "Medium",
    daysOpen: 18,
    owner: "QA Team",
  },
  {
    id: "3",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    ctrlNo: "AC-2.1",
    controlName: "Access Control — Least Privilege",
    instances: 14,
    failingPct: "22%",
    severity: "High",
    daysOpen: 41,
    owner: "IAM Team",
  },
  {
    id: "4",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    ctrlNo: "PR.AC-4",
    controlName: "Access Permissions Management",
    instances: 11,
    failingPct: "31%",
    severity: "High",
    daysOpen: 52,
    owner: "SecOps",
  },
  {
    id: "5",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    ctrlNo: "AU-2.1",
    controlName: "Audit Logging — Administrative",
    instances: 9,
    failingPct: "19%",
    severity: "High",
    daysOpen: 30,
    owner: "CloudOps",
  },
  {
    id: "6",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    ctrlNo: "SC-12.4",
    controlName: "Cryptographic Key Rotation",
    instances: 3,
    failingPct: "7%",
    severity: "Medium",
    daysOpen: 15,
    owner: "Crypto Team",
  },
  {
    id: "7",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    ctrlNo: "IA-2.1",
    controlName: "Multi-Factor Authentication",
    instances: 22,
    failingPct: "18%",
    severity: "High",
    daysOpen: 37,
    owner: "IAM Team",
  },
  {
    id: "8",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    ctrlNo: "DE.CM-1",
    controlName: "Network Monitoring",
    instances: 8,
    failingPct: "24%",
    severity: "Medium",
    daysOpen: 29,
    owner: "NetOps",
  },
  {
    id: "9",
    framework: "ISO 9001",
    frameworkSlug: "iso-9001",
    ctrlNo: "QM-10.2",
    controlName: "Nonconformity and Corrective Action",
    instances: 5,
    failingPct: "11%",
    severity: "Low",
    daysOpen: 12,
    owner: "QA Team",
  },
  {
    id: "10",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    ctrlNo: "ID.AM-2",
    controlName: "Software Inventory",
    instances: 6,
    failingPct: "18%",
    severity: "Medium",
    daysOpen: 22,
    owner: "IT Ops",
  },
  {
    id: "11",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    ctrlNo: "CM-6.3",
    controlName: "Configuration Baseline",
    instances: 7,
    failingPct: "8%",
    severity: "Low",
    daysOpen: 9,
    owner: "Infra Team",
  },
  {
    id: "12",
    framework: "ISO 9001",
    frameworkSlug: "iso-9001",
    ctrlNo: "QM-8.1",
    controlName: "Operational Planning",
    instances: 4,
    failingPct: "9%",
    severity: "Low",
    daysOpen: 7,
    owner: "Ops Team",
  },
];

// Unique frameworks for dropdown
const FRAMEWORK_NAMES = Array.from(new Set(ALL_GAPS.map((g) => g.framework)));

const FRAMEWORK_COLORS = {
  "ISO 27001": "text-blue-400",
  "ISO 9001": "text-green-400",
  "NIST CSF": "text-violet-400",
  "21 CFR Part II": "text-red-400",
};

const PAGE_SIZE = 10;

// ─── Helper Functions ─────────────────────────────────────────────────────────

const getColorByDaysOpen = (value) => {
  if (value >= 40) {
    return "text-red-400";
  }
  if (value >= 20) {
    return "text-amber-400";
  }
  return "text-foreground";
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CriticalGapsPage() {
  usePageTitle("critical-gaps", "Critical Gaps");

  const navigate = useNavigate();

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [frameworkFilter, setFrameworkFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  const handleFrameworkFilter = useCallback((val) => {
    setFrameworkFilter(val);
    setCurrentPage(1);
  }, []);

  const handleSeverityFilter = useCallback((val) => {
    setSeverityFilter(val);
    setCurrentPage(1);
  }, []);

  const handleSearch = useCallback((term) => {
    setSearchTerm(term);
    setCurrentPage(1);
  }, []);

  // Apply all filters
  const filteredData = useMemo(() => {
    let list = ALL_GAPS;

    if (frameworkFilter) {
      list = list.filter((g) => g.framework === frameworkFilter);
    }

    if (severityFilter) {
      list = list.filter((g) => g.severity === severityFilter);
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(
        (g) =>
          g.ctrlNo.toLowerCase().includes(q) ||
          g.controlName.toLowerCase().includes(q) ||
          g.framework.toLowerCase().includes(q) ||
          g.owner.toLowerCase().includes(q)
      );
    }

    return list;
  }, [searchTerm, frameworkFilter, severityFilter]);

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
      key: "ctrlNo",
      label: "Ctrl No.",
      sortable: false,
      render: (value) => (
        <span className="font-mono text-xs font-bold text-secondary bg-muted px-2 py-1 rounded whitespace-nowrap">
          {value}
        </span>
      ),
    },
    {
      key: "controlName",
      label: "Control Name",
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
          onClick={() => navigate(`/dashboard/framework/${row.frameworkSlug}`)}
          className={`text-xs font-semibold hover:underline text-left whitespace-nowrap ${FRAMEWORK_COLORS[value] ?? "text-primary"}`}
        >
          {value}
        </button>
      ),
    },
    {
      key: "instances",
      label: "Inst.",
      sortable: false,
      render: (value) => (
        <span className="text-sm font-medium text-foreground text-center block">
          {value}
        </span>
      ),
    },
    {
      key: "failingPct",
      label: "% Failing",
      sortable: false,
      render: (value) => (
        <span className="text-sm font-bold text-red-400">{value}</span>
      ),
    },
    {
      key: "severity",
      label: "Severity",
      sortable: false,
      render: (value) => <CustomBadge severity={value} size="sm" />,
    },
    {
      key: "daysOpen",
      label: "Days Open",
      sortable: false,
      render: (value) => (
        <span className={`text-sm font-semibold ${getColorByDaysOpen(value)}`}>
          {value}
        </span>
      ),
    },
    {
      key: "owner",
      label: "Owner",
      sortable: false,
      render: (value) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {value}
        </span>
      ),
    },
  ];

  // ── Header actions ──────────────────────────────────────────────────────────
  const getHeaderActions = () => [
    {
      type: "dropdown",
      label: frameworkFilter || "All Frameworks",
      triggerClassName: "w-fit min-w-36",
      options: [
        { label: "All Frameworks", onClick: () => handleFrameworkFilter("") },
        ...FRAMEWORK_NAMES.map((fw, i) => ({
          label: fw,
          separatorBefore: i === 0,
          onClick: () => handleFrameworkFilter(fw),
        })),
      ],
    },
    {
      type: "dropdown",
      label: severityFilter || "All Severities",
      triggerClassName: "w-fit min-w-32",
      options: [
        { label: "All Severities", onClick: () => handleSeverityFilter("") },
        {
          label: "High",
          separatorBefore: true,
          onClick: () => handleSeverityFilter("High"),
        },
        { label: "Medium", onClick: () => handleSeverityFilter("Medium") },
        { label: "Low", onClick: () => handleSeverityFilter("Low") },
      ],
    },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* Page header */}
      <div className="flex items-center justify-between px-1">
        <h2 className="text-lg font-semibold text-foreground">Critical Gaps</h2>
        <button
          onClick={() => navigate("/dashboard")}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-primary border border-border bg-accent hover:border-primary rounded px-3 py-1.5 transition-colors"
        >
          <Icon name="arrow-left" size="13px" /> Back to Dashboard
        </button>
      </div>

      {/* Hero summary banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3">
        <p className="text-2xl font-extrabold text-foreground leading-tight">
          <span className="text-red-400">{STATS.total}</span>{" "}
          <span className="text-base font-semibold">
            Critical Non-Conformances
          </span>
        </p>
        <p className="text-xs text-muted-foreground mt-1 max-w-xl">
          {STATS.description}
        </p>
        {/* Priority pills */}
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          {STATS.priorities.map((p) => (
            <span
              key={p.label}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold ${p.color}`}
            >
              {p.label}
            </span>
          ))}
        </div>
      </div>

      {/* DataTable — All Active Gaps */}
      <DataTable
        entityName="Gaps"
        columns={columns}
        data={pagedData}
        loading={false}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        onClearSearch={() => handleSearch("")}
        pagination={pagination}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search gaps..."
        emptyMessage={
          searchTerm || frameworkFilter || severityFilter
            ? "No gaps match your filters"
            : "No critical gaps found"
        }
      />
    </div>
  );
}
