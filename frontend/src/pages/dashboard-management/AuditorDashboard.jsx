/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import CardWrapper from "./components/CardWrapper";
import ProgressBar from "./components/ProgressBar";
import Icon from "@/components/custom/Icon";
import { useDateFilter } from "./hooks/useDateFilter";
import { useAuth } from "@/context/authContext/useAuth";
import { getRoleLabel } from "@/utils/commonUtils";
import { frameworkToSlug } from "@/utils/frameworkUtils";
import DateFilter from "./components/DateFilter";

// ─── Dynamic Frontend Configuration ──────────────────────────────────────────
const COLORS = [
  { tagColor: "#3b82f6", barColor: "bg-blue-500" },
  { tagColor: "#22c55e", barColor: "bg-green-500" },
  { tagColor: "#8b5cf6", barColor: "bg-violet-500" },
  { tagColor: "#ef4444", barColor: "bg-red-500" },
  { tagColor: "#f59e0b", barColor: "bg-amber-500" },
  { tagColor: "#06b6d4", barColor: "bg-cyan-500" },
  { tagColor: "#ec4899", barColor: "bg-pink-500" },
  { tagColor: "#14b8a6", barColor: "bg-teal-500" },
];

const getHashIndex = (str, max) => {
  if (!str) return 0;
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.codePointAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % max;
};

const DASHBOARD_CONFIG = {
  getFrameworkConfig: (name) => COLORS[getHashIndex(name, COLORS.length)],
};

// ─── Static Mock Data ────────────────────────────────────────────────────────

const MOCK = {
  overallProtection: { value: 84, trend: "+2% vs last month", up: true },
  criticalGaps: { value: 16, trend: "-2 since last month", up: false },
  controlPassing: { value: 711, total: 847, updatedAgo: "4 hours ago" },
  extraControls: { value: 43, label: "Above Standards" },

  frameworkHealth: [
    {
      name: "ISO-27001:2022",
      readiness: 91,
    },
    {
      name: "ISO-9001:2008",
      readiness: 89,
    },
    {
      name: "NIST-CSF:2021",
      readiness: 58,
    },
    {
      name: "CFR-Part-II:2023",
      readiness: 67,
    },
  ],

  activeGaps: [
    {
      framework: "ISO-27001:2022",
      ctrlId: "BC-12.4",
      description: "Cryptographic Key Establishment",
      instances: 5,
      failing: "9%",
      lastNcDate: "2024-02-28",
      trend: "down",
    },
    {
      framework: "ISO-9001:2008",
      ctrlId: "QM-4.2",
      description: "Document Control Procedures",
      instances: 6,
      failing: "14%",
      lastNcDate: "2024-02-18",
      trend: "down",
    },
    {
      framework: "ISO-27001:2022",
      ctrlId: "AC-2.1",
      description: "Access Control Policy",
      instances: 14,
      failing: "22%",
      lastNcDate: "2024-03-01",
      trend: "down",
    },
    {
      framework: "NIST-CSF:2021",
      ctrlId: "PR.AC-4",
      description: "Access Permissions Management",
      instances: 11,
      failing: "31%",
      lastNcDate: "2024-03-05",
      trend: "down",
    },
  ],

  deploymentPoints: [
    { name: "ISO-27001:2022", count: 234 },
    { name: "ISO-9001:2008", count: 189 },
    { name: "NIST-CSF:2021", count: 100 },
    { name: "CFR-Part-II:2023", count: 58 },
  ],

  aiInsights: [
    {
      text: "Update Access Control Policy (AC-2.1) to enforce least privilege and role-based access.",
      priority: "High",
    },
    {
      text: "Enable logging for all administrative activities (AU-2.1) across AWS IAM.",
      priority: "High",
    },
    {
      text: "Enforce multi-factor authentication for all users (IA-2.1).",
      priority: "Medium",
    },
    {
      text: "Review and update configuration settings (CM-6.3) to align with baseline standards.",
      priority: "Medium",
    },
    {
      text: "Implement key rotation policy for cryptographic keys (SC-12.4) at defined intervals.",
      priority: "Low",
    },
  ],

  liveAuditStreams: [
    {
      status: "Pass",
      label: "Password Complexity Check • AWS IAM",
      ago: "3s ago",
    },
    {
      status: "Pass",
      label: "Password Complexity Check • AWS IAM",
      ago: "3s ago",
    },
    {
      status: "Pass",
      label: "Password Complexity Check • AWS IAM",
      ago: "3s ago",
    },
    {
      status: "Pass",
      label: "Password Complexity Check • AWS IAM",
      ago: "3s ago",
    },
    {
      status: "Warn",
      label: "Password Complexity Check • AWS IAM",
      ago: "3s ago",
    },
    {
      status: "Pass",
      label: "Password Complexity Check • AWS IAM",
      ago: "3s ago",
    },
  ],
};

