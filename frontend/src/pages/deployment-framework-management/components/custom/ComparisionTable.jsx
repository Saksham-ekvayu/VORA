/* eslint-disable react/prop-types */

import { useCallback, useMemo, useState } from "react";
import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";
import { ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SectionsSidebar } from "../shared/SidebarShared";
import { useAuth } from "@/context/authContext/useAuth";
import {
  getReviewIcon,
  isAuditor,
  getScoreColor,
  getScoreLabel,
  getScoreMatchClass,
  capitalizeFirst,
} from "@/utils/commonUtils";
import ComparisonReviewCommentModal from "./ComparisonReviewCommentModal";
import { ScrollArea } from "@/components/ui/scroll-area";

const CIRC = 2 * Math.PI * 22;

function ScoreDonut({ score, color, matchLabel, matchClass }) {
  const offset = (CIRC * (1 - score / 100)).toFixed(1);
  let labelClass = "bg-destructive/10 text-destructive";
  if (matchClass === "high") labelClass = "bg-primary/10 text-primary";
  else if (matchClass === "medium") labelClass = "bg-amber-100 text-amber-900";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="58" height="58" viewBox="0 0 58 58">
        <circle
          cx="29"
          cy="29"
          r="22"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="5.5"
        />
        <circle
          cx="29"
          cy="29"
          r="22"
          fill="none"
          stroke={color}
          strokeWidth="5.5"
          strokeDasharray="138.2"
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 29 29)"
        />
        <text
          x="29"
          y="34"
          textAnchor="middle"
          fontSize="13"
          fontWeight="700"
          fill="#1a1a2e"
        >
          {score}%
        </text>
      </svg>
      <span
        className={`text-xs font-bold px-2 py-0.5 rounded-full tracking-wider ${labelClass}`}
      >
        {matchLabel}
      </span>
    </div>
  );
}

