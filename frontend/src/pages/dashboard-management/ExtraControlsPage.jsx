/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";

// ─── Static mock data ─────────────────────────────────────────────────────────

const STATS = {
  total: 43,
  description:
    "Your organization implements 43 additional security controls beyond mandatory framework minimums. These enhance your security posture and demonstrate proactive compliance maturity.",
};

const ALL_EXTRA_CONTROLS = [
  {
    id: "EX-001",
    ctrlId: "EX-001",
    control: "Zero-Trust Network Segmentation",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Network",
    basis: "Internal Policy",
    benefit: "Reduces lateral movement blast radius by 94%",
    status: "Active",
  },
  {
    id: "EX-002",
    ctrlId: "EX-002",
    control: "UEBA — Behavioral Anomaly Detection",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Threat Detection",
    basis: "Above NIST",
    benefit: "Detected 3 insider threats in last 90 days",
    status: "Active",
  },
  {
    id: "EX-003",
    ctrlId: "EX-003",
    control: "Immutable Backup Validation",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Resilience",
    basis: "Above ISO 27001",
    benefit: "RTO improved to <2h; ransomware-resilient",
    status: "Active",
  },
  {
    id: "EX-004",
    ctrlId: "EX-004",
    control: "Continuous Penetration Testing",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Vulnerability Mgmt",
    basis: "Internal Policy",
    benefit: "Monthly automated pen-test cadence",
    status: "Review Due",
  },
  {
    id: "EX-005",
    ctrlId: "EX-005",
    control: "Supply Chain Risk Scoring",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Vendor Risk",
    basis: "Above ISO 27001",
    benefit: "Scores 238 active vendors continuously",
    status: "Active",
  },
  {
    id: "EX-006",
    ctrlId: "EX-006",
    control: "AI-Assisted Log Correlation",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Monitoring",
    basis: "Internal Policy",
    benefit: "Reduces MTTD from 72h to 4h",
    status: "Active",
  },
  {
    id: "EX-007",
    ctrlId: "EX-007",
    control: "Hardware Security Key Enforcement",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Identity & Access",
    basis: "Above ISO 27001",
    benefit: "Eliminates phishing-based account takeover",
    status: "Active",
  },
  {
    id: "EX-008",
    ctrlId: "EX-008",
    control: "Data Residency Tagging",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Data Governance",
    basis: "Above NIST",
    benefit: "100% data classified with residency metadata",
    status: "Active",
  },
  {
    id: "EX-009",
    ctrlId: "EX-009",
    control: "Threat Intelligence Feed Integration",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Threat Detection",
    basis: "Internal Policy",
    benefit: "Ingests 14 live threat feeds daily",
    status: "Active",
  },
  {
    id: "EX-010",
    ctrlId: "EX-010",
    control: "Secure Code Review Automation",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Application Security",
    basis: "Above ISO 27001",
    benefit: "Catches 91% of OWASP Top-10 issues pre-release",
    status: "Review Due",
  },
  {
    id: "EX-011",
    ctrlId: "EX-011",
    control: "Privileged Access Workstation Policy",
    framework: "ISO 27001",
    frameworkSlug: "iso-27001",
    section: "Identity & Access",
    basis: "Internal Policy",
    benefit: "Isolates admin actions from general user traffic",
    status: "Active",
  },
  {
    id: "EX-012",
    ctrlId: "EX-012",
    control: "Cryptographic Agility Framework",
    framework: "NIST CSF",
    frameworkSlug: "nist-csf",
    section: "Cryptography",
    basis: "Above NIST",
    benefit: "Ready for post-quantum migration",
    status: "Active",
  },
];

// Unique framework names for the dropdown
const FRAMEWORK_NAMES = Array.from(
  new Set(ALL_EXTRA_CONTROLS.map((c) => c.framework))
);

const FRAMEWORK_COLORS = {
  "ISO 27001": "text-blue-400",
  "ISO 9001": "text-green-400",
  "NIST CSF": "text-violet-400",
  "21 CFR Part II": "text-red-400",
};

const PAGE_SIZE = 10;

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExtraControlsPage() {
  usePageTitle("extra-controls", "Extra Controls");

  const navigate = useNavigate();

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [frameworkFilter, setFrameworkFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  const handleFrameworkFilter = useCallback((val) => {
    setFrameworkFilter(val);
    setCurrentPage(1);
  }, []);

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
    let list = ALL_EXTRA_CONTROLS;

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
          c.name.toLowerCase().includes(q) ||
          c.framework.toLowerCase().includes(q) ||
          c.section.toLowerCase().includes(q)
        // c.basis.toLowerCase().includes(q)
      );
    }

    return list;
  }, [searchTerm, frameworkFilter, statusFilter]);

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
      label: "control",
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
      label: "section",
      sortable: false,
      render: (value) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
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
      label: statusFilter || "All Status",
      triggerClassName: "w-fit min-w-28",
      options: [
        { label: "All Status", onClick: () => handleStatusFilter("") },
        {
          label: "Active",
          separatorBefore: true,
          onClick: () => handleStatusFilter("Active"),
        },
        {
          label: "Review Due",
          onClick: () => handleStatusFilter("Review Due"),
        },
        {
          label: "Deprecated",
          onClick: () => handleStatusFilter("Deprecated"),
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
          Extra Controls
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
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3">
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
        headerActions={getHeaderActions()}
        searchPlaceholder="Search extra controls..."
        emptyMessage={
          searchTerm || frameworkFilter || statusFilter
            ? "No controls match your filters"
            : "No extra controls found"
        }
      />
    </div>
  );
}
