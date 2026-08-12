// User-friendly page titles (used for <h1> page title only)
export const PAGE_TITLES = {
  dashboard: "Dashboard",
  "my-profile": "My Profile",
  profiles: "Profiles Management",
  customers: "Customer Management",
  "framework-categories": "Framework Category Management",
  "framework-access": "Framework Access Management",
  "framework-assignments": "Framework Assignment Management",
  frameworks: "Framework Management",
  framework: "Framework Detail",
  "deployment-frameworks": "Deployment Framework Management",
  "assigned-frameworks": "Assigned Frameworks",
  documents: "Document Management",
  report: "Deployment Framework Report",
  "controls-passing": "Controls Passing",
  "extra-controls": "Extra Controls",
  "critical-gaps": "Critical Gaps",
  "overall-protection": "Overall Protection",
  "deployment-points": "Deployment Points",
  "monitoring-setup": "Monitoring Setup",
  setup: "Framework Workflow Setup",
};

// Format a raw URL segment into a readable label (for breadcrumbs)
const formatSegment = (segment) =>
  segment
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

export function generateBreadcrumbs(pathname) {
  if (pathname === "/" || pathname === "/dashboard") {
    return [{ label: "Dashboard", path: "/dashboard", active: true }];
  }

  const segments = pathname.split("/").filter(Boolean);
  const breadcrumbs = [
    { label: "Dashboard", path: "/dashboard", active: false },
  ];

  let currentPath = "";

  segments.forEach((segment, index) => {
    // Always accumulate the path (including "dashboard")
    currentPath += `/${segment}`;

    // Skip "dashboard" breadcrumb entry - it's already the root item
    if (segment === "dashboard") return;

    // Priority: 1. Global dynamic labels (set by detail pages) 2. Static mapping 3. Default formatting
    const dynamicLabel = globalThis.__VORA_BREADCRUMB_LABELS__?.[segment];
    const label =
      dynamicLabel || PAGE_TITLES[segment] || formatSegment(segment);

    breadcrumbs.push({
      label: label,
      path: currentPath,
      active: index === segments.length - 1,
    });
  });

  return breadcrumbs;
}
