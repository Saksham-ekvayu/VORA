/* eslint-disable react/prop-types */
import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import SearchInput from "@/components/custom/SearchInput";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { CheckIcon, ChevronDownIcon, FilterIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getDeploymentFrameworkClientControls,
  updateDeploymentPointPath,
} from "@/services/deploymentFrameworkService";
import { toast } from "sonner";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import { capitalizeFirst } from "@/utils/commonUtils";

// ─── Pure helpers ─────────────────────────────────────────────────────────────

/**
 * Flatten all documents' sections into a single list.
 * Sections are kept as-is per document — no merging by id,
 * because different documents can have the same section ids.
 * A stable unique key (docIndex + section.id) is added for React rendering.
 */
function normalizePoint(point) {
  return {
    ...point,
    path: point?.path ?? "",
    source: point?.source ?? "",
  };
}

function normalizeControl(control) {
  return {
    ...control,
    dps: (control?.deployment_points ?? control?.dps ?? []).map(normalizePoint),
  };
}

function normalizeSection(section, sectionIndex = 0) {
  return {
    ...section,
    _key: `${sectionIndex}-${section?.id ?? section?.name}`,
    controls: (section?.controls ?? []).map(normalizeControl),
  };
}

function normalizeFramework(framework) {
  const sections =
    framework?.controls ??
    framework?.package?.documents?.flatMap((doc) => doc.sections ?? []) ??
    [];

  return {
    ...framework,
    id: framework?.frameworkId ?? framework?.id,
    sections: sections.map(normalizeSection),
    package: {
      ...framework?.package,
      packageVersion:
        framework?.packageVersion ?? framework?.package?.packageVersion ?? null,
    },
  };
}

function normalizeClientControlsResponse(data = []) {
  return data.map(normalizeFramework);
}

function extractInitialSelection(data, targetFwId) {
  let firstFw = data[0] ?? null;
  if (targetFwId) {
    const found = data.find((f) => f.id === targetFwId);
    if (found) firstFw = found;
  }
  const sections = firstFw?.sections ?? [];
  const firstSection = sections[0] ?? null;
  const firstControl = firstSection?.controls?.[0] ?? null;
  return { firstFw, firstSection, firstControl };
}

function getPathKey(frameworkId, sectionKey, controlId, dpId) {
  return `${frameworkId}-${sectionKey}-${controlId}-${dpId}`;
}

function collectDpPaths(ctrl, accPaths, accSources, frameworkId, sectionKey) {
  for (const dp of ctrl?.dps ?? []) {
    const key = getPathKey(frameworkId, sectionKey, ctrl.id, dp.id);
    if (dp.path) accPaths[key] = dp.path;
    if (dp.source) accSources[key] = dp.source;
  }
}

function collectSectionPaths(section, accPaths, accSources, frameworkId) {
  for (const ctrl of section?.controls ?? [])
    collectDpPaths(ctrl, accPaths, accSources, frameworkId, section._key);
}

function buildSavedPaths(data) {
  const savedPaths = {};
  const savedSources = {};
  for (const fw of data) {
    for (const section of fw?.sections ?? [])
      collectSectionPaths(section, savedPaths, savedSources, fw.id);
  }
  return { savedPaths, savedSources };
}

// ─── Column Panel ─────────────────────────────────────────────────────────────