// ─── Small reusable pieces ───────────────────────────────────────────────────

function getStreamDotColor(status) {
  if (status === "Pass") return "bg-emerald-500";
  if (status === "Warn") return "bg-amber-500";
  return "bg-red-500";
}

function getStreamTextColor(status) {
  if (status === "Pass") return "text-emerald-500";
  if (status === "Warn") return "text-amber-500";
  return "text-red-500";
}

function TopStatCard({
  icon,
  iconColor = "text-primary",
  iconBg = "bg-primary/10",
  borderColor = "border-primary/40",
  title,
  navigation,
  children,
}) {
  return (
    <Link
      to={navigation}
      className="rounded border border-border bg-linear-to-br from-background to-card p-2.5 flex justify-between shadow-lg hover:shadow-xl transition-shadow duration-300 hover:border-primary/50 cursor-pointer"
    >
      <div className="flex flex-col gap-2 w-full">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </p>
        <div className="">{children}</div>
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
    </Link>
  );
}

function PriorityBadge({ priority }) {
  const map = {
    High: "bg-red-100   text-red-700   dark:bg-red-900/30   dark:text-red-400",
    Medium:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    Low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${map[priority] ?? "bg-muted text-muted-foreground"}`}
    >
      {priority}
    </span>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function AuditorDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [currentTime, setCurrentTime] = useState(new Date());
  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-3 mt-2">
      {/* ── Header bar ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2 px-1">
        <h2 className="text-lg font-semibold text-foreground">
          Welcome, {user?.name}
          <span className="text-sm font-normal text-muted-foreground ml-1">
            ({user?.role && getRoleLabel(user.role)})
          </span>
          {" 👋"}
        </h2>
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <p className="text-[10px] font-medium text-foreground">
              {currentTime.toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </p>
            <p className="text-xs text-muted-foreground font-mono">
              {currentTime.toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: true,
              })}
            </p>
          </div>
          <DateFilter
            value={datePreset}
            startDate={startDate}
            endDate={endDate}
            onChange={handleDateChange}
          />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {/* Overall Protection */}
        <TopStatCard
          title="Overall Protection"
          icon="shield"
          iconColor="text-primary"
          navigation="/dashboard/overall-protection"
        >
          <p className="text-4xl font-bold text-foreground group-hover:opacity-80 transition-opacity">
            {MOCK.overallProtection.value}%
          </p>
          <p
            className={`text-xs flex items-center gap-1 ${MOCK.overallProtection.up ? "text-emerald-500" : "text-red-500"}`}
          >
            <Icon
              name={MOCK.overallProtection.up ? "arrow-up" : "arrow-down"}
              size="14px"
            />
            {MOCK.overallProtection.trend}
          </p>
        </TopStatCard>

        {/* Critical Gaps */}
        <TopStatCard
          title="Critical Gaps"
          icon="warning"
          iconColor="text-amber-500"
          iconBg="bg-amber-500/10"
          borderColor="border-amber-500/40"
          navigation="/dashboard/critical-gaps"
        >
          <p className="text-4xl font-bold text-foreground group-hover:opacity-80 transition-opacity">
            {MOCK.criticalGaps.value}
          </p>
          <p className="text-xs flex items-center gap-1 text-red-500">
            <Icon name="arrow-down" size="14px" />
            {MOCK.criticalGaps.trend}
          </p>
        </TopStatCard>

        {/* Control Passing */}
        <TopStatCard
          title="Control Passing"
          icon="check-circle"
          iconColor="text-emerald-500"
          iconBg="bg-emerald-500/10"
          borderColor="border-emerald-500/40"
          navigation="/dashboard/controls-passing"
        >
          <p className="text-4xl font-bold text-foreground group-hover:opacity-80 transition-opacity">
            <span className="text-primary">{MOCK.controlPassing.value}</span>
            <span className="text-xl text-muted-foreground">
              /{MOCK.controlPassing.total}
            </span>
          </p>
          <p className="text-xs text-muted-foreground">
            Updated {MOCK.controlPassing.updatedAgo}
          </p>
        </TopStatCard>

        {/* Extra Controls */}
        <TopStatCard
          title="Extra Controls"
          icon="star"
          iconColor="text-amber-400"
          iconBg="bg-amber-400/10"
          borderColor="border-amber-400/40"
          navigation="/dashboard/extra-controls"
        >
          <p className="text-4xl font-bold text-foreground group-hover:opacity-80 transition-opacity">
            {MOCK.extraControls.value}
          </p>
          <p className="text-xs text-muted-foreground">
            {MOCK.extraControls.label}
          </p>
        </TopStatCard>
      </div>

      {/* ── Row 2: Framework Health | Active Gaps | Live Audit ────────────── */}
      <div className="grid xl:grid-cols-3 gap-3 items-stretch">
        {/* Framework Health */}
        <CardWrapper title="Framework Health" className="flex flex-col">
          {/* Column headers */}
          <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b border-border pb-1.5 mb-2 shrink-0">
            <span>Framework</span>
            <span>Pass/Warn-Readiness</span>
          </div>

          <div
            className="overflow-y-auto space-y-2.5 flex-1 pr-0.5"
            style={{ maxHeight: "220px" }}
          >
            {MOCK.frameworkHealth.map((fw) => (
              <button
                key={fw.name}
                type="button"
                onClick={() =>
                  navigate(`/dashboard/framework/${frameworkToSlug(fw.name)}`)
                }
                className="flex items-center gap-3 w-full group cursor-pointer"
              >
                {/* Colored pill tag */}
                <span
                  className="text-[11px] font-semibold px-1 py-0.3 rounded text-white shrink-0 min-w-24 text-center group-hover:opacity-80 transition-opacity"
                  style={{
                    backgroundColor: DASHBOARD_CONFIG.getFrameworkConfig(
                      fw.name
                    ).tagColor,
                  }}
                >
                  {fw.name}
                </span>
                {/* Progress bar */}
                <div className="flex-1">
                  <ProgressBar
                    value={fw.readiness}
                    color={
                      DASHBOARD_CONFIG.getFrameworkConfig(fw.name).barColor
                    }
                  />
                </div>
                {/* Percentage */}
                <span className="text-xs font-bold text-foreground w-9 text-right shrink-0 group-hover:text-primary transition-colors">
                  {fw.readiness}%
                </span>
              </button>
            ))}
          </div>
        </CardWrapper>

        {/* Deployment Points */}
        <CardWrapper
          title="Deployment Points"
          right={
            <button
              type="button"
              onClick={() => navigate("/dashboard/deployment-points")}
              className="text-primary flex items-center gap-1 text-xs hover:underline cursor-pointer"
            >
              View All <Icon name="arrow-right" size="14px" />
            </button>
          }
          className="flex flex-col"
        >
          <div
            className="overflow-y-auto flex-1 space-y-4 pr-0.5"
            style={{ maxHeight: "220px" }}
          >
            {MOCK.deploymentPoints.map((dp) => (
              <div
                key={dp.name}
                className="flex items-center gap-3 w-full group"
              >
                {/* Colored pill tag */}
                <span
                  className="text-[11px] font-semibold px-1 py-0.3 rounded text-white shrink-0 min-w-24 text-center group-hover:opacity-80 transition-opacity"
                  style={{
                    backgroundColor: DASHBOARD_CONFIG.getFrameworkConfig(
                      dp.name
                    ).tagColor,
                  }}
                >
                  {dp.name}
                </span>
                {/* Progress bar */}
                <div className="flex-1">
                  <ProgressBar
                    value={Math.min((dp.count / 250) * 100, 100)}
                    color={
                      DASHBOARD_CONFIG.getFrameworkConfig(dp.name).barColor
                    }
                  />
                </div>
                {/* Count */}
                <span className="text-xs font-bold text-foreground w-9 text-right shrink-0 group-hover:text-primary transition-colors">
                  {dp.count}
                </span>
              </div>
            ))}
          </div>
        </CardWrapper>

        {/* Active Gaps */}
        <CardWrapper
          title="Active Gaps"
          right={
            <button
              type="button"
              onClick={() => navigate("/deployment-frameworks")}
              className="text-primary flex items-center gap-1 text-xs hover:underline cursor-pointer"
            >
              View All <Icon name="arrow-right" size="14px" />
            </button>
          }
          className="flex flex-col"
        >
          {/* Table header */}
          <div className="grid grid-cols-[0.3fr_1.2fr_0.8fr_0.5fr_0.7fr_1fr] text-[10px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1.5 gap-1">
            <span>SL.</span>
            <span>Framework</span>
            <span>Ctrl No.</span>
            <span className="text-center">Inst.</span>
            <span className="text-center">% Failing</span>
            <span className="text-right">Last NC Date</span>
          </div>
          <div className="flex-1 mt-1">
            {MOCK.activeGaps.map((gap, idx) => (
              <div
                key={gap.ctrlId}
                className="grid grid-cols-[0.3fr_1.2fr_0.8fr_0.5fr_0.7fr_1fr] gap-1 items-center py-2 border-b border-border last:border-0 hover:bg-accent/50 rounded transition-colors px-0.5"
              >
                <span className="text-xs text-muted-foreground">{idx + 1}</span>
                <span className="text-xs font-semibold text-primary truncate">
                  {gap.framework}
                </span>
                <span className="text-xs text-secondary font-semibold">
                  {gap.ctrlId}
                </span>
                <span className="text-xs text-center text-foreground font-medium">
                  {gap.instances}
                </span>
                <div className="flex items-center justify-center gap-1">
                  <Icon
                    name={gap.trend === "up" ? "arrow-up" : "arrow-down"}
                    size="12px"
                    className={
                      gap.trend === "up" ? "text-emerald-500" : "text-red-500"
                    }
                  />
                  <span
                    className={`text-xs font-bold ${gap.trend === "up" ? "text-emerald-500" : "text-red-500"}`}
                  >
                    {gap.failing}
                  </span>
                </div>
                <span className="text-xs text-right text-muted-foreground">
                  {gap.lastNcDate}
                </span>
              </div>
            ))}
          </div>
        </CardWrapper>

        {/* Live Audit Streams */}
        <CardWrapper
          title="Live Audit Streams"
          right={
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>24x7 Active</span>
            </span>
          }
          className="flex flex-col xl:col-span-2"
        >
          <div
            className="overflow-y-auto flex-1 pr-0.5"
            style={{ maxHeight: "220px" }}
          >
            {MOCK.liveAuditStreams.map((stream, index) => (
              <div
                key={`${stream.status}-${stream.label}-${stream.ago}-${index}`}
                className="flex items-center gap-3 py-2.5 border-b border-border last:border-0"
              >
                <span
                  className={`w-2.5 h-2.5 rounded-full shrink-0 ${getStreamDotColor(stream.status)}`}
                />
                <span
                  className={`text-[13px] font-semibold shrink-0 w-9 ${getStreamTextColor(stream.status)}`}
                >
                  {stream.status}
                </span>
                <span className="text-[13px] text-foreground flex-1 truncate">
                  {stream.label}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {stream.ago}
                </span>
              </div>
            ))}
          </div>
        </CardWrapper>

        {/* AI Insights */}
        <CardWrapper
          title="AI Insights"
          right={
            <p className="text-xs text-muted-foreground">
              Recommended actions to bridge critical gaps
            </p>
          }
          className="flex flex-col"
        >
          <div
            className="overflow-y-auto flex-1 pr-0.5"
            style={{ maxHeight: "220px" }}
          >
            {MOCK.aiInsights.map((insight) => (
              <div
                key={insight.text.slice(0, 30)}
                className="flex items-start gap-3 py-1.5 border-b border-border last:border-0"
              >
                <p className="text-xs text-foreground flex-1 leading-relaxed">
                  {insight.text}
                </p>
                <div className="flex items-center gap-2 shrink-0 mt-0.5">
                  <PriorityBadge priority={insight.priority} />
                  <button
                    type="button"
                    title="View Control"
                    className="text-xs text-primary font-medium flex items-center gap-0.5 group hover:gap-1.5 transition-all duration-200 whitespace-nowrap"
                  >
                    →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </CardWrapper>
      </div>
    </div>
  );
}
