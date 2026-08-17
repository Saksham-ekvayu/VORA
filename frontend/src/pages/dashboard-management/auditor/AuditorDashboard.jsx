/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import CardWrapper from "../components/CardWrapper";
import ProgressBar from "../components/ProgressBar";
import Icon from "@/components/custom/Icon";
import DateFilter from "../components/DateFilter";
import { useDateFilter } from "../hooks/useDateFilter";
import { useAuth } from "@/context/authContext/useAuth";
import { getRoleLabel } from "@/utils/commonUtils";
import { frameworkToSlug } from "@/utils/frameworkUtils";

// ─── Static Mock Data ────────────────────────────────────────────────────────

const MOCK = {
  overallProtection: { value: 84, trend: "+2% vs last month", up: true },
  criticalGaps: { value: 16, trend: "-2 since last month", up: false },
  controlPassing: { value: 711, total: 847, updatedAgo: "4 hours ago" },
  extraControls: { value: 43, label: "Above Standards" },

  frameworkHealth: [
    {
      name: "ISO 27001",
      readiness: 91,
      tagColor: "#3b82f6",
      barColor: "bg-blue-500",
    },
    {
      name: "ISO 9001",
      readiness: 89,
      tagColor: "#22c55e",
      barColor: "bg-green-500",
    },
    {
      name: "NIST CSF",
      readiness: 58,
      tagColor: "#8b5cf6",
      barColor: "bg-violet-500",
    },
    {
      name: "21 CFR Part II",
      readiness: 67,
      tagColor: "#ef4444",
      barColor: "bg-red-500",
    },
  ],

  activeGaps: [
    {
      framework: "ISO 27001",
      ctrlNo: "BC-12.4",
      description: "Cryptographic Key Establishment",
      instances: 5,
      failing: "9%",
      lastNcDate: "2024-02-28",
      trend: "down",
    },
    {
      framework: "ISO 9001",
      ctrlNo: "QM-4.2",
      description: "Document Control Procedures",
      instances: 6,
      failing: "14%",
      lastNcDate: "2024-02-18",
      trend: "down",
    },
    {
      framework: "ISO 27001",
      ctrlNo: "AC-2.1",
      description: "Access Control Policy",
      instances: 14,
      failing: "22%",
      lastNcDate: "2024-03-01",
      trend: "down",
    },
    {
      framework: "NIST CSF",
      ctrlNo: "PR.AC-4",
      description: "Access Permissions Management",
      instances: 11,
      failing: "31%",
      lastNcDate: "2024-03-05",
      trend: "down",
    },
  ],

  deploymentPoints: [
    { name: "AWS Infrastructure", count: 234, icon: "cloud" },
    { name: "IAM / Okta", count: 189, icon: "key" },
    { name: "Application Logs", count: 100, icon: "document" },
    { name: "HR / Admin", count: 58, icon: "users" },
  ],

  riskByStatus: [
    {
      label: "Accepted Risk",
      icon: "check-circle",
      high: 2,
      medium: 4,
      low: 7,
    },
    { label: "Reduced Risk", icon: "check-circle", high: 3, medium: 6, low: 5 },
    {
      label: "Transferred Risk",
      icon: "arrow-right",
      high: 1,
      medium: 2,
      low: 3,
    },
    { label: "Mitigated Risk", icon: "shield", high: 2, medium: 7, low: 9 },
    { label: "Un-Mitigated Risk", icon: "warning", high: 4, medium: 5, low: 2 },
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

  upcomingEvents: [
    {
      title: "ISO 27001 Internal Audit",
      date: "Jun 10, 2024",
      daysLeft: 10,
      status: "Overdue Risk",
      openItems: 8,
      statusColor: "bg-red-500",
    },
    {
      title: "Management Review Meeting",
      date: "Jul 28, 2024",
      daysLeft: 58,
      status: "Upcoming",
      actions: 5,
      statusColor: "bg-amber-500",
    },
    {
      title: "ISO 27001 Surveillance Audit",
      date: "Aug 25, 2024",
      daysLeft: 86,
      status: "Upcoming",
      tasks: 7,
      statusColor: "bg-amber-500",
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
    <div className="space-y-3 my-2">
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
              name={MOCK.overallProtection.up ? "trending-up" : "trending-down"}
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
            <Icon name="trending-down" size="14px" />
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
                  className="text-[11px] font-semibold px-2 py-1 rounded text-white shrink-0 min-w-22.5 text-center group-hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: fw.tagColor }}
                >
                  {fw.name}
                </span>
                {/* Progress bar */}
                <div className="flex-1">
                  <ProgressBar value={fw.readiness} color={fw.barColor} />
                </div>
                {/* Percentage */}
                <span className="text-xs font-bold text-foreground w-9 text-right shrink-0 group-hover:text-primary transition-colors">
                  {fw.readiness}%
                </span>
              </button>
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
                key={gap.ctrlNo}
                className="grid grid-cols-[0.3fr_1.2fr_0.8fr_0.5fr_0.7fr_1fr] gap-1 items-center py-2 border-b border-border last:border-0 hover:bg-accent/50 rounded transition-colors px-0.5"
              >
                <span className="text-xs text-muted-foreground">{idx + 1}</span>
                <span className="text-xs font-semibold text-primary truncate">
                  {gap.framework}
                </span>
                <span className="text-xs text-secondary font-semibold">
                  {gap.ctrlNo}
                </span>
                <span className="text-xs text-center text-foreground font-medium">
                  {gap.instances}
                </span>
                <div className="flex items-center justify-center gap-1">
                  <Icon
                    name={gap.trend === "up" ? "trending-up" : "trending-down"}
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
          className="flex flex-col"
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
      </div>

      {/* ── Row 3: Deployment Points | Risk by Status | AI Insights ─────── */}
      <div className="grid xl:grid-cols-3 gap-3 items-stretch">
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
              <div key={dp.name}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <Icon
                      name={dp.icon}
                      size="15px"
                      className="text-muted-foreground"
                    />
                    <span className="text-sm text-foreground">{dp.name}</span>
                  </div>
                  <span className="text-sm font-bold text-foreground">
                    {dp.count}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-500"
                    style={{
                      width: `${Math.min((dp.count / 250) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </CardWrapper>

        {/* Risk by Status */}
        <CardWrapper title="Risk by Status" className="flex flex-col">
          {/* Column headers - fixed, don't scroll */}
          <div className="grid grid-cols-[2.5fr_0.6fr_0.7fr_0.6fr] text-[10px] font-semibold uppercase tracking-wide border-b border-border pb-1.5 gap-2 shrink-0">
            <span className="text-muted-foreground">Risk Status</span>
            <span className="text-center text-red-500">High</span>
            <span className="text-center text-amber-500">Medium</span>
            <span className="text-center text-emerald-500">Low</span>
          </div>
          <div
            className="overflow-y-auto flex-1 mt-1 pr-0.5"
            style={{ maxHeight: "220px" }}
          >
            {MOCK.riskByStatus.map((r) => (
              <div
                key={r.label}
                className="grid grid-cols-[2.5fr_0.6fr_0.7fr_0.6fr] items-center gap-2 py-2 border-b border-border last:border-0 hover:bg-accent/50 rounded px-0.5 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Icon
                    name={r.icon}
                    size="14px"
                    className="text-muted-foreground shrink-0"
                  />
                  <span className="text-xs text-foreground">{r.label}</span>
                </div>
                <div className="flex justify-center">
                  <span className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center text-[11px] font-bold text-white">
                    {r.high}
                  </span>
                </div>
                <div className="flex justify-center">
                  <span className="w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center text-[11px] font-bold text-white">
                    {r.medium}
                  </span>
                </div>
                <div className="flex justify-center">
                  <span className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center text-[11px] font-bold text-white">
                    {r.low}
                  </span>
                </div>
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

      {/* ── Row 4: Upcoming Events ─────────────────────────────────────────── */}
      <CardWrapper title="Upcoming Events" className="flex flex-col">
        <div
          className="overflow-y-auto flex-1 space-y-2 pr-0.5"
          style={{ maxHeight: "160px" }}
        >
          {MOCK.upcomingEvents.map((ev) => (
            <div
              key={ev.title}
              className="flex items-center gap-3 p-2 bg-accent rounded border border-border hover:border-primary/50 transition-colors"
            >
              <div
                className={`w-1 self-stretch rounded-full shrink-0 ${ev.statusColor}`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground">
                  {ev.title}
                </p>
              </div>
              <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground flex-wrap justify-end">
                <span className="flex items-center gap-1">
                  <Icon name="calendar" size="12px" />
                  {ev.date}
                </span>
                <span>{ev.daysLeft} days remaining</span>
                <span
                  className={`px-2 py-0.5 rounded-full font-semibold text-white text-[11px] ${ev.statusColor}`}
                >
                  {ev.status}
                </span>
                {Boolean(ev.openItems) && (
                  <span className="text-destructive">
                    {ev.openItems} open items ↑
                  </span>
                )}
                {Boolean(ev.actions) && (
                  <span>{ev.actions} actions pending →</span>
                )}
                {Boolean(ev.tasks) && <span>{ev.tasks} tasks →</span>}
              </div>
            </div>
          ))}
        </div>
      </CardWrapper>
    </div>
  );
}
