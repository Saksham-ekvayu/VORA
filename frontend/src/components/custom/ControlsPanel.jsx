/* eslint-disable react/prop-types */
import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";
import { ControlModal } from "@/components/custom/modal";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDownIcon } from "lucide-react";
import { toast } from "sonner";
import { capitalizeFirst } from "@/utils/commonUtils";

/**
 * Helper to determine the target section and control IDs to select.
 */
function getTargetSelection(
  sections,
  activeSectionId,
  activeControlId,
  prevActiveSectionId,
  prevActiveControlId
) {
  if (!sections || sections.length === 0) {
    return { targetSectionId: null, targetControlId: null };
  }

  const isValidSection =
    activeSectionId && sections.some((s) => s._uiKey === activeSectionId);
  const sectionWasDeleted =
    !isValidSection && activeSectionId === prevActiveSectionId;
  const targetSectionId = sectionWasDeleted
    ? sections[0]._uiKey
    : activeSectionId || sections[0]._uiKey;

  const targetSection = sections.find((s) => s._uiKey === targetSectionId);
  const controls = targetSection?.controls ?? [];

  const isValidControl =
    activeControlId && controls.some((c) => c._uiKey === activeControlId);
  const controlWasDeleted =
    !isValidControl && activeControlId === prevActiveControlId;

  let targetControlId = activeControlId;
  if (controlWasDeleted) {
    targetControlId = controls.length > 0 ? controls[0]._uiKey : null;
  }

  return { targetSectionId, targetControlId };
}