function DeploymentPoints({ dps, open, onToggle }) {
  const points = dps ?? [];

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={onToggle}
        className="inline-flex items-center gap-1 text-xs text-primary font-medium cursor-pointer bg-transparent border-none px-0 py-0"
      >
        Deployment Points ({points.length})
        <Icon
          name="chevron-down"
          size="12px"
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-1.5">
          {points.map((point, i) => (
            <div key={point.id ?? i} className="flex items-start gap-2">
              <span className="text-muted-foreground shrink-0 text-xs mt-0.5 font-medium">
                {i + 1}.
              </span>
              <span className="text-xs leading-relaxed text-foreground/90 text-justify">
                {point.point ?? point}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ControlRow({
  control,
  openDp,
  onToggleDpOpen,
  user,
  onReviewClick,
  hasComment,
  packageStatus,
}) {
  const showReviewButton =
    !isAuditor(user?.role) ||
    (hasComment && packageStatus?.toLowerCase() !== "pending");
  const buttonVariant = hasComment ? "default" : "outline";

  return (
    <div
      className="grid gap-0 border-b border-border min-h-20"
      style={{ gridTemplateColumns: "1fr 1fr 120px" }}
    >
      {/* Assigned (framework) control — left column */}
      <div className="px-2 py-3">
        <div className="text-[10px] font-bold text-primary uppercase tracking-wider mb-0.5">
          {control.assigned.id}
        </div>
        <div className="text-sm font-semibold text-foreground mb-1 leading-snug">
          {capitalizeFirst(control.assigned.name)}
        </div>
        <div className="text-xs text-muted-foreground leading-relaxed mb-2.5 text-justify">
          {control.assigned.desc}
        </div>
        <DeploymentPoints
          dps={control.assigned.dps}
          open={openDp}
          onToggle={onToggleDpOpen}
        />
      </div>

      {/* Deployment framework control — right column */}
      <div className="px-2 py-3 border-l border-border">
        <div className="flex items-center justify-between gap-2">
          <div className="text-[10px] font-bold text-primary uppercase tracking-wider mb-0.5">
            {control.deployment.id}
          </div>
          {showReviewButton && (
            <Button
              size="xs"
              variant={buttonVariant}
              onClick={() => onReviewClick?.(control)}
            >
              <Icon name={getReviewIcon(user?.role, hasComment)} />
              Review
            </Button>
          )}
        </div>
        <div className="text-sm font-semibold text-foreground mb-1 leading-snug">
          {capitalizeFirst(control.deployment.name)}
        </div>
        <div className="text-xs text-muted-foreground leading-relaxed mb-2.5 text-justify">
          {control.deployment.desc}
        </div>
        <DeploymentPoints
          dps={control.deployment.dps}
          open={openDp}
          onToggle={onToggleDpOpen}
        />
      </div>

      {/* Score */}
      <div className="px-4 py-4 flex items-start justify-center border-l border-border">
        <ScoreDonut
          score={control.score}
          color={control.scoreColor}
          matchLabel={control.matchLabel}
          matchClass={control.matchClass}
        />
      </div>
    </div>
  );
}

/**
 * Accepts:
 *   comparisonDataSource = activePackage.comparison
 *
 * Shape:
 * {
 *   status, message, timestamp,
 *   comparison_result: [
 *     {
 *       id: "A.5",
 *       name: "General Controls",
 *       controls: [
 *         {
 *           deployment_framework_control_id,
 *           deployment_framework_control_name,
 *           deployment_framework_control_description,
 *           deployment_framework_deployment_points: [{ id, point }],
 *           assigned_framework_control_id,
 *           assigned_framework_control_name,
 *           assigned_framework_control_description,
 *           assigned_framework_deployment_points: [{ id, point }],
 *           comparison_score   // 0–1 float
 *         }
 *       ]
 *     }
 *   ]
 * }
 */
export default function ComparisonsTable({
  comparisonDataSource,
  onRefresh,
  packageStatus,
  globalSearch = "",
}) {
  const { user } = useAuth();
  const [sortOrder, setSortOrder] = useState("High to Low");
  const [activeSection, setActiveSection] = useState(null);
  const [openDpRowIds, setOpenDpRowIds] = useState(() => new Set());

  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedControl, setSelectedControl] = useState(null);

  const handleReviewClick = useCallback((control) => {
    setSelectedControl(control);
    setReviewModalOpen(true);
  }, []);

  const toggleDpOpenForRow = useCallback((controlId) => {
    setOpenDpRowIds((prev) => {
      const next = new Set(prev);
      if (next.has(controlId)) next.delete(controlId);
      else next.add(controlId);
      return next;
    });
  }, []);

  /**
   * Build a map: { [sectionId]: { id, name, items[] } }
   * from comparison_result array.
   */
  const sectionsMap = useMemo(() => {
    const raw = comparisonDataSource?.comparison_result ?? [];
    const map = {};
    raw.forEach((section) => {
      const sectionId = section.id;
      const items = (section.controls ?? []).map((ctrl, idx) => {
        const rawScore = ctrl.comparison_score ?? 0;
        // comparison_score is 0–1; convert to 0–100 percentage
        const score = Math.round(rawScore * 100);
        return {
          id: `${sectionId}-${idx}`,
          assigned: {
            id: ctrl.assigned_framework_control_id || "",
            name: ctrl.assigned_framework_control_name || "",
            desc: ctrl.assigned_framework_control_description || "",
            dps: ctrl.assigned_framework_deployment_points ?? [],
          },
          deployment: {
            id: ctrl.deployment_framework_control_id || "",
            name: ctrl.deployment_framework_control_name || "",
            desc: ctrl.deployment_framework_control_description || "",
            dps: ctrl.deployment_framework_deployment_points ?? [],
          },
          score,
          scoreColor: getScoreColor(score),
          matchLabel: getScoreLabel(score),
          matchClass: getScoreMatchClass(score),
          reviewComment: ctrl.reviewComment || "",
        };
      });

      map[sectionId] = {
        id: sectionId,
        name: section.name || sectionId,
        items,
      };
    });
    return map;
  }, [comparisonDataSource]);

  /** Filtered sidebar list */
  const sectionsList = useMemo(() => {
    const list = Object.values(sectionsMap);
    if (!globalSearch) return list;
    const q = globalSearch.toLowerCase();

    return list.filter((s) => {
      if (s.name.toLowerCase().includes(q) || s.id.toLowerCase().includes(q))
        return true;
      return s.items.some((c) => {
        if (
          c.assigned.name.toLowerCase().includes(q) ||
          c.deployment.name.toLowerCase().includes(q) ||
          c.assigned.desc.toLowerCase().includes(q) ||
          c.deployment.desc.toLowerCase().includes(q)
        )
          return true;
        const assignedMatch = c.assigned.dps.some((dp) => {
          const text = typeof dp === "string" ? dp : dp.point || dp.name || "";
          return text.toLowerCase().includes(q);
        });
        if (assignedMatch) return true;
        const deploymentMatch = c.deployment.dps.some((dp) => {
          const text = typeof dp === "string" ? dp : dp.point || dp.name || "";
          return text.toLowerCase().includes(q);
        });
        return deploymentMatch;
      });
    });
  }, [sectionsMap, globalSearch]);

  /** Active section id — fallback to first */
  const resolvedSectionId = useMemo(() => {
    if (sectionsList.length === 0) return null;
    if (activeSection && sectionsList.some((s) => s.id === activeSection))
      return activeSection;
    return sectionsList[0].id;
  }, [activeSection, sectionsList]);

  const activeSectionLabel = sectionsList.find(
    (s) => s.id === resolvedSectionId
  )?.name;

  const getSectionCount = useCallback(
    (section) => {
      if (!globalSearch) return section.items.length;
      const q = globalSearch.toLowerCase();
      return section.items.filter((c) => {
        if (
          c.assigned.name.toLowerCase().includes(q) ||
          c.deployment.name.toLowerCase().includes(q) ||
          c.assigned.desc.toLowerCase().includes(q) ||
          c.deployment.desc.toLowerCase().includes(q)
        )
          return true;
        const assignedMatch = c.assigned.dps.some((dp) => {
          const text = typeof dp === "string" ? dp : dp.point || dp.name || "";
          return text.toLowerCase().includes(q);
        });
        if (assignedMatch) return true;
        const deploymentMatch = c.deployment.dps.some((dp) => {
          const text = typeof dp === "string" ? dp : dp.point || dp.name || "";
          return text.toLowerCase().includes(q);
        });
        return deploymentMatch;
      }).length;
    },
    [globalSearch]
  );

  const filteredControls = useMemo(() => {
    if (!resolvedSectionId || !sectionsMap[resolvedSectionId]) return [];
    return sectionsMap[resolvedSectionId].items
      .filter((c) => {
        if (!globalSearch) return true;
        const q = globalSearch.toLowerCase();

        if (
          c.assigned.name.toLowerCase().includes(q) ||
          c.deployment.name.toLowerCase().includes(q) ||
          c.assigned.desc.toLowerCase().includes(q) ||
          c.deployment.desc.toLowerCase().includes(q)
        )
          return true;

        const assignedMatch = c.assigned.dps.some((dp) => {
          const text = typeof dp === "string" ? dp : dp.point || dp.name || "";
          return text.toLowerCase().includes(q);
        });
        if (assignedMatch) return true;
        const deploymentMatch = c.deployment.dps.some((dp) => {
          const text = typeof dp === "string" ? dp : dp.point || dp.name || "";
          return text.toLowerCase().includes(q);
        });
        return deploymentMatch;
      })
      .sort((a, b) =>
        sortOrder === "High to Low" ? b.score - a.score : a.score - b.score
      );
  }, [globalSearch, sectionsMap, resolvedSectionId, sortOrder]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-[calc(100vh-400px)] min-h-125 overflow-hidden">
      {/* Sidebar */}
      <div className="lg:col-span-3 flex h-full">
        <SectionsSidebar
          sectionsList={sectionsList}
          resolvedSectionId={resolvedSectionId}
          getSectionCount={getSectionCount}
          onSectionClick={setActiveSection}
          totalCount={sectionsList.length}
        />
      </div>

      {/* Main content */}
      <div className="lg:col-span-9 flex flex-col overflow-hidden bg-card border border-border rounded shadow-sm h-full">
        {/* Toolbar */}
        <div className="px-4 py-3 border-b border-border bg-primary/5 flex items-center justify-between shrink-0 gap-3">
          <div className="flex items-center gap-2 text-base font-semibold text-foreground shrink-0">
            <span className="text-primary flex items-center justify-center">
              <Icon name="file" size="14px" />
            </span>
            {capitalizeFirst(activeSectionLabel) || "No Section Selected"}
          </div>

          <div className="flex items-center gap-2">
            {/* Sort order */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="text-xs text-foreground border border-border rounded px-2.5 py-1.5 bg-muted cursor-pointer outline-none h-8 w-fit flex items-center justify-between gap-1"
                >
                  {sortOrder}
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {["High to Low", "Low to High"].map((o) => (
                  <DropdownMenuItem
                    key={o}
                    onSelect={() => setSortOrder(o)}
                    className="text-xs"
                  >
                    {o}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="w-full min-w-200">
            {/* Table header */}
            <div
              className="grid gap-0 border-b border-border shrink-0 bg-muted items-center px-1 py-1.5"
              style={{
                gridTemplateColumns: "1fr 1fr 120px",
              }}
            >
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Assigned Framework Control
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Deployment Framework Control
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground text-center">
                Semantic Score
              </span>
            </div>

            {/* Rows */}
            <div className="flex-1">
              {filteredControls.length === 0 ? (
                <div className="p-10 text-center text-muted-foreground text-sm">
                  No controls found.
                </div>
              ) : (
                filteredControls.map((control) => {
                  const hasComment = !!control.reviewComment?.trim();
                  return (
                    <ControlRow
                      key={control.id}
                      control={control}
                      openDp={openDpRowIds.has(control.id)}
                      onToggleDpOpen={() => toggleDpOpenForRow(control.id)}
                      user={user}
                      onReviewClick={handleReviewClick}
                      hasComment={hasComment}
                      packageStatus={packageStatus}
                    />
                  );
                })
              )}
            </div>
          </div>
        </ScrollArea>
      </div>
      <ComparisonReviewCommentModal
        isOpen={reviewModalOpen}
        onClose={() => {
          setReviewModalOpen(false);
          setSelectedControl(null);
        }}
        control={selectedControl}
        userRole={user?.role}
        onSave={onRefresh}
      />
    </div>
  );
}
