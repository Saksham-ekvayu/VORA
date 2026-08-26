/* eslint-disable react/prop-types */

import { useState, useMemo, useCallback } from "react";
import { Button } from "@/components/ui/button";
import Icon from "@/components/custom/Icon";
import { Shield } from "lucide-react";
import { SectionsSidebar } from "../shared/SidebarShared";
import { useAuth } from "@/context/authContext/useAuth";
import {
  getReviewIcon,
  isAuditor,
  getScoreColor,
  STATUS_IMPLEMENTED,
  STATUS_PARTIAL,
  STATUS_NOT_IMPLEMENTED,
  capitalizeFirst,
} from "@/utils/commonUtils";
import GapReviewCommentModal from "./GapReviewCommentModal";
import { ScrollArea } from "@/components/ui/scroll-area";

// ---------------------------------------------------------------------------
// Pure helpers (module level — no nesting)
// ---------------------------------------------------------------------------

function getStatusConfig(status) {
  switch (status?.toLowerCase()) {
    case STATUS_IMPLEMENTED:
      return {
        icon: <Icon name="check-circle" size="14px" />,
        text: STATUS_IMPLEMENTED,
        className: "bg-green-500/15 text-green-600",
      };
    case STATUS_PARTIAL:
      return {
        icon: <Icon name="alert-circle" size="14px" />,
        text: STATUS_PARTIAL,
        className: "bg-yellow-500/15 text-yellow-600",
      };
    case STATUS_NOT_IMPLEMENTED:
      return {
        icon: <Icon name="x-circle" size="14px" />,
        text: STATUS_NOT_IMPLEMENTED,
        className: "bg-red-500/15 text-red-600",
      };
    default:
      return {
        icon: <Icon name="info" size="14px" />,
        text: status || "unknown",
        className: "bg-gray-500/15 text-gray-600",
      };
  }
}

function pointMatchesStatus(point, status) {
  if (status === "all") return true;
  return point.implementation_status?.toLowerCase() === status.toLowerCase();
}

