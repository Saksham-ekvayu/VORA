import React, { useEffect, useState } from "react";
import {
  FileCheck2,
  History,
  CheckCircle2,
  RotateCcw,
  BarChart3,
  MessageSquare,
  FileSearch,
  ClipboardCheck,
  Rocket,
  ChevronRight,
  ChevronDown,
  Info,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import CardWrapper from "./components/CardWrapper";
import { getRoleLabel } from "@/utils/commonUtils";
import { useAuth } from "@/context/authContext/useAuth";
import DateFilter from "./components/DateFilter";
import { useDateFilter } from "./hooks/useDateFilter";

const reviewRequests = [
  {
    id: "df-001",
    framework: "ISO27001:2022 - Deployment Framework",
    customer: "Acme Corporation",
    assignedFramework: "ISO27001:2022",
    assignedVersion: "v1.0",
    packageVersion: "2.1.0",
    packageStatus: "In Review",
    requestedBy: "Auditor John",
    requesterEmail: "auditor.john@acme.com",
    requestedAt: "2 hours ago",
    requestedDate: "08 May 2025",
    status: "In Review",
    health: 68,
    healthLabel: "Medium",
  },
  {
    id: "df-002",
    framework: "ISO9001:2015 - QMS Framework",
    customer: "Tech Solutions Ltd.",
    assignedFramework: "ISO9001:2015",
    assignedVersion: "v2.0",
    packageVersion: "1.3.0",
    packageStatus: "Pending",
    requestedBy: "Auditor Sarah",
    requesterEmail: "auditor.sarah@tech.com",
    requestedAt: "1 day ago",
    requestedDate: "07 May 2025",
    status: "Pending",
    health: 82,
    healthLabel: "Good",
  },
  {
    id: "df-003",
    framework: "SOC 2 Type II - Security Framework",
    customer: "DataSecure Inc.",
    assignedFramework: "SOC 2 Type II",
    assignedVersion: "v1.0",
    packageVersion: "3.0.0",
    packageStatus: "In Review",
    requestedBy: "Auditor Mike",
    requesterEmail: "auditor.mike@datasec.com",
    requestedAt: "2 days ago",
    requestedDate: "06 May 2025",
    status: "In Review",
    health: 55,
    healthLabel: "Medium",
  },
  {
    id: "df-004",
    framework: "GDPR Compliance Framework",
    customer: "Global Systems",
    assignedFramework: "GDPR",
    assignedVersion: "v1.1",
    packageVersion: "1.0.0",
    packageStatus: "Pending",
    requestedBy: "Auditor Emma",
    requesterEmail: "emma@globalsys.com",
    requestedAt: "3 days ago",
    requestedDate: "06 May 2025",
    status: "Pending",
    health: 72,
    healthLabel: "Good",
  },
];

const statusStyles = {
  Pending: "border-amber-200 bg-amber-50 text-amber-700",
  "In Review": "border-purple-200 bg-purple-50 text-purple-700",
  Returned: "border-red-200 bg-red-50 text-red-700",
  Approved: "border-green-200 bg-green-50 text-green-700",
};

const healthStyles = {
  Good: "text-green-600",
  Medium: "text-amber-600",
  Critical: "text-destructive",
};

function StatusBadge({ status }) {
  return (
    <Badge
      variant="outline"
      className={`rounded-full px-3 py-1 text-xs font-medium ${statusStyles[status] ?? ""}`}
    >
      {status}
    </Badge>
  );
}

function HealthValue({ value, label }) {
  return (
    <div className="min-w-[70px]">
      <div className={`text-lg font-semibold ${healthStyles[label] ?? "text-foreground"}`}>
        {value}%
      </div>
      <div className={`text-xs ${healthStyles[label] ?? "text-muted-foreground"}`}>
        {label}
      </div>
    </div>
  );
}

function MetricCard({ icon: Icon, title, value, description, tone }) {
  const tones = {
    primary: "bg-primary/10 text-primary",
    secondary: "bg-secondary/10 text-secondary",
    success: "bg-green-50 text-green-600",
    danger: "bg-destructive/10 text-destructive",
  };

  const valueColors = {
    primary: "text-primary",
    secondary: "text-secondary",
    success: "text-green-600",
    danger: "text-destructive",
  };

  return (
    <Card className="border-border/70 shadow-sm">
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-xl ${tones[tone]}`}>
          <Icon className="h-8 w-8" strokeWidth={1.8} />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className={`mt-1 text-3xl font-semibold ${valueColors[tone]}`}>{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryCard({ icon: Icon, value, title, description, tone }) {
  const styles = {
    success: ["bg-green-50 text-green-600", "text-green-600"],
    danger: ["bg-destructive/10 text-destructive", "text-destructive"],
    secondary: ["bg-secondary/10 text-secondary", "text-secondary"],
  };

  return (
    <div className="flex items-center gap-4 rounded-xl border border-border/70 bg-card p-4">
      <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${styles[tone][0]}`}>
        <Icon className="h-7 w-7" strokeWidth={1.8} />
      </div>
      <div>
        <div className={`text-2xl font-semibold ${styles[tone][1]}`}>{value}</div>
        <div className="text-sm font-medium text-foreground">{title}</div>
        <div className="text-xs text-muted-foreground">{description}</div>
      </div>
    </div>
  );
}