function ColPanel({ title, badge, children, className = "" }) {
  return (
    <Card
      className={`flex flex-col h-full rounded border border-border bg-linear-to-br from-background to-card overflow-hidden gap-0 py-0 shadow-sm ${className}`}
    >
      <CardHeader className="flex flex-row items-center justify-between border-b border-border px-3 py-2 pb-2! shrink-0">
        <CardTitle className="text-xs font-semibold text-foreground">
          {title}
        </CardTitle>
        {badge !== undefined && (
          <Badge
            variant="default"
            className="w-4 h-4 p-0 flex items-center justify-center text-[9px] font-bold"
          >
            {badge}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-2 space-y-1">{children}</div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// ─── Shared Components ────────────────────────────────────────────────────────

const FILTER_OPTIONS = [
  { label: "All Points", value: "all" },
  { label: "Configured", value: "configured" },
  { label: "Unconfigured", value: "unconfigured" },
];

function FilterDropdown({ value, onChange, counts }) {
  const [open, setOpen] = useState(false);
  const selectedOption =
    FILTER_OPTIONS.find((opt) => opt.value === value) || FILTER_OPTIONS[0];

  const handleSelect = (val) => {
    onChange(val);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "relative flex items-center gap-2 text-xs font-medium justify-between h-9",
            "border-border bg-accent hover:border-primary hover:bg-primary/10",
            open && "border-primary bg-primary/10"
          )}
        >
          <div className="flex items-center gap-1.5 min-w-0">
            <FilterIcon className="size-4 text-primary shrink-0" />
            <span className="truncate">{selectedOption.label}</span>
          </div>
          <ChevronDownIcon className="size-3.5 text-muted-foreground shrink-0 ml-1" />
          {counts && (
            <span className="absolute -top-2 -right-2 bg-primary text-primary-foreground text-[10px] font-bold px-1.5 py-0.5 rounded-full shadow-sm leading-none border border-background">
              {counts[value]}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-36 p-1 shadow-2xl"
      >
        <div className="space-y-0.5">
          {FILTER_OPTIONS.map((opt) => {
            const active = value === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleSelect(opt.value)}
                className={cn(
                  "w-full flex items-center justify-between rounded px-2 py-2 text-xs text-left transition-colors cursor-pointer",
                  active
                    ? "bg-primary/15 text-primary font-medium"
                    : "text-foreground hover:bg-accent"
                )}
              >
                <span className="font-medium">{opt.label}</span>
                {active && <CheckIcon className="size-3.5 shrink-0" />}
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ─── Framework Dropdown ───────────────────────────────────────────────────────
function FrameworkDropdown({ frameworks = [], selectedFw, onSelect }) {
  const [open, setOpen] = useState(false);

  const handleSelect = (fw) => {
    onSelect(fw);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "flex items-center gap-2 text-xs font-medium max-w-65 justify-between h-9",
            "border-border bg-accent hover:border-primary hover:bg-primary/10",
            open && "border-primary bg-primary/10"
          )}
        >
          <div className="flex items-center gap-1.5 min-w-0">
            <Icon
              name="framework"
              size="20px"
              className="text-primary shrink-0"
            />
            <div className="flex flex-col items-start min-w-0">
              <span className="truncate max-w-45 leading-tight">
                {selectedFw ? selectedFw.frameworkName : "Select Framework"}
              </span>
              {selectedFw?.frameworkVersion && (
                <span className="text-2.5 text-muted-foreground leading-tight">
                  {selectedFw.frameworkVersion}
                </span>
              )}
            </div>
          </div>
          <ChevronDownIcon className="size-3.5 text-muted-foreground shrink-0 ml-1" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-auto min-w-65 p-1 shadow-2xl"
      >
        <div className="space-y-0.5">
          {frameworks.map((fw) => {
            const active = selectedFw?.id === fw.id;
            return (
              <button
                key={fw.id}
                type="button"
                onClick={() => handleSelect(fw)}
                className={cn(
                  "w-full flex items-center justify-between rounded px-2 py-2 text-xs text-left transition-colors cursor-pointer",
                  active
                    ? "bg-primary/15 text-primary font-medium"
                    : "text-foreground hover:bg-accent"
                )}
              >
                <div className="flex flex-col items-start pr-4">
                  <span className="font-medium whitespace-nowrap">
                    {fw.frameworkName}
                  </span>
                  {fw.frameworkVersion && (
                    <span className="text-2.5 text-muted-foreground mt-0.5">
                      {fw.frameworkVersion}
                    </span>
                  )}
                </div>
                {active && <CheckIcon className="size-3.5 shrink-0" />}
              </button>
            );
          })}
          {frameworks.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-3">
              No frameworks available
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function MonitoringSetup() {
  usePageTitle("monitoring-setup", "Monitoring Setup");

  const [frameworks, setFrameworks] = useState([]);
  const [loading, setLoading] = useState(true);

  const [searchParams, setSearchParams] = useSearchParams();

  const [selectedFw, setSelectedFw] = useState(null);
  const [selectedSection, setSelectedSection] = useState(null);
  const [selectedControl, setSelectedControl] = useState(null);
  const [sectionSearch, setSectionSearch] = useState("");
  const [controlSearch, setControlSearch] = useState("");
  const [dpFilter, setDpFilter] = useState(searchParams.get("filter") || "all");
  const [paths, setPaths] = useState({});
  const [savedPaths, setSavedPaths] = useState({});
  const [sources, setSources] = useState({});
  const [savedSources, setSavedSources] = useState({});
  const [savingDp, setSavingDp] = useState(null);

  // ── Fetch ─────────────────────────────────────────────────────────────────
  const fetchClientControls = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getDeploymentFrameworkClientControls();
      if (!res.success || !Array.isArray(res.data)) return;

      const frameworksData = normalizeClientControlsResponse(res.data);
      const fwIdFromUrl = new URLSearchParams(globalThis.location.search).get(
        "frameworkId"
      );
      const { firstFw, firstSection, firstControl } = extractInitialSelection(
        frameworksData,
        fwIdFromUrl
      );

      setFrameworks(frameworksData);
      setSelectedFw(firstFw);
      setSelectedSection(firstSection);
      setSelectedControl(firstControl);
      const { savedPaths: sp, savedSources: ss } =
        buildSavedPaths(frameworksData);
      setPaths(sp);
      setSavedPaths(sp);
      setSources(ss);
      setSavedSources(ss);
    } catch (err) {
      toast.error(err.message || "Failed to load client controls");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClientControls();
  }, [fetchClientControls]);

  // Sync state to URL
  useEffect(() => {
    if (!selectedFw) return;
    setSearchParams(
      (prev) => {
        const currentFw = prev.get("frameworkId");
        const currentFilter = prev.get("filter") || "all";
        if (currentFw !== selectedFw.id || currentFilter !== dpFilter) {
          const next = new URLSearchParams(prev);
          next.set("frameworkId", selectedFw.id);
          if (dpFilter === "all") next.delete("filter");
          else next.set("filter", dpFilter);
          return next;
        }
        return prev;
      },
      { replace: true }
    );
  }, [selectedFw, dpFilter, setSearchParams]);

  // ── Derived data ──────────────────────────────────────────────────────────
  const sections = useMemo(
    () => selectedFw?.sections ?? [],
    [selectedFw?.sections]
  );
  const controls = useMemo(
    () => selectedSection?.controls ?? [],
    [selectedSection?.controls]
  );
  const points = useMemo(
    () => selectedControl?.dps ?? [],
    [selectedControl?.dps]
  );

  const dpCounts = useMemo(() => {
    let all = 0;
    let configured = 0;
    let unconfigured = 0;

    for (const s of sections) {
      for (const c of s.controls || []) {
        for (const dp of c.dps || []) {
          all++;
          const pathKey = getPathKey(selectedFw?.id, s._key, c.id, dp.id);
          const dpPath = savedPaths[pathKey] ?? "";
          if (dpPath.trim().length > 0) configured++;
          else unconfigured++;
        }
      }
    }
    return { all, configured, unconfigured };
  }, [sections, savedPaths, selectedFw?.id]);

  const getCurrentPathKey = (dpId) =>
    getPathKey(
      selectedFw?.id,
      selectedSection?._key,
      selectedControl?.id,
      dpId
    );
  const getPath = (dpId) => paths[getCurrentPathKey(dpId)] ?? "";
  const setPath = (dpId, val) =>
    setPaths((prev) => ({ ...prev, [getCurrentPathKey(dpId)]: val }));

  const getSource = (dpId) => sources[getCurrentPathKey(dpId)] ?? "";
  const setSource = (dpId, val) =>
    setSources((prev) => ({ ...prev, [getCurrentPathKey(dpId)]: val }));

  const pointMatches = (dp, sKey, c) => {
    const dpPath =
      savedPaths[getPathKey(selectedFw?.id, sKey, c.id, dp.id)] ?? "";
    const hasPath = dpPath.trim().length > 0;

    if (dpFilter === "configured" && !hasPath) return false;
    if (dpFilter === "unconfigured" && hasPath) return false;

    return true;
  };

  const sectionHasMatchingPoint = (s) => {
    if (dpFilter === "all") return true;
    return (s.controls || []).some((c) =>
      (c.dps || []).some((dp) => pointMatches(dp, s._key, c))
    );
  };

  const getMatchingControlsCount = (sec) => {
    if (dpFilter === "all") return sec.controls?.length ?? 0;
    return (sec.controls || []).filter((c) =>
      (c.dps || []).some((dp) => pointMatches(dp, sec._key, c))
    ).length;
  };

  const controlHasMatchingPoint = (c) => {
    if (dpFilter === "all") return true;
    return (c.dps || []).some((dp) =>
      pointMatches(dp, selectedSection?._key, c)
    );
  };

  const getMatchingDpCount = (ctrl) => {
    if (dpFilter === "all") return ctrl.dps?.length ?? 0;
    return (ctrl.dps || []).filter((dp) =>
      pointMatches(dp, selectedSection?._key, ctrl)
    ).length;
  };

  const filteredSections = sections.filter((s) => {
    const matchesName = s.name
      .toLowerCase()
      .includes(sectionSearch.toLowerCase());
    const matchesGlobal = sectionHasMatchingPoint(s);
    return matchesName && matchesGlobal;
  });

  const filteredControls = controls.filter((c) => {
    const matchesName =
      c.name.toLowerCase().includes(controlSearch.toLowerCase()) ||
      c.id.toLowerCase().includes(controlSearch.toLowerCase());
    const matchesGlobal = controlHasMatchingPoint(c);
    return matchesName && matchesGlobal;
  });

  const filteredPoints = points.filter((dp) =>
    pointMatches(dp, selectedSection?._key, selectedControl)
  );

  // ── Save path ─────────────────────────────────────────────────────────────
  const handleSavePath = useCallback(
    async (dpId) => {
      const pathKey = getPathKey(
        selectedFw.id,
        selectedSection._key,
        selectedControl.id,
        dpId
      );
      const pathVal = (paths[pathKey] ?? "").trim();
      const sourceVal = (sources[pathKey] ?? "").trim();

      if (!pathVal) {
        toast.error("Please enter a path before saving");
        return;
      }

      setSavingDp(pathKey);
      try {
        const res = await updateDeploymentPointPath(selectedFw.id, {
          packageVersion:
            selectedFw.packageVersion ?? selectedFw.package?.packageVersion,
          sectionId: selectedSection.id,
          controlId: selectedControl.id,
          pointId: dpId,
          path: pathVal,
          source: sourceVal,
        });

        if (res.success) {
          toast.success(res.message);
          setSavedPaths((prev) => ({ ...prev, [pathKey]: pathVal }));
          setSavedSources((prev) => ({ ...prev, [pathKey]: sourceVal }));
        }
      } catch (err) {
        console.error("Failed to save path:", err);
        toast.error(err.message);
      } finally {
        setSavingDp(null);
      }
    },
    [selectedFw, selectedSection, selectedControl, paths, sources]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-4 my-2">
      {/* Header */}
      <div className="border border-border rounded bg-card p-2 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-primary/10 flex items-center justify-center">
            <Icon name="settings" size="24px" className="text-primary" />
          </div>
          <div className="flex flex-col">
            <h2 className="text-sm font-semibold text-foreground">
              Monitoring Setup
            </h2>
            <p className="text-xs text-muted-foreground">
              Configure control monitoring paths. VORA&apos;s AI compliance
              engine uses these paths to automatically retrieve and verify
              evidence documents for automated audits.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Global DP Filter */}
          <FilterDropdown
            value={dpFilter}
            onChange={setDpFilter}
            counts={dpCounts}
          />

          {/* Framework selector dropdown */}
          <FrameworkDropdown
            frameworks={frameworks}
            selectedFw={selectedFw}
            onSelect={(fw) => {
              setSelectedFw(fw);
              const nextSection = fw.sections?.[0] ?? null;
              setSelectedSection(nextSection);
              setSelectedControl(nextSection?.controls?.[0] ?? null);
            }}
          />
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 h-[70vh]">
        {/* ── Col 1: Sections ───────────────────────────────────────────── */}
        <ColPanel
          title="Sections"
          badge={
            filteredSections.length > 0 ? filteredSections.length : undefined
          }
        >
          <div className="mb-1 shrink-0">
            <SearchInput
              placeholder="Search sections..."
              value={sectionSearch}
              onChange={setSectionSearch}
              onClear={() => setSectionSearch("")}
              className="bg-accent border-border focus-visible:ring-1"
            />
          </div>
          {filteredSections.map((sec) => (
            <button
              type="button"
              key={sec._key}
              onClick={() => {
                setSelectedSection(sec);
                setSelectedControl(sec.controls?.[0] ?? null);
              }}
              className={`w-full flex items-center justify-between gap-2 rounded p-2 transition-all cursor-pointer ${
                selectedSection?._key === sec._key
                  ? "bg-primary/10 text-primary"
                  : "hover:bg-accent"
              }`}
            >
              <div className="flex gap-2">
                <span className="text-[10px] font-bold text-primary shrink-0">
                  {sec.id}
                </span>
                <p
                  title={sec.name}
                  className={`text-xs font-semibold leading-snug line-clamp-1 text-left ${
                    selectedSection?._key === sec._key
                      ? "text-primary"
                      : "text-foreground"
                  }`}
                >
                  {capitalizeFirst(sec.name)}
                </p>
              </div>
              <Badge className="min-w-4 h-4 px-1 rounded-full flex items-center justify-center text-[9px] font-semibold shrink-0">
                {getMatchingControlsCount(sec)}
              </Badge>
            </button>
          ))}
          {filteredSections.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-6">
              No sections found
            </p>
          )}
        </ColPanel>

        {/* ── Col 3: Controls ───────────────────────────────────────────── */}
        <ColPanel title="Controls" badge={filteredControls.length || undefined}>
          <div className="mb-1 shrink-0">
            <SearchInput
              placeholder="Search controls..."
              value={controlSearch}
              onChange={setControlSearch}
              onClear={() => setControlSearch("")}
              className="bg-accent border-border focus-visible:ring-1"
            />
          </div>
          {filteredControls.length > 0 && (
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1 px-1 mb-1">
              <span className="min-w-12 shrink-0">ID</span>
              <span>Title</span>
            </div>
          )}
          {filteredControls.map((ctrl) => (
            <button
              type="button"
              key={ctrl.id}
              onClick={() => setSelectedControl(ctrl)}
              className={`w-full text-left flex items-center justify-between gap-2 rounded px-1 py-1.5 transition-all cursor-pointer ${
                selectedControl?.id === ctrl.id
                  ? "bg-primary/10"
                  : "hover:bg-accent"
              }`}
            >
              <div className="flex items-start gap-2 overflow-hidden flex-1">
                <span className="text-[10px] font-bold text-primary shrink-0">
                  {ctrl.id}
                </span>
                <span
                  className={`text-xs leading-snug line-clamp-1 ${
                    selectedControl?.id === ctrl.id
                      ? "text-primary"
                      : "text-foreground"
                  }`}
                >
                  {capitalizeFirst(ctrl.name)}
                </span>
              </div>
              <Badge className="min-w-4 h-4 px-1 rounded-full flex items-center justify-center text-[9px] font-semibold shrink-0">
                {getMatchingDpCount(ctrl)}
              </Badge>
            </button>
          ))}
          {!selectedSection && (
            <p className="text-xs text-muted-foreground text-center py-8">
              Select a section to view controls
            </p>
          )}
          {selectedSection && filteredControls.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-4">
              No controls found
            </p>
          )}
        </ColPanel>

        {/* ── Col 4: Monitoring Points ──────────────────────────────────── */}
        <ColPanel
          className="col-span-2"
          title={
            selectedControl
              ? `${selectedControl.id} · ${capitalizeFirst(selectedControl.name)}`
              : "Monitoring Points"
          }
          badge={selectedControl ? filteredPoints.length : undefined}
        >
          {selectedControl ? (
            <div className="space-y-4 p-1">
              {filteredPoints.map((dp, idx) => (
                <div key={dp.id}>
                  <p className="text-xs text-foreground mb-1 leading-relaxed">
                    <span className="font-bold text-muted-foreground mr-1">
                      {idx + 1}
                    </span>
                    {capitalizeFirst(dp.name)}
                  </p>
                  <div className="flex items-center gap-2">
                    <Input
                      type="text"
                      placeholder="Enter path..."
                      value={getPath(dp.id)}
                      onChange={(e) => setPath(dp.id, e.target.value)}
                      className="h-7 text-xs! flex-1"
                    />
                    <Input
                      type="text"
                      placeholder="Source..."
                      value={getSource(dp.id)}
                      onChange={(e) => setSource(dp.id, e.target.value)}
                      className="h-7 text-xs! w-24 shrink-0"
                    />
                    <Button
                      size="xs"
                      className="h-7 text-[10px] font-semibold px-2.5"
                      disabled={
                        savingDp === getCurrentPathKey(dp.id) ||
                        !getPath(dp.id).trim() ||
                        (getPath(dp.id).trim() ===
                          (savedPaths[getCurrentPathKey(dp.id)] ?? "") &&
                          getSource(dp.id).trim() ===
                            (savedSources[getCurrentPathKey(dp.id)] ?? ""))
                      }
                      onClick={() => handleSavePath(dp.id)}
                    >
                      {savingDp === getCurrentPathKey(dp.id)
                        ? "Saving..."
                        : "Save"}
                    </Button>
                  </div>
                </div>
              ))}
              {filteredPoints.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-6">
                  No monitoring points found
                </p>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <Icon
                name="cloud-upload"
                size="40px"
                className="text-muted-foreground mb-3"
              />
              <p className="text-sm text-muted-foreground">
                Select a control to view monitoring points
              </p>
            </div>
          )}
        </ColPanel>
      </div>
    </div>
  );
}
