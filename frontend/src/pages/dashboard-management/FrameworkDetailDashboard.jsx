/* eslint-disable react/prop-types */
import { useParams, useNavigate } from "react-router-dom";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import CardWrapper from "./components/CardWrapper";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import ProgressBar from "../../components/custom/ProgressBar";
// ─── Per-framework mock data ──────────────────────────────────────────────────

const data = {
  id: 1,
  frameworkName: "Information Security Management System",
  frameworkVersion: "ISO-27001:2022",
  controls: {
    subscribed: 95, // All applicable controls in assigned framework
    compliant: 82, // Controls with status Compliant
    nonCompliant: 7, // Controls with status Non-Compliant
    notAssessed: 6, // Controls with status Not Assessed
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
    gapAnalysis: [
      { label: "Access Ctrl", value: 7 },
      { label: "Incident Res", value: 6 },
      { label: "Data Privacy", value: 5 },
      { label: "Risk Assess", value: 4 },
      { label: "Physical Sec", value: 4 },
      { label: "Physical Sec", value: 4 },
      { label: "Physical Sec", value: 4 },
      { label: "Physical Sec", value: 4 },
      { label: "Physical Sec", value: 7 },
      { label: "Physical Sec", value: 9 },
      { label: "Physical Sec", value: 3 },
      { label: "Physical Sec", value: 6 },
      { label: "Physical Sec", value: 1 },
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
};

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
              <Cell
                key={`${index}-${entry.name}`}
                fill={CHART_COLORS[index % CHART_COLORS.length]}
              />
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

function StatCard({
  title,
  subtitle,
  value,
  icon,
  borderColor = "border-primary/40",
  iconColor = "text-primary",
  iconBg = "bg-primary/10",
}) {
  return (
    <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex justify-between gap-1.5 shadow-lg">
      <div className="flex flex-col justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground leading-tight">
            {title}
          </p>
        </div>
        <div className="flex items-end gap-2">
          <p className="text-3xl font-bold text-foreground leading-none">
            {value}
          </p>

          {subtitle && (
            <p className="text-[11px] text-muted-foreground">{subtitle}</p>
          )}
        </div>
      </div>
      <span
        className={cn(
          "w-12 h-12 rounded shrink-0 flex items-center justify-center transition-transform duration-300 group-hover:scale-105 border",
          borderColor,
          iconBg,
          iconColor
        )}
      >
        <Icon name={icon} size="24px" />
      </span>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function FrameworkDetailDashboard() {
  const { id } = useParams();
  const navigate = useNavigate();

  const paramKey = id;

  // Set dynamic breadcrumb label to actual framework name (e.g. "ISO 27001")
  usePageTitle(paramKey, "Framework Details");

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
  } = data;

  return (
    <div className="space-y-3 my-2">
      {/* ── Premium Header ──── */}
      <div className="rounded border border-border/50 bg-card overflow-hidden shadow-sm relative">
        {/* Subtle Gradient Background */}
        <div className="absolute inset-0 bg-linear-to-r from-primary/10 via-primary/5 to-transparent pointer-events-none" />

        <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
          {/* Left - Icon, Name & Version */}
          <div className="flex-1 min-w-0 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-primary/15 flex items-center justify-center border border-primary/20 shrink-0 shadow-inner">
              <Icon name="framework" size="20px" className="text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight text-foreground flex items-center gap-2">
                {data.frameworkName}
              </h1>
              <p className="text-xs text-muted-foreground font-medium mt-0.5 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                Active Version:{" "}
                <span className="text-primary font-semibold">
                  {data.frameworkVersion}
                </span>
              </p>
            </div>
          </div>

          {/* Right - Back button */}
          <div className="shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate("/dashboard")}
            >
              <Icon name="arrow-left" size="14px" className="mr-1.5" /> Back to
              Dashboard
            </Button>
          </div>
        </div>
      </div>

      {/* ── Row 1: 4 stat cards ───────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Controls"
          subtitle="Subscribed by Company"
          value={controls.subscribed}
          icon="framework"
          borderColor="border-primary/40"
          iconColor="text-primary"
          iconBg="bg-primary/10"
        />
        <StatCard
          title="Compliant Controls"
          value={controls.compliant}
          icon="check-circle"
          borderColor="border-emerald-500/40"
          iconColor="text-emerald-500"
          iconBg="bg-emerald-500/10"
        />
        <StatCard
          title="Non-Compliant Controls"
          value={controls.nonCompliant}
          icon="warning"
          borderColor="border-red-500/40"
          iconColor="text-red-500"
          iconBg="bg-red-500/10"
        />
        <StatCard
          title="Not Assessed Controls"
          value={controls.notAssessed}
          icon="star"
          borderColor="border-amber-400/40"
          iconColor="text-amber-400"
          iconBg="bg-amber-400/10"
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
          <div className="flex justify-center flex-wrap gap-x-4 gap-y-2 mt-4 max-h-20 overflow-y-auto custom-scrollbar">
            {coverage.breakdown.map((item, index) => (
              <div
                key={item.name}
                className="flex items-center gap-1.5 shrink-0"
              >
                <span
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{
                    backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                  }}
                />
                <span className="text-xs text-muted-foreground whitespace-nowrap">
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
          <div className="flex justify-center flex-wrap gap-x-4 gap-y-2 mt-4 max-h-20 overflow-y-auto custom-scrollbar">
            {compliance.breakdown.map((item, index) => (
              <div
                key={item.name}
                className="flex items-center gap-1.5 shrink-0"
              >
                <span
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{
                    backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                  }}
                />
                <span className="text-xs text-muted-foreground whitespace-nowrap">
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
              Audit Dashboard
            </div>
          }
          className="flex flex-col"
        >
          {/* Gap Analysis bars */}
          <div className="flex flex-col gap-3 max-h-60 overflow-y-auto custom-scrollbar pr-1">
            {auditDashboard.gapAnalysis.map((gap, index) => {
              const gapColor = CHART_COLORS[index % CHART_COLORS.length];
              return (
                <div key={gap.label} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-24 truncate shrink-0">
                    {gap.label}
                  </span>
                  <div className="flex-1">
                    <ProgressBar
                      value={Math.min(Math.abs(gap.value) * 10, 100)}
                      height="2"
                      color={gapColor}
                    />
                  </div>
                  <span
                    className="text-[11px] font-bold w-6 text-right shrink-0"
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
            className="overflow-y-auto flex-1 pr-1 custom-scrollbar"
            style={{ maxHeight: "220px" }}
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
            className="overflow-y-auto flex-1 pr-1 custom-scrollbar"
            style={{ maxHeight: "220px" }}
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
    </div>
  );
}
