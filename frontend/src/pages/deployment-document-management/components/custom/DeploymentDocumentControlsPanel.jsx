/* eslint-disable react/prop-types */

import { useState, useMemo } from "react";
import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";

// Helper function to parse deployment points
const parseDeploymentPoints = (deploymentPoints) => {
  if (Array.isArray(deploymentPoints)) return deploymentPoints;

  if (typeof deploymentPoints === "string") {
    // Split on lines, strip leading "N. " numbering, drop empty entries
    return deploymentPoints
      .split("\n")
      .map((line) => {
        const trimmed = line.trim();
        // Remove leading "1. " / "12. " style numbering
        const dotIdx = trimmed.indexOf(". ");
        if (dotIdx > 0 && dotIdx <= 3) {
          const prefix = trimmed.slice(0, dotIdx);
          if (prefix.split("").every((ch) => ch >= "0" && ch <= "9")) {
            return trimmed.slice(dotIdx + 2).trim();
          }
        }
        return trimmed;
      })
      .filter(Boolean);
  }

  return [];
};

// Helper function to render point content
const renderPointContent = (point) => {
  if (typeof point === "string") return point.trim();
  if (typeof point === "object" && point?.dp) return point.dp;
  return JSON.stringify(point);
};

function DeploymentDocumentControlsPanel({
  controls,
  totalControls,
  onEdit,
  onDelete,
  canEdit,
}) {
  const [controlSearch, setControlSearch] = useState("");

  // Group controls - deployment documents have a flat structure
  const allControls = useMemo(() => {
    if (!controls || !Array.isArray(controls)) return [];

    return controls.map((control, index) => ({
      ...control,
      // Give each control a stable synthetic ID based on its index
      Control_id: control.Control_id || `CTRL-${index + 1}`,
      Control_name:
        control.Client_control_name ||
        control.Control_name ||
        `Control ${index + 1}`,
      Control_description:
        control.Client_control_description || control.Control_description || "",
      Deployment_points:
        control.Client_deployment_points || control.Deployment_points || [],
      Control_type: control.Control_type || "",
    }));
  }, [controls]);

  // Filter controls by search
  const controlsList = useMemo(() => {
    if (!controlSearch) return allControls;
    const lowerQ = controlSearch.toLowerCase();
    return allControls.filter(
      (c) =>
        c.Control_name.toLowerCase().includes(lowerQ) ||
        c.Control_id.toLowerCase().includes(lowerQ)
    );
  }, [allControls, controlSearch]);

  const [activeControlId, setActiveControlId] = useState(null);

  const resolvedControlId = useMemo(() => {
    if (controlsList.length === 0) return null;
    if (
      activeControlId &&
      controlsList.some((c) => c.Control_id === activeControlId)
    )
      return activeControlId;
    return controlsList[0].Control_id;
  }, [controlsList, activeControlId]);

  const activeControl = useMemo(() => {
    return controlsList.find((c) => c.Control_id === resolvedControlId) || null;
  }, [controlsList, resolvedControlId]);

  const points = parseDeploymentPoints(activeControl.Deployment_points);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-112.5 bg-background">
      {/* ===== LEFT PANEL: CONTROL LIST ===== */}
      <div className="lg:col-span-4 flex flex-col rounded border border-border bg-card shadow-sm overflow-hidden h-full">
        <div className="p-3 border-b border-border bg-primary/5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Icon name="document" size="18px" className="text-primary" />
              <h3 className="font-bold text-foreground">Controls</h3>
            </div>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-primary/15 text-primary">
              {totalControls ?? allControls.length}
            </span>
          </div>
          <div className="relative">
            <Icon
              name="search"
              size="14px"
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <input
              type="text"
              placeholder="Search controls..."
              value={controlSearch}
              onChange={(e) => setControlSearch(e.target.value)}
              className="w-full bg-background border border-border rounded pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto w-full">
          {controlsList.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              No controls found.
            </div>
          ) : (
            <div className="w-full">
              <div className="sticky top-0 bg-muted/80 backdrop-blur z-10 px-3 py-1.5 border-b border-border grid grid-cols-12 gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                <div className="col-span-1">#</div>
                <div className="col-span-11">Control Title</div>
              </div>
              <div className="divide-y divide-border">
                {controlsList.map((control, index) => (
                  <button
                    key={control.Control_id}
                    onClick={() => setActiveControlId(control.Control_id)}
                    className={`w-full text-left px-3 py-2 grid grid-cols-12 gap-2 items-center transition-colors cursor-pointer ${
                      resolvedControlId === control.Control_id
                        ? "bg-primary/10"
                        : "hover:bg-muted"
                    }`}
                  >
                    <div className="col-span-1">
                      <span
                        className={`text-xs font-semibold px-2 py-1 rounded inline-block ${
                          resolvedControlId === control.Control_id
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {index + 1}
                      </span>
                    </div>
                    <div
                      className={`col-span-11 text-sm font-medium pr-2 ${
                        resolvedControlId === control.Control_id
                          ? "text-primary"
                          : "text-foreground"
                      }`}
                    >
                      {control.Control_name}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ===== RIGHT PANEL: DETAILS ===== */}
      <div className="lg:col-span-8 flex flex-col rounded border border-border bg-card shadow-sm overflow-hidden h-full">
        {activeControl ? (
          <>
            <div className="p-3 border-b border-border bg-linear-to-r from-primary/10 to-transparent">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-foreground leading-tight mb-1">
                    {activeControl.Control_name}
                  </h2>
                  {activeControl.Control_type && (
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-secondary/20 text-secondary">
                      {activeControl.Control_type}
                    </span>
                  )}
                </div>

                {canEdit && (
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      size="icon"
                      variant="outline"
                      className="w-8 h-8 rounded border-border bg-background hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all"
                      onClick={() => onEdit?.(activeControl)}
                      title="Edit Control"
                    >
                      <Icon name="edit" size="14px" />
                    </Button>
                    <Button
                      size="icon"
                      variant="outline"
                      className="w-8 h-8 rounded border-border bg-background hover:bg-red-500 hover:text-white hover:border-red-500 transition-all"
                      onClick={() => onDelete?.(activeControl)}
                      title="Delete Control"
                    >
                      <Icon name="trash" size="14px" />
                    </Button>
                  </div>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-5">
              {/* Description */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Icon
                    name="document"
                    size="16px"
                    className="text-secondary"
                  />
                  <h3 className="text-sm font-bold uppercase tracking-wide">
                    Description
                  </h3>
                </div>
                <div className="bg-muted/40 p-2 rounded border border-border/50">
                  <p className="text-sm text-foreground/90 leading-relaxed">
                    {activeControl.Control_description ||
                      "No description provided."}
                  </p>
                </div>
              </div>

              {/* Deployment Points */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Icon
                    name="check-circle"
                    size="16px"
                    className="text-green-500"
                  />
                  <h3 className="text-sm font-bold uppercase tracking-wide flex items-center gap-2">
                    Deployment Points{" "}
                    <span className="bg-green-500/20 text-green-600 text-[10px] px-2 py-0.5 rounded">
                      {points.length}
                    </span>
                  </h3>
                </div>

                <div className="space-y-3">
                  {points.length === 0 ? (
                    <p className="text-sm text-muted-foreground italic pl-6">
                      No deployment points defined.
                    </p>
                  ) : (
                    points.map((point, i) => (
                      <div
                        key={i + 1}
                        className="flex gap-3 bg-card p-1 rounded border border-border hover:border-primary/30 hover:shadow-sm transition-all"
                      >
                        <div className="w-6 h-6 rounded bg-primary/10 text-primary flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                          {i + 1}
                        </div>
                        <p className="text-sm text-foreground/90 leading-relaxed">
                          {renderPointContent(point)}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
            <div className="w-16 h-16 rounded bg-muted flex items-center justify-center mb-4">
              <Icon
                name="document"
                size="24px"
                className="text-muted-foreground/50"
              />
            </div>
            <h3 className="text-lg font-semibold mb-2">No Control Selected</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Select a control from the list to view its description and
              deployment points.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DeploymentDocumentControlsPanel;