export default function InternalExpertDashboard() {
  const { user } = useAuth();
  const [currentTime, setCurrentTime] = useState(new Date());

  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-3 my-2">
      {/* Metrics */}
      <CardWrapper
        title={
          <>
            Welcome, {user?.name}
            <span className="text-sm ml-1">
              ({user?.role && getRoleLabel(user.role)})
            </span>{" "}
            👋
          </>
        }
        right={
          <div className="flex items-center gap-4">
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
        }
      >
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <MetricCard icon={FileCheck2} title="Pending Review" value="7" description="Awaiting your review" tone="primary" />
          <MetricCard icon={History} title="In Review" value="3" description="Currently under review" tone="secondary" />
          <MetricCard icon={CheckCircle2} title="Approved" value="12" description="Approved packages" tone="success" />
          <MetricCard icon={RotateCcw} title="Returned" value="5" description="Sent back for changes" tone="danger" />
        </div>
      </CardWrapper>

      <Card className="overflow-hidden border-border/70 shadow-sm">
        <CardHeader className="gap-4 border-b border-border/60 pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="text-lg">Review Requests</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Deployment frameworks requested by auditors for expert review.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-[160px] bg-card justify-between font-normal text-muted-foreground">
                  All Frameworks
                  <ChevronDown className="h-4 w-4 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-[160px]">
                <DropdownMenuItem>All Frameworks</DropdownMenuItem>
                <DropdownMenuItem>ISO27001</DropdownMenuItem>
                <DropdownMenuItem>ISO9001</DropdownMenuItem>
                <DropdownMenuItem>SOC 2</DropdownMenuItem>
                <DropdownMenuItem>GDPR</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-[165px] bg-card justify-between font-normal text-muted-foreground">
                  Sort: Requested At
                  <ChevronDown className="h-4 w-4 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-[165px]">
                <DropdownMenuItem>Sort: Requested At</DropdownMenuItem>
                <DropdownMenuItem>Sort: Health</DropdownMenuItem>
                <DropdownMenuItem>Sort: Package Version</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="flex gap-2 overflow-x-auto border-b border-border/60 px-5 py-3">
            {[
              ["All", 7, true],
              ["Pending", 4],
              ["In Review", 3],
              ["Returned", 0],
              ["Approved", 0],
            ].map(([label, count, active]) => (
              <Button
                key={label}
                variant={active ? "default" : "outline"}
                size="sm"
                className={active ? "rounded-md bg-primary text-primary-foreground hover:bg-primary/90" : "rounded-md"}
              >
                {label} ({count})
              </Button>
            ))}
          </div>

          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[1100px] text-sm">
              <thead>
                <tr className="border-b border-border/60 bg-muted/40 text-left text-xs font-medium text-muted-foreground">
                  <th className="px-5 py-3">Deployment Framework</th>
                  <th className="px-4 py-3">Assigned Framework</th>
                  <th className="px-4 py-3">Package Version</th>
                  <th className="px-4 py-3">Requested By</th>
                  <th className="px-4 py-3">Requested At</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Overall Health</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {reviewRequests.map((item) => (
                  <tr key={item.id} className="border-b border-border/50 last:border-0 hover:bg-muted/30">
                    <td className="px-5 py-4">
                      <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-semibold text-primary">
                          {item.framework.split(" ")[0].slice(0, 4)}
                        </div>
                        <div>
                          <div className="font-medium text-foreground">{item.framework}</div>
                          <div className="mt-1 text-xs text-muted-foreground">{item.customer}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{item.assignedFramework}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{item.assignedVersion}</div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{item.packageVersion}</div>
                      <div className="mt-1"><StatusBadge status={item.packageStatus} /></div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{item.requestedBy}</div>
                      <div className="mt-1 max-w-[160px] truncate text-xs text-muted-foreground">{item.requesterEmail}</div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{item.requestedAt}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{item.requestedDate}</div>
                    </td>
                    <td className="px-4 py-4"><StatusBadge status={item.status} /></td>
                    <td className="px-4 py-4"><HealthValue value={item.health} label={item.healthLabel} /></td>
                    <td className="px-5 py-4 text-right">
                      <Button size="sm" className="gap-1 bg-primary text-primary-foreground hover:bg-primary/90">
                        Review Now
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-3 p-4 md:hidden">
            {reviewRequests.map((item) => (
              <div key={item.id} className="rounded-xl border border-border/70 bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-semibold text-primary">
                      {item.framework.split(" ")[0].slice(0, 4)}
                    </div>
                    <div>
                      <div className="text-sm font-medium">{item.framework}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{item.customer}</div>
                    </div>
                  </div>
                  <StatusBadge status={item.status} />
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                  <div><span className="text-muted-foreground">Package</span><p className="mt-1 font-medium">{item.packageVersion}</p></div>
                  <div><span className="text-muted-foreground">Requested By</span><p className="mt-1 font-medium">{item.requestedBy}</p></div>
                  <div><span className="text-muted-foreground">Assigned Framework</span><p className="mt-1 font-medium">{item.assignedFramework}</p></div>
                  <div><span className="text-muted-foreground">Health</span><div className="mt-1"><HealthValue value={item.health} label={item.healthLabel} /></div></div>
                </div>

                <Button className="mt-4 w-full bg-primary hover:bg-primary/90">
                  Review Now <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.4fr]">
        <Card className="border-border/70 shadow-sm">
          <CardHeader><CardTitle className="text-lg">My Review Summary</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <SummaryCard icon={CheckCircle2} value="12" title="Approved" description="Packages approved by you" tone="success" />
            <SummaryCard icon={RotateCcw} value="5" title="Returned" description="Packages sent back for changes" tone="danger" />
            <SummaryCard icon={MessageSquare} value="28" title="Remarks Added" description="Review remarks added by you" tone="secondary" />
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader><CardTitle className="text-lg">Review Process</CardTitle></CardHeader>
          <CardContent>
            <div className="grid gap-5 md:grid-cols-5">
              {[
                [FileSearch, "1. Review Request", "Auditor requests review for deployment framework.", "bg-primary/10 text-primary"],
                [BarChart3, "2. Review & Analysis", "Review deployment points, comparison & gap analysis.", "bg-secondary/10 text-secondary"],
                [MessageSquare, "3. Add Remark", "Add review remark for each deployment point.", "bg-orange-50 text-orange-600"],
                [ClipboardCheck, "4. Approve / Return", "Approve if acceptable or return for changes.", "bg-amber-50 text-amber-600"],
                [Rocket, "5. Next Steps", "Auditor updates and resubmits or package gets approved.", "bg-primary/10 text-primary"],
              ].map(([Icon, title, text, tone], index) => (
                <React.Fragment key={title}>
                  <div className="flex gap-3 md:block">
                    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${tone}`}>
                      <Icon className="h-6 w-6" strokeWidth={1.8} />
                    </div>
                    <div className="mt-0 md:mt-3">
                      <p className="text-sm font-semibold">{title}</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">{text}</p>
                    </div>
                  </div>
                  {index < 4 && <ChevronRight className="hidden self-center text-muted-foreground/60 md:block" />}
                </React.Fragment>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-start justify-center gap-2 px-2 text-center text-xs text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>Overall Health is calculated based on comparison and gap analysis of deployment points.</span>
      </div>
    </div>
  );
}
