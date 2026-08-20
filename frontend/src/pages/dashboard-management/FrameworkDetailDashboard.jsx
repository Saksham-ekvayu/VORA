/* eslint-disable react/prop-types */
import { useParams, useNavigate } from "react-router-dom";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import CardWrapper from "./components/CardWrapper";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
// ─── Per-framework mock data ──────────────────────────────────────────────────

const FRAMEWORK_DATA = [
  {
    name: "ISO-27001:2022",
    version: "ISO 27001:2022",
    controls: {
      subscribed: 95,
      compliant: 82,
      compliantPct: "84%",
      nonCompliant: 7,
      nonCompliantPct: "7%",
      notAssessed: 6,
      notAssessedPct: "6%",
    },
    coverage: {
      total: 103,
      breakdown: [
        { name: "Pak Controls", value: 48 },
        { name: "Org. Specific", value: 22 },
      ],
    },
    compliance: {
      total: 95,
      breakdown: [
        { name: "Compliant", value: 82 },
        { name: "Non-Compliant", value: 7 },
        { name: "Not Assessed", value: 6 },
      ],
    },
    auditDashboard: {
      externalCertification: { status: "Yes", date: "Nov 15, 2023" },
      internalAudit: { status: "Partial", date: "Feb 20, 2024" },
      gapAnalysis: [
        { label: "Access Ctrl", value: -7 },
        { label: "Incident Res", value: -6 },
        { label: "Data Privacy", value: -5 },
        { label: "Risk Assess", value: -4 },
        { label: "Physical Sec", value: -4 },
      ],
    },
    nonCompliantControls: [
      {
        sl: 1,
        ctrlNo: "BC-12.4",
        description: "Cryptographic Key Establishment",
        instances: 9,
        failing: "9%",
        lastNcDate: "2024-02-28",
      },
      {
        sl: 2,
        ctrlNo: "AU-9.2",
        description: "Content of Audit Records",
        instances: 3,
        failing: "5%",
        lastNcDate: "2024-02-10",
      },
      {
        sl: 3,
        ctrlNo: "AC-2.1",
        description: "Access Control Policy",
        instances: 14,
        failing: "23%",
        lastNcDate: "2024-03-01",
      },
      {
        sl: 4,
        ctrlNo: "CM-6.3",
        description: "Configuration Settings",
        instances: 5,
        failing: "18%",
        lastNcDate: "2024-02-28",
      },
      {
        sl: 5,
        ctrlNo: "IA-5.1",
        description: "Authenticator Management",
        instances: 7,
        failing: "12%",
        lastNcDate: "2024-02-20",
      },
    ],
    notAssessed: [
      {
        sl: 1,
        ctrlNo: "MP-6.1",
        description: "Media Sanitization",
        reason: "Manual review scheduled",
      },
      {
        sl: 2,
        ctrlNo: "AT-2.2",
        description: "Security Awareness Training",
        reason: "Training platform update",
      },
      {
        sl: 3,
        ctrlNo: "SA-6.3",
        description: "Vulnerability Scanning",
        reason: "Scanner offline",
      },
      {
        sl: 4,
        ctrlNo: "PE-5.4",
        description: "Fire Protection",
        reason: "Awaiting evidence upload",
      },
      {
        sl: 5,
        ctrlNo: "SI-7.8",
        description: "Software and Information Integrity",
        reason: "Out of scope this quarter",
      },
    ],
    subscriptions: [
      {
        framework: "ISO 27001 BMS Base",
        version: "2022",
        startDate: "Jan 10, 2024",
        duration: "24 mo",
        users: 348,
        location: "EU-Rest",
      },
      {
        framework: "ISO 27001 Cloud",
        version: "2013",
        startDate: "Feb 01, 2024",
        duration: "12 mo",
        users: 198,
        location: "EU-Rest",
      },
    ],
  },
  {
    name: "ISO-9001:2008",
    version: "ISO 9001:2015",
    controls: {
      subscribed: 78,
      compliant: 67,
      compliantPct: "89%",
      nonCompliant: 5,
      nonCompliantPct: "6%",
      notAssessed: 4,
      notAssessedPct: "5%",
    },
    coverage: {
      total: 78,
      breakdown: [
        { name: "Pak Controls", value: 40 },
        { name: "Org. Specific", value: 16 },
      ],
    },
    compliance: {
      total: 78,
      breakdown: [
        { name: "Compliant", value: 67 },
        { name: "Non-Compliant", value: 5 },
        { name: "Not Assessed", value: 4 },
      ],
    },
    auditDashboard: {
      externalCertification: { status: "Yes", date: "Oct 05, 2023" },
      internalAudit: { status: "Yes", date: "Jan 12, 2024" },
      gapAnalysis: [
        { label: "Doc Control", value: -5 },
        { label: "Process Mon", value: -4 },
        { label: "Customer Foc", value: -3 },
        { label: "Mgmt Review", value: -2 },
      ],
    },
    nonCompliantControls: [
      {
        sl: 1,
        ctrlNo: "QM-4.2",
        description: "Document Control Procedures",
        instances: 6,
        failing: "14%",
        lastNcDate: "2024-02-18",
      },
      {
        sl: 2,
        ctrlNo: "QM-8.1",
        description: "Operational Planning",
        instances: 4,
        failing: "9%",
        lastNcDate: "2024-02-15",
      },
      {
        sl: 3,
        ctrlNo: "QM-9.1",
        description: "Monitoring and Measurement",
        instances: 3,
        failing: "7%",
        lastNcDate: "2024-03-01",
      },
      {
        sl: 4,
        ctrlNo: "QM-6.2",
        description: "Quality Objectives",
        instances: 2,
        failing: "5%",
        lastNcDate: "2024-02-20",
      },
      {
        sl: 5,
        ctrlNo: "QM-10.2",
        description: "Nonconformity and Corrective Action",
        instances: 5,
        failing: "11%",
        lastNcDate: "2024-02-28",
      },
    ],
    notAssessed: [
      {
        sl: 1,
        ctrlNo: "QM-7.4",
        description: "Communication",
        reason: "Policy review pending",
      },
      {
        sl: 2,
        ctrlNo: "QM-5.3",
        description: "Roles and Responsibilities",
        reason: "Org chart update",
      },
      {
        sl: 3,
        ctrlNo: "QM-8.4",
        description: "External Providers",
        reason: "Vendor audit scheduled",
      },
      {
        sl: 4,
        ctrlNo: "QM-4.1",
        description: "Context of Organization",
        reason: "Strategy review ongoing",
      },
    ],
    subscriptions: [
      {
        framework: "ISO 9001 QMS Base",
        version: "2015",
        startDate: "Mar 01, 2024",
        duration: "24 mo",
        users: 210,
        location: "EU-Rest",
      },
    ],
  },
  {
    name: "NIST-CSF:2021",
    version: "NIST CSF v1.1",
    controls: {
      subscribed: 108,
      compliant: 63,
      compliantPct: "58%",
      nonCompliant: 22,
      nonCompliantPct: "20%",
      notAssessed: 14,
      notAssessedPct: "13%",
    },
    coverage: {
      total: 108,
      breakdown: [
        { name: "Pak Controls", value: 50 },
        { name: "Org. Specific", value: 20 },
      ],
    },
    compliance: {
      total: 108,
      breakdown: [
        { name: "Compliant", value: 63 },
        { name: "Non-Compliant", value: 22 },
        { name: "Not Assessed", value: 14 },
      ],
    },
    auditDashboard: {
      externalCertification: { status: "No", date: "—" },
      internalAudit: { status: "Partial", date: "Mar 10, 2024" },
      gapAnalysis: [
        { label: "Identify", value: -9 },
        { label: "Protect", value: -7 },
        { label: "Detect", value: -5 },
        { label: "Respond", value: -4 },
        { label: "Recover", value: -3 },
      ],
    },
    nonCompliantControls: [
      {
        sl: 1,
        ctrlNo: "PR.AC-4",
        description: "Access Permissions Management",
        instances: 11,
        failing: "31%",
        lastNcDate: "2024-03-05",
      },
      {
        sl: 2,
        ctrlNo: "DE.CM-1",
        description: "Network Monitoring",
        instances: 8,
        failing: "24%",
        lastNcDate: "2024-02-28",
      },
      {
        sl: 3,
        ctrlNo: "ID.AM-2",
        description: "Software Inventory",
        instances: 6,
        failing: "18%",
        lastNcDate: "2024-03-01",
      },
      {
        sl: 4,
        ctrlNo: "RS.CO-2",
        description: "Incident Reporting",
        instances: 4,
        failing: "12%",
        lastNcDate: "2024-02-25",
      },
      {
        sl: 5,
        ctrlNo: "PR.DS-1",
        description: "Data at Rest Protection",
        instances: 9,
        failing: "27%",
        lastNcDate: "2024-03-02",
      },
    ],
    notAssessed: [
      {
        sl: 1,
        ctrlNo: "RC.RP-1",
        description: "Recovery Planning",
        reason: "Plan under development",
      },
      {
        sl: 2,
        ctrlNo: "ID.GV-3",
        description: "Legal Requirements",
        reason: "Legal review pending",
      },
      {
        sl: 3,
        ctrlNo: "PR.IP-9",
        description: "Response Plans",
        reason: "Template not finalized",
      },
    ],
    subscriptions: [
      {
        framework: "NIST CSF Core",
        version: "1.1",
        startDate: "Jan 15, 2024",
        duration: "12 mo",
        users: 156,
        location: "US-East",
      },
    ],
  },
  {
    name: "CFR-Part-II:2023",
    version: "21 CFR Part 11:2023",
    controls: {
      subscribed: 54,
      compliant: 36,
      compliantPct: "67%",
      nonCompliant: 10,
      nonCompliantPct: "19%",
      notAssessed: 8,
      notAssessedPct: "15%",
    },
    coverage: {
      total: 54,
      breakdown: [
        { name: "Pak Controls", value: 28 },
        { name: "Org. Specific", value: 10 },
      ],
    },
    compliance: {
      total: 54,
      breakdown: [
        { name: "Compliant", value: 36 },
        { name: "Non-Compliant", value: 10 },
        { name: "Not Assessed", value: 8 },
      ],
    },
    auditDashboard: {
      externalCertification: { status: "Partial", date: "Dec 01, 2023" },
      internalAudit: { status: "No", date: "—" },
      gapAnalysis: [
        { label: "Electronic Rec", value: -6 },
        { label: "Audit Trail", value: -5 },
        { label: "Signatures", value: -4 },
        { label: "Access Ctrl", value: -3 },
      ],
    },
    nonCompliantControls: [
      {
        sl: 1,
        ctrlNo: "11.10a",
        description: "Validation of Systems",
        instances: 5,
        failing: "19%",
        lastNcDate: "2024-02-28",
      },
      {
        sl: 2,
        ctrlNo: "11.10e",
        description: "Audit Trail Controls",
        instances: 7,
        failing: "26%",
        lastNcDate: "2024-03-01",
      },
      {
        sl: 3,
        ctrlNo: "11.300",
        description: "Electronic Signatures",
        instances: 4,
        failing: "15%",
        lastNcDate: "2024-02-20",
      },
    ],
    notAssessed: [
      {
        sl: 1,
        ctrlNo: "11.50",
        description: "Signature Manifestations",
        reason: "Legal review pending",
      },
      {
        sl: 2,
        ctrlNo: "11.70",
        description: "Signature/Record Linking",
        reason: "Technical assessment due",
      },
    ],
    subscriptions: [
      {
        framework: "21 CFR Part 11 Base",
        version: "2023",
        startDate: "Feb 01, 2024",
        duration: "12 mo",
        users: 89,
        location: "US-East",
      },
    ],
  },
];

