import React, { useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import CardWrapper from "./components/CardWrapper";
import { getRoleLabel } from "@/utils/commonUtils";
import { useAuth } from "@/context/authContext/useAuth";
import DateFilter from "./components/DateFilter";
import { useDateFilter } from "./hooks/useDateFilter";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import Icon from "@/components/custom/Icon";

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
    <div className="min-w-17.5">
      <div
        className={`text-lg font-semibold ${healthStyles[label] ?? "text-foreground"}`}
      >
        {value}%
      </div>
      <div
        className={`text-xs ${healthStyles[label] ?? "text-muted-foreground"}`}
      >
        {label}
      </div>
    </div>
  );
}

function MetricCard({
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

function SummaryCard({ icon: Icon, value, title, description, tone }) {
  const styles = {
    success: ["bg-green-50 text-green-600", "text-green-600"],
    danger: ["bg-destructive/10 text-destructive", "text-destructive"],
    secondary: ["bg-secondary/10 text-secondary", "text-secondary"],
  };

  return (
    <div className="flex items-center gap-4 rounded-xl border border-border/70 bg-card p-4">
      <div
        className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${styles[tone][0]}`}
      >
        <Icon name={Icon} size="28px" />
      </div>
      <div>
        <div className={`text-2xl font-semibold ${styles[tone][1]}`}>
          {value}
        </div>
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
          <MetricCard
            icon="document"
            iconColor="text-primary"
            iconBg="bg-primary/10"
            borderColor="border-primary/40"
            title="Pending Review Framework"
            navigation="/pending-reviews"
          >
            {" "}
            <p className="text-4xl font-bold text-primary group-hover:opacity-80 transition-opacity">
              7
            </p>
          </MetricCard>
          <MetricCard
            icon="history"
            iconColor="text-secondary"
            iconBg="bg-secondary/10"
            borderColor="border-secondary/40"
            title="In Review Framework"
            navigation="/in-review"
          >
            {" "}
            <p className="text-4xl font-bold text-secondary group-hover:opacity-80 transition-opacity">
              33
            </p>
          </MetricCard>
          <MetricCard
            icon="check-circle"
            iconColor="text-green-500"
            iconBg="bg-green-500/10"
            borderColor="border-green-500/40"
            title="Approved Framework"
            navigation="/approved"
          >
            {" "}
            <p className="text-4xl font-bold text-green-500 group-hover:opacity-80 transition-opacity">
              12345
            </p>
          </MetricCard>
          <MetricCard
            icon="back"
            iconColor="text-destructive"
            iconBg="bg-destructive/10"
            borderColor="border-destructive/40"
            title="Returned Framework"
            navigation="/returned"
          >
            {" "}
            <p className="text-4xl font-bold text-destructive group-hover:opacity-80 transition-opacity">
              543
            </p>
          </MetricCard>
        </div>
      </CardWrapper>

      <CardWrapper
        title={
          <div>
            <CardTitle className="text-lg">Review Requests</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Deployment frameworks requested by auditors for expert review.
            </p>
          </div>
        }
        right={
          <div className="flex flex-wrap gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-fit">
                  Review Status
                  <Icon
                    name="chevron-down"
                    size="16px"
                    className="opacity-50"
                  />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-fit">
                <DropdownMenuItem>All Status</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem>Pending</DropdownMenuItem>
                <DropdownMenuItem>In Review</DropdownMenuItem>
                <DropdownMenuItem>Returned</DropdownMenuItem>
                <DropdownMenuItem>Approved</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
      >
        <CardContent className="p-0">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-275 text-sm">
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
                  <tr
                    key={item.id}
                    className="border-b border-border/50 last:border-0 hover:bg-muted/30"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-semibold text-primary">
                          {item.framework.split(" ")[0].slice(0, 4)}
                        </div>
                        <div>
                          <div className="font-medium text-foreground">
                            {item.framework}
                          </div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {item.customer}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">
                        {item.assignedFramework}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {item.assignedVersion}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{item.packageVersion}</div>
                      <div className="mt-1">
                        <StatusBadge status={item.packageStatus} />
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{item.requestedBy}</div>
                      <div className="mt-1 max-w-40 truncate text-xs text-muted-foreground">
                        {item.requesterEmail}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{item.requestedAt}</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {item.requestedDate}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-4">
                      <HealthValue
                        value={item.health}
                        label={item.healthLabel}
                      />
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Button
                        size="sm"
                        className="gap-1 bg-primary text-primary-foreground hover:bg-primary/90"
                      >
                        Review Now
                        <Icon name="chevron-right" size="16px" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-3 p-4 md:hidden">
            {reviewRequests.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-border/70 bg-card p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-semibold text-primary">
                      {item.framework.split(" ")[0].slice(0, 4)}
                    </div>
                    <div>
                      <div className="text-sm font-medium">
                        {item.framework}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {item.customer}
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={item.status} />
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-muted-foreground">Package</span>
                    <p className="mt-1 font-medium">{item.packageVersion}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Requested By</span>
                    <p className="mt-1 font-medium">{item.requestedBy}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      Assigned Framework
                    </span>
                    <p className="mt-1 font-medium">{item.assignedFramework}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Health</span>
                    <div className="mt-1">
                      <HealthValue
                        value={item.health}
                        label={item.healthLabel}
                      />
                    </div>
                  </div>
                </div>

                <Button className="mt-4 w-full bg-primary hover:bg-primary/90">
                  Review Now{" "}
                  <Icon name="chevron-right" size="16px" className="ml-1" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </CardWrapper>

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.4fr]">
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">My Review Summary</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <SummaryCard
              icon="check-circle"
              value="12"
              title="Approved"
              description="Packages approved by you"
              tone="success"
            />
            <SummaryCard
              icon="refresh"
              value="5"
              title="Returned"
              description="Packages sent back for changes"
              tone="danger"
            />
            <SummaryCard
              icon="message-square"
              value="28"
              title="Remarks Added"
              description="Review remarks added by you"
              tone="secondary"
            />
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Review Process</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-5 md:grid-cols-5">
              {[
                [
                  "audit",
                  "1. Review Request",
                  "Auditor requests review for deployment framework.",
                  "bg-primary/10 text-primary",
                ],
                [
                  "analytics",
                  "2. Review & Analysis",
                  "Review deployment points, comparison & gap analysis.",
                  "bg-secondary/10 text-secondary",
                ],
                [
                  "message-square",
                  "3. Add Remark",
                  "Add review remark for each deployment point.",
                  "bg-orange-50 text-orange-600",
                ],
                [
                  "report",
                  "4. Approve / Return",
                  "Approve if acceptable or return for changes.",
                  "bg-amber-50 text-amber-600",
                ],
                [
                  "rocket",
                  "5. Next Steps",
                  "Auditor updates and resubmits or package gets approved.",
                  "bg-primary/10 text-primary",
                ],
              ].map(([iconName, title, text, tone], index) => (
                <React.Fragment key={title}>
                  <div className="flex gap-3 md:block">
                    <div
                      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${tone}`}
                    >
                      <Icon name={iconName} size="24px" />
                    </div>
                    <div className="mt-0 md:mt-3">
                      <p className="text-sm font-semibold">{title}</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {text}
                      </p>
                    </div>
                  </div>
                  {index < 4 && (
                    <Icon
                      name="chevron-right"
                      size="24px"
                      className="hidden self-center text-muted-foreground/60 md:block"
                    />
                  )}
                </React.Fragment>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-start justify-center gap-2 px-2 text-center text-xs text-muted-foreground">
        <Icon name="info" size="16px" className="mt-0.5 shrink-0" />
        <span>
          Overall Health is calculated based on comparison and gap analysis of
          deployment points.
        </span>
      </div>
    </div>
  );
}