function pointMatchesSearch(point, q) {
  if (!q) return true;
  const haystack = [
    point.assigned_framework_control_name,
    point.assigned_dp?.point,
    point.deployment_framework_control_name,
    point.deployment_dp?.point,
    point.implementation_status,
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

function normalisePoint(p) {
  return {
    assigned_framework_control_id: p.assigned_framework_control_id || "",
    assigned_framework_control_name: p.assigned_framework_control_name || "",
    assigned_dp: p.assigned_framework_deployment_points ?? {},
    deployment_framework_control_id: p.deployment_framework_control_id || "",
    deployment_framework_control_name:
      p.deployment_framework_control_name || "",
    deployment_dp: p.deployment_framework_deployment_points ?? {},
    similarity_score: p.similarity_score ?? 0,
    implementation_status: p.implementation_status || "",
    reviewComment: p.reviewComment || "",
  };
}

function normaliseControl(controlObj) {
  const controlId = Object.keys(controlObj)[0];
  const rawPoints = controlObj[controlId] ?? [];
  return {
    controlId,
    controlName: rawPoints[0]?.assigned_framework_control_name || controlId,
    points: rawPoints.map(normalisePoint),
  };
}

function buildSectionsMap(deploymentGaps) {
  const raw = deploymentGaps?.deployment_gap_results ?? [];
  const map = {};

  if (raw.length === 0) return map;

  // Check if it's a flat array of points
  if (
    raw[0].assigned_framework_control_id !== undefined ||
    raw[0].assigned_framework_section_id !== undefined
  ) {
    raw.forEach((p) => {
      const sectionId = p.assigned_framework_section_id || "Uncategorized";
      const sectionName = p.assigned_framework_section_name || sectionId;

      if (!map[sectionId]) {
        map[sectionId] = {
          id: sectionId,
          name: sectionName,
          controls: [],
        };
      }

      const controlId = p.assigned_framework_control_id || "Unknown Control";
      const controlName = p.assigned_framework_control_name || controlId;

      let control = map[sectionId].controls.find(
        (c) => c.controlId === controlId
      );
      if (!control) {
        control = {
          controlId: controlId,
          controlName: controlName,
          points: [],
        };
        map[sectionId].controls.push(control);
      }

      control.points.push(normalisePoint(p));
    });
  } else {
    // Fallback for old hierarchical structure
    raw.forEach((section) => {
      map[section.id] = {
        id: section.id,
        name: section.name || section.id,
        controls: (section.controls ?? []).map(normaliseControl),
      };
    });
  }

  return map;
}

function computeStats(allPoints) {
  return {
    total: allPoints.length,
    implemented: allPoints.filter(
      (p) => p.implementation_status?.toLowerCase() === STATUS_IMPLEMENTED
    ).length,
    partial: allPoints.filter(
      (p) => p.implementation_status?.toLowerCase() === STATUS_PARTIAL
    ).length,
    notImpl: allPoints.filter(
      (p) => p.implementation_status?.toLowerCase() === STATUS_NOT_IMPLEMENTED
    ).length,
  };
}

function countImplemented(points) {
  return points.filter(
    (p) => p.implementation_status?.toLowerCase() === STATUS_IMPLEMENTED
  ).length;
}

function countPartial(points) {
  return points.filter(
    (p) => p.implementation_status?.toLowerCase() === STATUS_PARTIAL
  ).length;
}

function countNotImplemented(points) {
  return points.filter(
    (p) => p.implementation_status?.toLowerCase() === STATUS_NOT_IMPLEMENTED
  ).length;
}

function pluralPoints(n) {
  return n === 1 ? "1 point" : `${n} points`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatusBadge = ({ status }) => {
  const config = getStatusConfig(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold whitespace-nowrap capitalize ${config.className}`}
    >
      {config.icon}
      {config.text}
    </span>
  );
};

const SimilarityScore = ({ score }) => {
  const percentage = Math.round(score);
  const color = getScoreColor(percentage);
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-bold" style={{ color }}>
        {percentage}%
      </span>
    </div>
  );
};

const GapPointExpanded = ({ point, user, onReviewClick, packageStatus }) => {
  const hasComment = !!point.reviewComment?.trim();

  const showReviewButton =
    !isAuditor(user?.role) ||
    (hasComment && packageStatus?.toLowerCase() !== "pending");
  const buttonVariant = hasComment ? "default" : "outline";

  return (
    <div className="p-3 border-t border-border bg-muted/10 space-y-3">
      {/* Metadata Panel */}
      <div className="flex flex-wrap items-center justify-between gap-4 text-xs bg-card p-2.5 rounded border border-border/60 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground font-semibold uppercase tracking-wider text-[10px]">
            Status:
          </span>
          <StatusBadge status={point.implementation_status} />
        </div>
        <div className="flex items-center gap-4 whitespace-nowrap">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground font-semibold uppercase tracking-wider text-[10px]">
              Similarity Score:
            </span>
            <SimilarityScore score={point.similarity_score} />
          </div>
          {showReviewButton && (
            <Button
              size="xs"
              variant={buttonVariant}
              onClick={() => onReviewClick?.(point)}
            >
              <Icon name={getReviewIcon(user?.role, hasComment)} />
              Review
            </Button>
          )}
        </div>
      </div>

      {/* Side-by-Side Comparison Table */}
      <ScrollArea className="rounded border border-border bg-card shadow-sm">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="text-left py-2.5 px-4 font-semibold text-xs uppercase tracking-wider text-muted-foreground w-1/2 border-r border-border">
                Assigned Framework
              </th>
              <th className="text-left py-2.5 px-4 font-semibold text-xs uppercase tracking-wider text-muted-foreground w-1/2">
                Deployment Framework
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="p-4 align-top border-r border-border space-y-4">
                {/* Assigned Control Info */}
                <div className="space-y-1">
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Control Details
                  </div>
                  <div className="flex items-start gap-2 min-w-0">
                    <span className="font-mono bg-muted px-2 py-0.5 rounded border border-border text-[11px] font-semibold text-foreground whitespace-nowrap mt-0.5">
                      {point.assigned_framework_control_id || "N/A"}
                    </span>
                    <span
                      className="text-xs font-semibold text-foreground/80 leading-relaxed"
                      title={point.assigned_framework_control_name}
                    >
                      {capitalizeFirst(point.assigned_framework_control_name)}
                    </span>
                  </div>
                </div>

                {/* Assigned DP Info */}
                <div className="space-y-1.5">
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Deployment Point{" "}
                    {point.assigned_dp?.id ? `#${point.assigned_dp.id}` : ""}
                  </div>
                  {point.assigned_dp?.point ? (
                    <p className="text-sm leading-relaxed border-l-2 border-primary pl-3 bg-primary/5 py-2.5 rounded-r text-foreground/90 font-medium">
                      {point.assigned_dp.point}
                    </p>
                  ) : (
                    <span className="text-muted-foreground italic text-xs">
                      N/A
                    </span>
                  )}
                </div>
              </td>

              <td className="p-4 align-top space-y-4">
                {/* Deployment Control Info */}
                <div className="space-y-1">
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Control Details
                  </div>
                  <div className="flex items-start gap-2 min-w-0">
                    <span className="font-mono bg-muted px-2 py-0.5 rounded border border-border text-[11px] font-semibold text-foreground whitespace-nowrap mt-0.5">
                      {point.deployment_framework_control_id || "N/A"}
                    </span>
                    <span
                      className="text-xs font-semibold text-foreground/80 leading-relaxed"
                      title={point.deployment_framework_control_name}
                    >
                      {capitalizeFirst(point.deployment_framework_control_name)}
                    </span>
                  </div>
                </div>

                {/* Deployment DP Info */}
                <div className="space-y-1.5">
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Deployment Point{" "}
                    {point.deployment_dp?.id
                      ? `#${point.deployment_dp.id}`
                      : ""}
                  </div>
                  {point.deployment_dp?.point ? (
                    <p className="text-sm leading-relaxed border-l-2 border-emerald-500 pl-3 bg-emerald-50 dark:bg-emerald-900/10 py-2.5 rounded-r text-foreground/90 font-medium">
                      {point.deployment_dp.point}
                    </p>
                  ) : (
                    <span className="text-muted-foreground italic text-xs">
                      No matching deployment point
                    </span>
                  )}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </ScrollArea>
    </div>
  );
};
const GapPointCard = ({
  point,
  index,
  isExpanded,
  onToggle,
  user,
  onReviewClick,
  packageStatus,
}) => {
  return (
    <div className="border border-border rounded overflow-hidden bg-card">
      <button
        type="button"
        className="w-full flex items-center justify-between p-2 cursor-pointer hover:bg-muted/50 transition-colors text-left min-w-0"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="text-xs font-mono bg-muted px-2 py-1 rounded whitespace-nowrap shrink-0">
            Point {index + 1}
          </span>
          <span className="text-sm font-medium flex-1 leading-relaxed wrap-break-word">
            {capitalizeFirst(point.assigned_dp?.point)}
          </span>
          {/* <StatusBadge status={point.implementation_status} /> */}
        </div>
        <span className="p-1 hover:bg-muted rounded ml-2 shrink-0">
          {isExpanded ? (
            <Icon name="chevron-up" size="18px" />
          ) : (
            <Icon name="chevron-down" size="18px" />
          )}
        </span>
      </button>

      {isExpanded && (
        <GapPointExpanded
          point={point}
          user={user}
          onReviewClick={onReviewClick}
          packageStatus={packageStatus}
        />
      )}
    </div>
  );
};

const ControlStatusCounts = ({ points }) => {
  const impl = countImplemented(points);
  const partial = countPartial(points);
  const notImpl = countNotImplemented(points);

  return (
    <div className="flex items-center gap-1.5 text-xs">
      {impl > 0 && (
        <span className="flex items-center gap-1 text-green-600 bg-green-50 px-1.5 py-0.5 rounded dark:bg-green-900/20">
          <Icon name="check-circle" size="12px" />
          {impl}
        </span>
      )}
      {partial > 0 && (
        <span className="flex items-center gap-1 text-yellow-600 bg-yellow-50 px-1.5 py-0.5 rounded dark:bg-yellow-900/20">
          <Icon name="alert-circle" size="12px" />
          {partial}
        </span>
      )}
      {notImpl > 0 && (
        <span className="flex items-center gap-1 text-red-600 bg-red-50 px-1.5 py-0.5 rounded dark:bg-red-900/20">
          <Icon name="x-circle" size="12px" />
          {notImpl}
        </span>
      )}
    </div>
  );
};

const StatsCard = ({
  label,
  value,
  activeFilter,
  filterValue,
  colorClass,
  borderActiveClass,
  onClick,
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`flex items-center justify-between p-2 rounded bg-card border cursor-pointer transition-colors ${
      activeFilter === filterValue ? borderActiveClass : "border-border"
    }`}
  >
    <p className="text-xs font-medium tracking-wider text-muted-foreground capitalize">
      {label}
    </p>
    <p className={`text-xl font-bold ${colorClass}`}>{value}</p>
  </button>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function GapsTable({
  deploymentGaps,
  onRefresh,
  packageStatus,
  globalSearch = "",
}) {
  const { user } = useAuth();
  const [filterStatus, setFilterStatus] = useState("all");
  const [activeSectionId, setActiveSectionId] = useState(null);
  const [activeControlId, setActiveControlId] = useState(null);
  const [expandedPoints, setExpandedPoints] = useState(new Set());

  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState(null);

  const handleReviewClick = useCallback((point) => {
    setSelectedPoint(point);
    setReviewModalOpen(true);
  }, []);

  const sectionsMap = useMemo(
    () => buildSectionsMap(deploymentGaps),
    [deploymentGaps]
  );

  const allPoints = useMemo(
    () =>
      Object.values(sectionsMap).flatMap((s) =>
        s.controls.flatMap((c) => c.points)
      ),
    [sectionsMap]
  );

  const stats = useMemo(() => computeStats(allPoints), [allPoints]);

  const sectionsList = useMemo(() => {
    const list = Object.values(sectionsMap);
    if (!globalSearch) return list;
    const q = globalSearch.toLowerCase();

    return list.filter((s) => {
      if (s.name.toLowerCase().includes(q) || s.id.toLowerCase().includes(q))
        return true;
      return s.controls.some((c) => {
        if (
          c.controlName.toLowerCase().includes(q) ||
          c.controlId.toLowerCase().includes(q)
        )
          return true;
        return c.points.some((p) => pointMatchesSearch(p, q));
      });
    });
  }, [sectionsMap, globalSearch]);

  const resolvedSectionId = useMemo(() => {
    if (sectionsList.length === 0) return null;
    if (activeSectionId && sectionsList.some((s) => s.id === activeSectionId))
      return activeSectionId;
    return sectionsList[0]?.id ?? null;
  }, [sectionsList, activeSectionId]);

  const activeSection = resolvedSectionId
    ? sectionsMap[resolvedSectionId]
    : null;

  const filteredControls = useMemo(() => {
    if (!activeSection) return [];
    const q = globalSearch.toLowerCase();

    return activeSection.controls
      .filter((ctrl) => {
        if (!q) return true;
        if (
          ctrl.controlId.toLowerCase().includes(q) ||
          ctrl.controlName.toLowerCase().includes(q)
        )
          return true;
        return ctrl.points.some((p) => pointMatchesSearch(p, q));
      })
      .map((ctrl) => ({
        ...ctrl,
        points: ctrl.points.filter(
          (p) => pointMatchesStatus(p, filterStatus) && pointMatchesSearch(p, q)
        ),
      }))
      .filter((ctrl) => ctrl.points.length > 0);
  }, [activeSection, filterStatus, globalSearch]);

  const selectedControl = useMemo(() => {
    if (!activeSection || activeSection.controls.length === 0) return null;
    const found = activeSection.controls.find(
      (c) => c.controlId === activeControlId
    );
    return found || activeSection.controls[0];
  }, [activeSection, activeControlId]);

  const filteredPointsForSelectedControl = useMemo(() => {
    if (!selectedControl) return [];
    const q = globalSearch.toLowerCase();
    return selectedControl.points.filter(
      (p) => pointMatchesStatus(p, filterStatus) && pointMatchesSearch(p, q)
    );
  }, [selectedControl, filterStatus, globalSearch]);

  const getSectionCount = (section) => {
    const q = globalSearch.toLowerCase();
    return section.controls.filter((ctrl) =>
      ctrl.points.some(
        (p) => pointMatchesStatus(p, filterStatus) && pointMatchesSearch(p, q)
      )
    ).length;
  };

  const togglePoint = (pointKey) => {
    setExpandedPoints((prev) => {
      const next = new Set(prev);
      if (next.has(pointKey)) {
        next.delete(pointKey);
      } else {
        next.add(pointKey);
      }
      return next;
    });
  };

  const expandAll = () => {
    if (!selectedControl) return;
    const allPointKeys = new Set();
    filteredPointsForSelectedControl.forEach((_, idx) => {
      allPointKeys.add(`${selectedControl.controlId}-${idx}`);
    });
    setExpandedPoints(allPointKeys);
  };

  const collapseAll = () => {
    setExpandedPoints(new Set());
  };

  const renderPointsList = () => {
    if (!selectedControl) {
      return (
        <div className="p-10 text-center text-muted-foreground text-sm">
          Select a control to view points.
        </div>
      );
    }

    if (filteredPointsForSelectedControl.length === 0) {
      return (
        <div className="p-10 text-center text-muted-foreground text-sm">
          No matching points found for this control.
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {filteredPointsForSelectedControl.map((point, idx) => {
          const pointKey = `${selectedControl.controlId}-${idx}`;
          return (
            <GapPointCard
              key={pointKey}
              point={point}
              index={idx}
              isExpanded={expandedPoints.has(pointKey)}
              onToggle={() => togglePoint(pointKey)}
              user={user}
              onReviewClick={handleReviewClick}
              packageStatus={packageStatus}
            />
          );
        })}
      </div>
    );
  };

  if (!deploymentGaps) return null;

  return (
    <div className="space-y-2">
      {allPoints.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatsCard
            label="total points"
            value={stats.total}
            activeFilter={filterStatus}
            filterValue="all"
            colorClass=""
            borderActiveClass="border-primary"
            onClick={() => setFilterStatus("all")}
          />
          <StatsCard
            label={STATUS_IMPLEMENTED}
            value={stats.implemented}
            activeFilter={filterStatus}
            filterValue={STATUS_IMPLEMENTED}
            colorClass="text-green-500"
            borderActiveClass="border-green-500"
            onClick={() => setFilterStatus(STATUS_IMPLEMENTED)}
          />
          <StatsCard
            label={STATUS_PARTIAL}
            value={stats.partial}
            activeFilter={filterStatus}
            filterValue={STATUS_PARTIAL}
            colorClass="text-yellow-500"
            borderActiveClass="border-yellow-500"
            onClick={() => setFilterStatus(STATUS_PARTIAL)}
          />
          <StatsCard
            label={STATUS_NOT_IMPLEMENTED}
            value={stats.notImpl}
            activeFilter={filterStatus}
            filterValue={STATUS_NOT_IMPLEMENTED}
            colorClass="text-red-500"
            borderActiveClass="border-red-500"
            onClick={() => setFilterStatus(STATUS_NOT_IMPLEMENTED)}
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-[calc(100vh-400px)] min-h-125 bg-background">
        {/* LEFT: Sections sidebar */}
        <div className="lg:col-span-3 flex h-full">
          <SectionsSidebar
            sectionsList={sectionsList}
            resolvedSectionId={resolvedSectionId}
            getSectionCount={getSectionCount}
            onSectionClick={setActiveSectionId}
            totalCount={sectionsList.length}
          />
        </div>

        {/* MIDDLE: Controls list */}
        <div className="lg:col-span-3 flex flex-col rounded border border-border bg-card shadow-sm overflow-hidden h-full">
          <div className="px-2 py-3 border-b border-border bg-primary/5 shrink-0">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <Shield className="w-4 h-4 text-primary shrink-0" />
                <h3 className="font-bold text-foreground text-sm truncate">
                  {capitalizeFirst(activeSection?.name)}
                </h3>
              </div>
              <span className="text-xs font-semibold text-primary-foreground bg-primary px-2 py-0.5 rounded shrink-0">
                {filteredControls.length}
              </span>
            </div>
          </div>

          <ScrollArea className="flex-1 bg-muted/10">
            <div className="p-2 space-y-2">
              {filteredControls.length === 0 ? (
                <div className="p-10 text-center text-muted-foreground text-sm">
                  No controls found.
                </div>
              ) : (
                filteredControls.map((ctrl) => {
                  const isSelected =
                    selectedControl?.controlId === ctrl.controlId;
                  return (
                    <button
                      type="button"
                      key={ctrl.controlId}
                      onClick={() => setActiveControlId(ctrl.controlId)}
                      className={`w-full flex flex-col p-2.5 rounded border text-left cursor-pointer transition-all ${
                        isSelected
                          ? "bg-primary/5 border-primary shadow-sm"
                          : "bg-card border-border hover:bg-muted/30"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 w-full mb-1">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isSelected
                              ? "bg-primary text-primary-foreground"
                              : "bg-primary/10 text-primary"
                          }`}
                        >
                          {ctrl.controlId}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-medium">
                          {pluralPoints(ctrl.points.length)}
                        </span>
                      </div>
                      <span className="font-semibold text-xs text-foreground line-clamp-1 mb-2">
                        {capitalizeFirst(ctrl.controlName)}
                      </span>
                      <div className="flex items-center justify-between w-full">
                        <ControlStatusCounts points={ctrl.points} />
                        <Icon
                          name="chevron-right"
                          size="14px"
                          className={`text-muted-foreground/60 transition-transform ${
                            isSelected ? "translate-x-0.5 text-primary" : ""
                          }`}
                        />
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </div>

        {/* RIGHT: DPs List for selected control */}
        <div className="lg:col-span-6 flex flex-col rounded border border-border bg-card shadow-sm overflow-hidden h-full">
          <div className="px-2 py-3 border-b border-border bg-primary/5 shrink-0">
            {selectedControl ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary whitespace-nowrap">
                      {selectedControl.controlId}
                    </span>
                    <h3
                      className="font-bold text-foreground text-sm truncate"
                      title={selectedControl.controlName}
                    >
                      {capitalizeFirst(selectedControl.controlName)}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={expandAll}
                      className="h-8 px-1.5 text-[11px]"
                    >
                      Expand All
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={collapseAll}
                      className="h-8 px-1.5 text-[11px]"
                    >
                      Collapse All
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-muted-foreground" />
                <h3 className="font-bold text-muted-foreground text-sm">
                  Points Detail
                </h3>
              </div>
            )}
          </div>

          <ScrollArea className="flex-1 bg-muted/10">
            <div className="p-2">{renderPointsList()}</div>
          </ScrollArea>
        </div>
      </div>

      <GapReviewCommentModal
        isOpen={reviewModalOpen}
        onClose={() => {
          setReviewModalOpen(false);
          setSelectedPoint(null);
        }}
        point={selectedPoint}
        userRole={user?.role}
        onSave={onRefresh}
      />
    </div>
  );
}