// ─── Donut chart with center label ───────────────────────────────────────────
function getCertStatusColor(status) {
  if (status === "Yes") return "bg-emerald-500";
  if (status === "Partial") return "bg-amber-500";
  return "bg-red-500";
}

const CHART_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#f97316", // orange
];

function DonutChart({ data, total, label }) {
  return (
    <div className="relative w-full h-40">
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-2xl font-bold text-foreground">{total}</span>
        {label && (
          <span className="text-[10px] text-muted-foreground">{label}</span>
        )}
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={48}
            outerRadius={68}
            paddingAngle={2}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--card)",
              borderColor: "var(--border)",
              fontSize: "11px",
              borderRadius: "6px",
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Top stat card ────────────────────────────────────────────────────────────

function StatCard({ title, subtitle, value, pct, icon, iconColor }) {
  return (
    <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col gap-1.5 shadow-lg">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground leading-tight">
            {title}
          </p>
          {subtitle && (
            <p className="text-[10px] text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <span className={iconColor}>
          <Icon name={icon} size="18px" />
        </span>
      </div>
      <div className="flex items-end gap-2">
        <p className="text-3xl font-bold text-foreground leading-none">
          {value}
        </p>
        {pct && (
          <span className="text-xs font-semibold text-emerald-500 mb-0.5">
            {pct}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function FrameworkDetailDashboard() {
  const { id, frameworkId } = useParams();
  const navigate = useNavigate();

  const paramKey = id || frameworkId;
  const data = FRAMEWORK_DATA[paramKey] || Object.values(FRAMEWORK_DATA)[0];

  // Set dynamic breadcrumb label to actual framework name (e.g. "ISO 27001")
  usePageTitle(paramKey, data?.name);

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-100">
        <div className="text-center">
          <Icon
            name="warning"
            size="48px"
            className="text-muted-foreground mb-3"
          />
          <p className="text-muted-foreground">Framework not found</p>
          <button
            type="button"
            onClick={() => navigate("/dashboard")}
            className="mt-3 text-sm text-primary hover:underline"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const {
    controls,
    coverage,
    compliance,
    auditDashboard,
    nonCompliantControls,
    notAssessed,
    subscriptions,
  } = data;

  return (
    <div className="space-y-3 my-2">
      {/* ── Header: Framework name + version (left) | Back (right) ──── */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left - Framework name & version */}
        <div className="flex-1 min-w-0 flex items-center gap-3">
          <span className="text-sm font-bold">{data.name}</span>
          <span className="text-xs text-muted-foreground font-medium">
            version: {data.version}
          </span>
        </div>
        {/* Right - Back button */}
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

      {/* ── Row 1: 4 stat cards ───────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Controls"
          subtitle="Subscribed by Company"
          value={controls.subscribed}
          icon="framework"
          iconColor="text-primary"
        />
        <StatCard
          title="Compliant Controls"
          value={controls.compliant}
          pct={controls.compliantPct}
          icon="check-circle"
          iconColor="text-emerald-500"
        />
        <StatCard
          title="Non-Compliant Controls"
          value={controls.nonCompliant}
          pct={controls.nonCompliantPct}
          icon="warning"
          iconColor="text-red-500"
        />
        <StatCard
          title="Not Assessed Controls"
          value={controls.notAssessed}
          pct={controls.notAssessedPct}
          icon="star"
          iconColor="text-amber-400"
        />
      </div>

      {/* ── Row 2: Framework Coverage | Compliance Status | Audit Dashboard ── */}
      <div className="grid xl:grid-cols-3 gap-3 items-stretch">
        {/* Framework Coverage */}
        <CardWrapper title="Framework Coverage" className="flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <p className="text-xs text-muted-foreground flex-1">
              Current framework status
            </p>
            <span className="text-sm font-bold text-foreground">
              {coverage.total}
            </span>
            <span className="text-[10px] text-muted-foreground">
              Total Controls
            </span>
          </div>
          <DonutChart data={coverage.breakdown} total={coverage.total} />
          <div className="flex justify-center gap-4 mt-4">
            {coverage.breakdown.map((item, index) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                />
                <span className="text-xs text-muted-foreground">
                  {item.name}
                </span>
              </div>
            ))}
          </div>
        </CardWrapper>

        {/* Compliance Status */}
        <CardWrapper title="Compliance Status" className="flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <p className="text-xs text-muted-foreground flex-1">
              Current framework status
            </p>
            <span className="text-sm font-bold text-foreground">
              {compliance.total}
            </span>
            <span className="text-[10px] text-muted-foreground">
              Total Controls
            </span>
          </div>
          <DonutChart data={compliance.breakdown} total={compliance.total} />
          <div className="flex justify-center gap-4 mt-4">
            {compliance.breakdown.map((item, index) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                />
                <span className="text-xs text-muted-foreground">
                  {item.name}
                </span>
              </div>
            ))}
          </div>
        </CardWrapper>

        {/* Audit Dashboard */}
        <CardWrapper
          title={
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-primary/20 flex items-center justify-center shrink-0">
                <Icon name="shield" size="14px" className="text-primary" />
              </div>
              Audit Dashboard (External + Internal)
            </div>
          }
          className="flex flex-col"
        >
          {/* Certification row */}
          <div className="grid grid-cols-2 gap-3 mb-3 pb-3 border-b border-border">
            <div>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                External Certification
              </p>
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${getCertStatusColor(auditDashboard.externalCertification.status)}`}
                />
                <span className="text-xs font-semibold text-foreground">
                  {auditDashboard.externalCertification.status}
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {auditDashboard.externalCertification.date}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                Internal Audit
              </p>
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${getCertStatusColor(auditDashboard.internalAudit.status)}`}
                />
                <span className="text-xs font-semibold text-foreground">
                  {auditDashboard.internalAudit.status}
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {auditDashboard.internalAudit.date}
              </p>
            </div>
          </div>

          {/* Gap Analysis bars */}
          <div className="flex flex-col gap-3">
            {auditDashboard.gapAnalysis.map((gap, index) => {
              const gapColor = CHART_COLORS[index % CHART_COLORS.length];
              return (
                <div key={gap.label} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-20 truncate shrink-0">
                    {gap.label}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden flex justify-end">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(Math.abs(gap.value) * 10, 100)}%`,
                        backgroundColor: gapColor,
                      }}
                    />
                  </div>
                  <span
                    className="text-[11px] font-bold w-5 text-right shrink-0"
                    style={{ color: gapColor }}
                  >
                    {gap.value}
                  </span>
                </div>
              );
            })}
          </div>
        </CardWrapper>
      </div>

      {/* ── Row 3: Non-Compliant Controls | Not Assessed ─────────────── */}
      <div className="grid xl:grid-cols-2 gap-3 items-stretch">
        {/* Non-Compliant Controls */}
        <CardWrapper
          title={
            <span className="flex items-center gap-2">
              Non-Compliant Controls{" "}
              <span className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center text-[11px] font-bold text-white">
                {nonCompliantControls.length}
              </span>
            </span>
          }
          right={
            <button
              type="button"
              onClick={() => navigate("/deployment-frameworks")}
              className="text-primary text-xs hover:underline flex items-center gap-1 cursor-pointer"
            >
              View All <Icon name="arrow-right" size="12px" />
            </button>
          }
          className="flex flex-col"
        >
          <div className="grid grid-cols-[0.25fr_0.7fr_1.6fr_0.4fr_0.6fr_0.85fr] text-[10px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1.5 gap-1 shrink-0">
            <span>SL.</span>
            <span>Ctrl No.</span>
            <span>Description</span>
            <span className="text-center">Inst.</span>
            <span className="text-center">% Failing</span>
            <span className="text-right">Last NC Date</span>
          </div>
          <div
            className="overflow-y-auto flex-1 pr-0.5"
            style={{ maxHeight: "200px" }}
          >
            {nonCompliantControls.map((ctrl) => (
              <div
                key={ctrl.sl}
                className="grid grid-cols-[0.25fr_0.7fr_1.6fr_0.4fr_0.6fr_0.85fr] gap-1 items-center py-2 border-b border-border last:border-0 hover:bg-accent/50 rounded transition-colors px-0.5"
              >
                <span className="text-xs text-muted-foreground">{ctrl.sl}</span>
                <span className="text-xs text-secondary font-semibold">
                  {ctrl.ctrlNo}
                </span>
                <span className="text-xs text-foreground leading-tight">
                  {ctrl.description}
                </span>
                <span className="text-xs text-center font-medium">
                  {ctrl.instances}
                </span>
                <div className="flex items-center justify-center gap-1">
                  <Icon
                    name="trending-down"
                    size="11px"
                    className="text-red-500"
                  />
                  <span className="text-xs font-bold text-red-500">
                    {ctrl.failing}
                  </span>
                </div>
                <span className="text-xs text-right text-muted-foreground">
                  {ctrl.lastNcDate}
                </span>
              </div>
            ))}
          </div>
        </CardWrapper>

        {/* Not Assessed */}
        <CardWrapper
          title={
            <span className="flex items-center gap-2">
              Not Assessed{" "}
              <span className="w-5 h-5 rounded-full bg-amber-500 flex items-center justify-center text-[11px] font-bold text-white">
                {notAssessed.length}
              </span>
            </span>
          }
          right={
            <button
              type="button"
              className="text-primary text-xs hover:underline flex items-center gap-1 cursor-pointer"
            >
              View All <Icon name="arrow-right" size="12px" />
            </button>
          }
          className="flex flex-col"
        >
          <div className="grid grid-cols-[0.25fr_0.7fr_1.8fr_1.5fr] text-[10px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1.5 gap-1 shrink-0">
            <span>SL.</span>
            <span>Ctrl</span>
            <span>Description</span>
            <span>Reason</span>
          </div>
          <div
            className="overflow-y-auto flex-1 pr-0.5"
            style={{ maxHeight: "200px" }}
          >
            {notAssessed.map((ctrl) => (
              <div
                key={ctrl.sl}
                className="grid grid-cols-[0.25fr_0.7fr_1.8fr_1.5fr] gap-1 items-center py-2 border-b border-border last:border-0 hover:bg-accent/50 rounded transition-colors px-0.5"
              >
                <span className="text-xs text-muted-foreground">{ctrl.sl}</span>
                <span className="text-xs text-secondary font-semibold">
                  {ctrl.ctrlNo}
                </span>
                <span className="text-xs text-foreground leading-tight">
                  {ctrl.description}
                </span>
                <span className="text-xs text-muted-foreground leading-tight">
                  {ctrl.reason}
                </span>
              </div>
            ))}
          </div>
        </CardWrapper>
      </div>

      {/* ── Row 4: Active Subscription Details ───────────────────────── */}
      <CardWrapper
        title="Active Subscription Details"
        right={
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-500">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            {subscriptions.length} active · auto-renew on
          </span>
        }
      >
        <div className="grid grid-cols-[2fr_0.6fr_0.9fr_0.6fr_0.5fr_0.8fr] text-[10px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1.5 gap-2 shrink-0">
          <span>Framework</span>
          <span>Version</span>
          <span>Start Date</span>
          <span>Duration</span>
          <span className="text-center">Users</span>
          <span>Location</span>
        </div>
        <div className="space-y-0">
          {subscriptions.map((sub) => (
            <div
              key={sub.framework}
              className="grid grid-cols-[2fr_0.6fr_0.9fr_0.6fr_0.5fr_0.8fr] gap-2 items-center py-2 border-b border-border last:border-0 hover:bg-accent/50 rounded transition-colors px-0.5"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                <span className="text-xs text-foreground font-medium truncate">
                  {sub.framework}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {sub.version}
              </span>
              <span className="text-xs text-primary font-medium">
                {sub.startDate}
              </span>
              <span className="text-xs text-foreground">{sub.duration}</span>
              <span className="text-xs text-center font-semibold text-foreground">
                {sub.users}
              </span>
              <span className="text-xs text-primary font-medium">
                {sub.location}
              </span>
            </div>
          ))}
        </div>
      </CardWrapper>
    </div>
  );
}