const LeftPanelSections = ({
  filteredSections,
  resolvedSectionId,
  setActiveSectionId,
  totalSections,
  sections,
  totalControls,
}) => {
  return (
    <div className="lg:col-span-3 flex flex-col rounded border border-border bg-card shadow-sm overflow-hidden h-full">
      <div className="p-3 border-b border-border bg-primary/5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Icon name="folder" size="18px" className="text-primary" />
            <h3 className="font-bold text-foreground">Sections</h3>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-primary/15 text-primary">
              {totalSections || sections.length}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-foreground">Controls</p>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-primary/15 text-primary">
              {totalControls}
            </span>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1 w-full">
        {filteredSections.length > 0 && (
          <div className="sticky top-0 bg-muted/80 backdrop-blur z-10 px-3 py-1.5 border-b border-border flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
            <div className="w-10 shrink-0">ID</div>
            <div className="flex-1">Section Name</div>
            <div className="w-6 shrink-0"></div>
          </div>
        )}
        <div className="p-2 space-y-1">
          {filteredSections.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              No sections found.
            </div>
          ) : (
            filteredSections.map((section) => (
              <button
                type="button"
                key={section._uiKey}
                onClick={() => setActiveSectionId(section._uiKey)}
                className={`w-full text-left p-2 rounded border transition-all duration-200 group flex items-start gap-3 cursor-pointer ${
                  resolvedSectionId === section._uiKey
                    ? "bg-primary/10 border-primary"
                    : "bg-muted/80 border-transparent hover:border-border"
                }`}
              >
                <div className="w-fit shrink-0">
                  <span
                    className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded inline-block whitespace-nowrap ${
                      resolvedSectionId === section._uiKey
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary"
                    }`}
                  >
                    {section.id}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <h4
                    className={`font-semibold text-xs leading-relaxed mt-0.5 ${
                      resolvedSectionId === section._uiKey
                        ? "text-primary"
                        : "text-foreground group-hover:text-primary transition-colors"
                    }`}
                  >
                    {capitalizeFirst(section.name)}
                  </h4>
                </div>
                <div className="w-6 shrink-0 flex justify-end">
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                      resolvedSectionId === section._uiKey
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary transition-colors"
                    }`}
                  >
                    {section.controls?.length ?? 0}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

const ControlDetailsPanel = ({
  activeControl,
  isNAActive,
  showApplicability,
  canModify,
  handleMarkApplicable,
  onUpdateControlApplicability,
  setNotApplicableIds,
  setSelectedIds,
  controlWeightages,
  handleWeightageChange,
  onEdit,
  onDelete,
  deploymentPoints,
  frameworkApprovalStatus,
  isCustomControl,
  setShowAddModal,
  activeSection,
  globalSearch,
}) => {
  return (
    <div className="lg:col-span-5 flex flex-col rounded border border-border bg-card shadow-sm overflow-hidden h-full">
      {activeControl ? (
        <>
          <div
            className={`p-3 border-b border-border relative ${
              isNAActive
                ? "bg-orange-50/60 dark:bg-orange-950/20"
                : "bg-linear-to-r from-primary/10 to-transparent"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-sm font-bold px-2 py-0.5 rounded bg-primary text-primary-foreground shrink-0">
                    {activeControl.id}
                  </span>
                  <h2 className="text-sm font-bold text-foreground leading-tight">
                    {capitalizeFirst(activeControl.name)}
                  </h2>
                  {showApplicability && isNAActive && (
                    <span className="text-[9px] font-bold px-1 py-0.3 rounded bg-orange-100 text-orange-600 dark:bg-orange-950 dark:text-orange-400 uppercase border border-orange-300 dark:border-orange-700 shrink-0">
                      NOT APPLICABLE
                    </span>
                  )}
                  {isCustomControl && (
                    <span className="inline-block ml-1.5 text-[9px] font-bold px-1 py-0.3 rounded bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-400 uppercase align-middle whitespace-nowrap">
                      Org. Specific
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-2">
                  {showApplicability && canModify && (
                    <div className="">
                      {isNAActive ? (
                        <Button
                          size="xs"
                          variant="outline"
                          className="border-green-500 text-green-600 hover:bg-green-50 hover:text-green-700 dark:hover:bg-green-950 font-medium w-fit justify-center"
                          onClick={() =>
                            handleMarkApplicable(
                              activeControl._uiKey,
                              activeControl.id
                            )
                          }
                        >
                          <Icon
                            name="check-circle"
                            size="12px"
                            className="mr-1"
                          />
                          Mark Applicable
                        </Button>
                      ) : (
                        <Button
                          size="xs"
                          variant="outline"
                          className="border-orange-400 text-orange-500 hover:bg-orange-50 hover:text-orange-600 dark:hover:bg-orange-950 font-medium w-fit justify-center"
                          onClick={async () => {
                            setNotApplicableIds((prev) => {
                              const next = new Set(prev);
                              next.add(activeControl._uiKey);
                              return next;
                            });
                            setSelectedIds((prev) => {
                              const next = new Set(prev);
                              next.delete(activeControl._uiKey);
                              return next;
                            });
                            if (onUpdateControlApplicability) {
                              await onUpdateControlApplicability(
                                [activeControl.id],
                                false
                              );
                            } else {
                              toast.success(
                                "Control marked as not applicable."
                              );
                            }
                          }}
                        >
                          <Icon name="x-circle" size="12px" className="mr-1" />
                          Mark Not Applicable
                        </Button>
                      )}
                    </div>
                  )}

                  {canModify && (
                    <div className="flex items-center gap-1 shrink-0">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="outline"
                            size="xs"
                            className="w-fit justify-between text-xs font-semibold px-2"
                            disabled={showApplicability && isNAActive}
                          >
                            Weightage:{" "}
                            {controlWeightages[activeControl._uiKey] ?? 0}
                            <ChevronDownIcon className="size-3 opacity-50 ml-1" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start" className=" p-2">
                          <DropdownMenuLabel className="text-[10px] py-1 px-2">
                            Select Weightage
                          </DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <div className="grid grid-cols-5 gap-2">
                            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                              <button
                                key={num}
                                type="button"
                                onClick={() =>
                                  handleWeightageChange(activeControl, num)
                                }
                                className={`
                                  h-8 w-8 rounded text-sm font-semibold transition-all
                                  flex items-center justify-center cursor-pointer
                                  ${
                                    controlWeightages[activeControl._uiKey] ===
                                    num
                                      ? "bg-primary text-primary-foreground shadow-sm ring-2 ring-primary ring-offset-1"
                                      : "bg-muted hover:bg-muted/80 text-foreground hover:ring-1 hover:ring-border"
                                  }
                                `}
                              >
                                {num}
                              </button>
                            ))}
                          </div>
                        </DropdownMenuContent>
                      </DropdownMenu>

                      <Button
                        size="xs"
                        variant="default"
                        onClick={() => setShowAddModal(true)}
                        title="Add Control"
                      >
                        <Icon name="plus" size="14px" />
                      </Button>

                      {/* For assigned page, only custom controls can be edited/deleted */}
                      {(!showApplicability || isCustomControl) && (
                        <>
                          <Button
                            size="xs"
                            variant="outline"
                            onClick={() => onEdit?.(activeControl)}
                            title="Edit Control"
                            disabled={showApplicability && isNAActive}
                          >
                            <Icon name="edit" size="14px" />
                          </Button>
                          <Button
                            size="xs"
                            variant="destructive"
                            onClick={() => onDelete?.(activeControl)}
                            title="Delete Control"
                            disabled={showApplicability && isNAActive}
                          >
                            <Icon name="trash" size="14px" />
                          </Button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {(!canModify || frameworkApprovalStatus === "approved") && (
                <span className="text-xs font-medium text-foreground">
                  Weightage: {controlWeightages[activeControl._uiKey] ?? 0}
                </span>
              )}
            </div>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-4 space-y-5">
              {/* Description */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Icon
                    name="document"
                    size="16px"
                    className="text-secondary"
                  />
                  <h3 className="text-xs font-bold uppercase tracking-wide">
                    Description
                  </h3>
                </div>
                <div className="bg-muted/40 p-3 rounded border border-border/50">
                  <p className="text-xs text-foreground/90 leading-relaxed text-justify">
                    {activeControl.description || "No description provided."}
                  </p>
                </div>
              </div>

              {/* Deployment Points */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Icon
                    name="check-circle"
                    size="16px"
                    className="text-green-500"
                  />
                  <h3 className="text-xs font-bold uppercase tracking-wide flex items-center gap-2">
                    Deployment Points{" "}
                    <span className="bg-green-500/20 text-green-600 text-[10px] px-2 py-0.5 rounded">
                      {deploymentPoints.length}
                    </span>
                  </h3>
                </div>

                {deploymentPoints.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic pl-2">
                    No deployment points defined.
                  </p>
                ) : (
                  <div className="space-y-1.5">
                    {deploymentPoints
                      .filter((point) => {
                        if (!globalSearch?.trim()) return true;
                        const q = globalSearch.toLowerCase().trim();

                        // If the active control name/ID matches, or active section matches, show all DPs
                        if (
                          activeControl?.name?.toLowerCase().includes(q) ||
                          activeControl?.id?.toLowerCase().includes(q) ||
                          activeSection?.name?.toLowerCase().includes(q) ||
                          activeSection?.id?.toLowerCase().includes(q)
                        ) {
                          return true;
                        }

                        const text =
                          typeof point === "string"
                            ? point.trim()
                            : point?.name || point?.point || "";
                        return text.toLowerCase().includes(q);
                      })
                      .map((point, i) => (
                        <div
                          key={point.id ?? i}
                          className="bg-card rounded border border-border hover:border-primary/30 hover:shadow-sm transition-all"
                        >
                          <div className="flex gap-2 p-2">
                            <div className="w-5 h-5 rounded bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                              {i + 1}
                            </div>
                            <p className="text-xs text-foreground/90 leading-relaxed text-justify">
                              {typeof point === "string"
                                ? point.trim()
                                : point?.name || point?.point}
                            </p>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          </ScrollArea>
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
          {activeSection && (activeSection.controls ?? []).length === 0 ? (
            <>
              <h3 className="text-lg font-semibold mb-2">
                No Controls in Section
              </h3>
              <p className="text-sm text-muted-foreground max-w-sm mb-4">
                This section doesn't have any controls yet. Add a new control to
                get started.
              </p>
              {canModify && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <Icon name="plus" size="14px" />
                  Add Control
                </Button>
              )}
            </>
          ) : (
            <>
              <h3 className="text-lg font-semibold mb-2">
                No Control Selected
              </h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Select a control from the middle panel to view its details and
                deployment points.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default function ControlsPanel({
  sections: propSections = [],
  totalSections = 0,
  totalControls = 0,
  canModify = false,
  onEdit,
  onDelete,
  onAdd,
  onUpdateWeightage,
  // Applicability features
  showApplicability = false,
  onUpdateControlApplicability,
  // Page specific flags
  showOrgSpecificBadge = false,
  isDeploymentFramework = false,
  frameworkApprovalStatus = "",
  globalSearch = "",
}) {
  const [searchParams, setSearchParams] = useSearchParams();

  const activeSectionId = searchParams.get("section");
  const activeControlId = searchParams.get("control");

  // Track applicability and weightages locally for responsive UI
  const [notApplicableIds, setNotApplicableIds] = useState(new Set());
  const [controlWeightages, setControlWeightages] = useState({});
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showAddModal, setShowAddModal] = useState(false);

  const sections = useMemo(() => {
    return propSections.map((s, sIdx) => ({
      ...s,
      _uiKey: s._uiKey || `${s.id}-${sIdx}`,
      controls: (s.controls || []).map((c, cIdx) => ({
        ...c,
        _uiKey: c._uiKey || `${c.id}-${sIdx}-${cIdx}`,
      })),
    }));
  }, [propSections]);

  // Sync initial applicability and weightage values from incoming sections data
  const initialData = useMemo(() => {
    const naSet = new Set();
    const weightages = {};
    sections.forEach((sect) => {
      (sect.controls || []).forEach((ctrl) => {
        if (
          ctrl.customization?.is_applicable === false ||
          ctrl.is_applicable === false
        ) {
          naSet.add(ctrl._uiKey);
        }
        let cw =
          ctrl.customization?.weightage?.customer_weightage ?? ctrl.weightage;

        if (cw === undefined || cw === null) {
          if (ctrl.deployment_points && ctrl.deployment_points.length > 0) {
            const total = ctrl.deployment_points.reduce(
              (sum, dp) => sum + (dp.weightage || 0),
              0
            );
            cw = Math.round(total / ctrl.deployment_points.length);
          } else {
            cw = 0;
          }
        }

        weightages[ctrl._uiKey] = cw;
      });
    });
    return { naSet, weightages };
  }, [sections]);

  useEffect(() => {
    setNotApplicableIds(initialData.naSet);
    setControlWeightages(initialData.weightages);
  }, [initialData]);

  const updateActiveSelection = useCallback(
    (sectId, ctrlId) => {
      setSearchParams((prev) => {
        const nextParams = new URLSearchParams(prev);
        if (sectId !== undefined) {
          if (sectId) {
            nextParams.set("section", sectId);
          } else {
            nextParams.delete("section");
          }
        }
        if (ctrlId !== undefined) {
          if (ctrlId) {
            nextParams.set("control", ctrlId);
          } else {
            nextParams.delete("control");
          }
        }
        return nextParams;
      });
    },
    [setSearchParams]
  );

  const setActiveSectionId = (id) => updateActiveSelection(id, null);
  const setActiveControlId = (id) => updateActiveSelection(undefined, id);

  const prevActiveSectionIdRef = useRef(activeSectionId);
  const prevActiveControlIdRef = useRef(activeControlId);

  const prevActiveSectionId = prevActiveSectionIdRef.current;
  const prevActiveControlId = prevActiveControlIdRef.current;

  // Keep selection synchronized with URL query parameters
  useEffect(() => {
    const { targetSectionId, targetControlId } = getTargetSelection(
      sections,
      activeSectionId,
      activeControlId,
      prevActiveSectionId,
      prevActiveControlId
    );

    if (
      activeSectionId !== targetSectionId ||
      activeControlId !== targetControlId
    ) {
      updateActiveSelection(targetSectionId, targetControlId);
    }

    prevActiveSectionIdRef.current = activeSectionId;
    prevActiveControlIdRef.current = activeControlId;
  }, [
    sections,
    activeSectionId,
    activeControlId,
    prevActiveSectionId,
    prevActiveControlId,
    updateActiveSelection,
  ]);

  // Filter sections by search query
  const filteredSections = useMemo(() => {
    if (!globalSearch?.trim()) return sections;
    const q = globalSearch.toLowerCase().trim();

    return sections.filter((s) => {
      if (
        s?.name?.toLowerCase().includes(q) ||
        s?.id?.toLowerCase().includes(q)
      )
        return true;

      return (s?.controls || []).some((c) => {
        if (
          c?.name?.toLowerCase().includes(q) ||
          c?.id?.toLowerCase().includes(q)
        )
          return true;

        let dps = [];
        if (c?.deployment_points) {
          if (Array.isArray(c.deployment_points)) {
            dps = c.deployment_points;
          } else if (typeof c.deployment_points === "string") {
            dps = c.deployment_points
              .split(/^\d+\.\s+/m)
              .filter((p) => p.trim());
          }
        }
        return dps.some((dp) => {
          const text =
            typeof dp === "string" ? dp : dp?.point || dp?.name || "";
          return text.toLowerCase().includes(q);
        });
      });
    });
  }, [sections, globalSearch]);

  // Resolve active section — default to first
  const resolvedSectionId = useMemo(() => {
    if (filteredSections.length === 0) return null;
    if (
      activeSectionId &&
      filteredSections.some((s) => s._uiKey === activeSectionId)
    )
      return activeSectionId;
    return filteredSections[0]._uiKey;
  }, [filteredSections, activeSectionId]);

  const activeSection = useMemo(
    () => filteredSections.find((s) => s._uiKey === resolvedSectionId) ?? null,
    [filteredSections, resolvedSectionId]
  );

  // Filter controls within active section by search query
  const filteredControls = useMemo(() => {
    const list = activeSection?.controls ?? [];
    if (!globalSearch?.trim()) return list;
    const q = globalSearch.toLowerCase().trim();

    // If the active section itself matches the search query, show all its controls!
    if (
      activeSection?.name?.toLowerCase().includes(q) ||
      activeSection?.id?.toLowerCase().includes(q)
    ) {
      return list;
    }

    return list.filter((c) => {
      if (
        c?.name?.toLowerCase().includes(q) ||
        c?.id?.toLowerCase().includes(q)
      )
        return true;

      let dps = [];
      if (c?.deployment_points) {
        if (Array.isArray(c.deployment_points)) {
          dps = c.deployment_points;
        } else if (typeof c.deployment_points === "string") {
          dps = c.deployment_points.split(/^\d+\.\s+/m).filter((p) => p.trim());
        }
      }
      return dps.some((dp) => {
        const text = typeof dp === "string" ? dp : dp?.point || dp?.name || "";
        return text.toLowerCase().includes(q);
      });
    });
  }, [activeSection, globalSearch]);

  // Resolve active control — default to first
  const resolvedControlId = useMemo(() => {
    if (filteredControls.length === 0) return null;
    if (
      activeControlId &&
      filteredControls.some((c) => c._uiKey === activeControlId)
    )
      return activeControlId;
    return filteredControls[0]._uiKey;
  }, [filteredControls, activeControlId]);

  const activeControl = useMemo(
    () => filteredControls.find((c) => c._uiKey === resolvedControlId) ?? null,
    [filteredControls, resolvedControlId]
  );

  const deploymentPoints = useMemo(() => {
    if (!activeControl?.deployment_points) return [];
    if (Array.isArray(activeControl.deployment_points)) {
      return activeControl.deployment_points;
    }
    if (typeof activeControl.deployment_points === "string") {
      return activeControl.deployment_points
        .split(/^\d+\.\s+/m)
        .filter((point) => point.trim());
    }
    return [];
  }, [activeControl]);

  // Toggle single checkbox selection
  const handleToggleSelect = (e, controlId) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(controlId) ? next.delete(controlId) : next.add(controlId);
      return next;
    });
  };

  const selectableControls = filteredControls.filter(
    (c) => !notApplicableIds.has(c._uiKey)
  );

  const allSelected =
    selectableControls.length > 0 &&
    selectableControls.every((c) => selectedIds.has(c._uiKey));

  const handleToggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(selectableControls.map((c) => c._uiKey)));
    }
  };

  const handleMarkMultipleApplicable = async () => {
    if (selectedIds.size === 0) {
      toast.warning("Please select at least one control first.");
      return;
    }
    setNotApplicableIds((prev) => {
      const next = new Set(prev);
      selectedIds.forEach((id) => next.delete(id));
      return next;
    });

    if (onUpdateControlApplicability) {
      const actualIds = Array.from(selectedIds)
        .map((uiKey) => {
          for (const s of sections) {
            const ctrl = s.controls?.find((c) => c._uiKey === uiKey);
            if (ctrl) return ctrl.id;
          }
          return null;
        })
        .filter(Boolean);
      await onUpdateControlApplicability(actualIds, true);
    } else {
      toast.success("Controls marked as applicable.");
    }
    setSelectedIds(new Set());
  };

  const handleMarkNotApplicable = async () => {
    if (selectedIds.size === 0) {
      toast.warning("Please select at least one control first.");
      return;
    }
    setNotApplicableIds((prev) => {
      const next = new Set(prev);
      selectedIds.forEach((id) => next.add(id));
      return next;
    });

    if (onUpdateControlApplicability) {
      const actualIds = Array.from(selectedIds)
        .map((uiKey) => {
          for (const s of sections) {
            const ctrl = s.controls?.find((c) => c._uiKey === uiKey);
            if (ctrl) return ctrl.id;
          }
          return null;
        })
        .filter(Boolean);
      await onUpdateControlApplicability(actualIds, false);
    } else {
      toast.success("Controls marked as not applicable.");
    }
    setSelectedIds(new Set());
  };

  const handleMarkApplicable = async (controlUiKey, controlId) => {
    setNotApplicableIds((prev) => {
      const next = new Set(prev);
      next.delete(controlUiKey);
      return next;
    });
    if (onUpdateControlApplicability) {
      await onUpdateControlApplicability([controlId], true);
    } else {
      toast.success("Control has been marked as applicable.");
    }
  };

  const handleWeightageChange = (control, value) => {
    setControlWeightages((prev) => ({
      ...prev,
      [control._uiKey]: value,
    }));
    onUpdateWeightage?.(control, value);
  };

  const selectedCount = filteredControls.filter((c) =>
    selectedIds.has(c._uiKey)
  ).length;

  const isCustomControl =
    activeControl?.customization?.source === "custom" ||
    activeControl?.source === "custom";
  const isNAActive = activeControl
    ? notApplicableIds.has(activeControl._uiKey)
    : false;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-140 bg-background">
      {/* LEFT PANEL: SECTIONS */}
      <LeftPanelSections
        filteredSections={filteredSections}
        resolvedSectionId={resolvedSectionId}
        setActiveSectionId={setActiveSectionId}
        isDeploymentFramework={isDeploymentFramework}
        totalSections={totalSections}
        sections={sections}
        totalControls={totalControls}
      />

      {/* MIDDLE PANEL: CONTROLS */}
      <div className="lg:col-span-4 flex flex-col rounded border border-border bg-card shadow-sm overflow-hidden h-full">
        <div className="p-3 border-b border-border bg-primary/5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 min-w-0">
              <Icon
                name="document"
                size="18px"
                className="text-primary shrink-0"
              />
              <h3 className="font-bold text-foreground truncate">
                {activeSection?.name ?? "—"}
              </h3>
            </div>
            <div className="flex items-center gap-1.5 shrink-0 ml-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-primary/15 text-primary whitespace-nowrap">
                {filteredControls.length} Controls
              </span>
              {showApplicability && canModify && selectedCount > 0 && (
                <div className="flex items-center gap-1.5">
                  <Button
                    size="xs"
                    variant="outline"
                    className="whitespace-nowrap border-green-500 text-green-600 hover:bg-green-50 hover:text-green-700 dark:hover:bg-green-950"
                    onClick={handleMarkMultipleApplicable}
                    title="Mark selected controls as Applicable"
                  >
                    <Icon name="check-circle" size="12px" className="mr-1" />
                    Applicable
                    <span className="ml-1 bg-green-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                      {selectedCount}
                    </span>
                  </Button>
                  <Button
                    size="xs"
                    variant="outline"
                    className="whitespace-nowrap border-orange-400 text-orange-500 hover:bg-orange-50 hover:text-orange-600 dark:hover:bg-orange-950"
                    onClick={handleMarkNotApplicable}
                    title="Mark selected controls as Not Applicable"
                  >
                    <Icon name="x-circle" size="12px" className="mr-1" />
                    Not Applicable
                    <span className="ml-1 bg-orange-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                      {selectedCount}
                    </span>
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>

        <ScrollArea className="flex-1 w-full">
          {filteredControls.length === 0 ? (
            <div className="text-center py-8 px-4 flex flex-col items-center justify-center gap-3">
              <p className="text-sm text-muted-foreground">
                No controls found.
              </p>
              {canModify && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <Icon name="plus" size="14px" />
                  Add Control
                </Button>
              )}
            </div>
          ) : (
            <div className="w-full">
              <div className="sticky top-0 bg-muted/80 backdrop-blur z-10 px-3 py-1.5 border-b border-border grid grid-cols-12 gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                {showApplicability && canModify && (
                  <div className="col-span-1 flex items-center">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={handleToggleSelectAll}
                      className="h-3.5 w-3.5 rounded border-border accent-primary cursor-pointer"
                      title="Select all"
                    />
                  </div>
                )}
                <div className="col-span-2">ID</div>
                <div
                  className={
                    showApplicability && canModify
                      ? "col-span-9"
                      : "col-span-10"
                  }
                >
                  Control Name
                </div>
              </div>
              <div className="divide-y divide-border">
                {filteredControls.map((control) => {
                  const isNA = notApplicableIds.has(control._uiKey);
                  const isSelected = selectedIds.has(control._uiKey);
                  const isActive = resolvedControlId === control._uiKey;
                  const isCustom =
                    control.customization?.source === "custom" ||
                    control.source === "custom";

                  let rowBg = "hover:bg-muted";
                  if (isNA) {
                    rowBg = "bg-muted/40";
                  } else if (isActive) {
                    rowBg = "bg-primary/10";
                  }

                  return (
                    <button
                      key={control._uiKey}
                      type="button"
                      onClick={() => setActiveControlId(control._uiKey)}
                      className={`w-full text-left px-3 py-2 grid grid-cols-12 gap-2 items-center transition-colors cursor-pointer ${rowBg}`}
                    >
                      {showApplicability && canModify && (
                        <div className="col-span-1 flex items-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              if (!isNA) {
                                handleToggleSelect(e, control._uiKey);
                              }
                            }}
                            onClick={(e) => e.stopPropagation()}
                            disabled={isNA}
                            className="h-3.5 w-3.5 rounded border-border accent-primary cursor-pointer disabled:cursor-not-allowed"
                          />
                        </div>
                      )}

                      <div className="col-span-2">
                        <span
                          className={`text-xs font-semibold px-2 py-1 rounded inline-block ${
                            isActive
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {control.id}
                        </span>
                      </div>
                      <div
                        className={`${showApplicability && canModify ? "col-span-9" : "col-span-10"} text-xs font-medium pr-2 ${
                          isActive ? "text-primary" : "text-foreground"
                        }`}
                      >
                        <span
                          className={
                            isNA
                              ? "line-through decoration-orange-500 text-muted-foreground"
                              : ""
                          }
                        >
                          {capitalizeFirst(control.name)}
                        </span>
                        {isNA && (
                          <span className="inline-block ml-1.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-orange-100 text-orange-600 dark:bg-orange-950 dark:text-orange-400 uppercase align-middle whitespace-nowrap">
                            N/A
                          </span>
                        )}
                        {showOrgSpecificBadge && isCustom && (
                          <span className="inline-block ml-1.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-400 uppercase align-middle whitespace-nowrap">
                            Org. Specific
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </ScrollArea>
      </div>

      {/* RIGHT PANEL: DETAILS */}
      <ControlDetailsPanel
        activeControl={activeControl}
        isNAActive={isNAActive}
        showApplicability={showApplicability}
        canModify={canModify}
        handleMarkApplicable={handleMarkApplicable}
        onUpdateControlApplicability={onUpdateControlApplicability}
        setNotApplicableIds={setNotApplicableIds}
        setSelectedIds={setSelectedIds}
        controlWeightages={controlWeightages}
        handleWeightageChange={handleWeightageChange}
        onEdit={onEdit}
        onDelete={onDelete}
        deploymentPoints={deploymentPoints}
        frameworkApprovalStatus={frameworkApprovalStatus}
        isCustomControl={isCustomControl}
        setShowAddModal={setShowAddModal}
        activeSection={activeSection}
        globalSearch={globalSearch}
      />

      {/* ADD CONTROL MODAL */}
      {showAddModal && (
        <ControlModal
          type="add"
          open={showAddModal}
          sections={sections}
          onSave={async (newControl) => {
            const res = await onAdd?.(newControl);
            if (res?.success && res?.data) {
              const { sectionId, control } = res.data;
              if (sectionId || control?.id) {
                updateActiveSelection(sectionId, control?.id);
              }
            }
            setShowAddModal(false);
          }}
          onCancel={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
}
